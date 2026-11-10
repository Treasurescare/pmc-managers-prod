import { useEffect, useState } from "react";
import { useNavigate, Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { useUiTheme } from "@/context/UiThemeContext";
import { adminApi, api, staffApi, vendorApi, marketingApi, showApiError, cacheCsrf } from "@/lib/api";
import { startGoogleLogin } from "@/apps/auth-e/GoogleAuthCallback";
import LinkedInSignIn from "@/apps/auth-e/LinkedInSignIn";
import PasswordInput from "@/components/PasswordInput";

// v50-login-fix (Feb 2026) — Made the Option E sign-in form fully functional.
// Previously this was a pure static template (hardcoded password value, no
// onSubmit, no state) which is why users could not sign in from /login. The
// legacy portal-scoped routes (/vendor/login, /admin/login, /staff/login)
// continue to serve their own components; this page is the unified entry.
export default function SignInE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const nav = useNavigate();
  const [params] = useSearchParams();
  const rawNext = params.get("next") || "";
  const next = rawNext.startsWith("/") && !rawNext.startsWith("//") ? rawNext : "";
  const nextRole = next.startsWith("/admin") ? "admin" : next.startsWith("/buyer") ? "buyer" : next.startsWith("/staff") ? "staff" : next.startsWith("/vendor") ? "supplier" : next.startsWith("/escrow") ? "escrow" : next.startsWith("/partner") ? "partner" : "supplier";
  const qRole = params.get("role");
  const [role, setRole] = useState(["supplier", "staff", "admin", "escrow", "partner", "buyer"].includes(qRole) ? qRole : nextRole); // supplier | staff | admin
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  const [googleOn, setGoogleOn] = useState(false);
  useEffect(() => { marketingApi.googleConfig().then((c) => setGoogleOn(!!c.enabled)).catch(() => {}); }, []);
  useEffect(() => {
    if (params.get("deleted") === "1") {
      toast.success("Your account has been deleted", { description: "Your profile has been anonymised and you have been signed out.", duration: 10000 });
    }
  }, [params]);

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  const submit = async (e) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Enter your email and password to continue.");
      return;
    }
    setBusy(true);
    try {
      if (role === "partner") {
        try {
          const pr = await api.post("/api/v1/agents/auth/login", { email, password });
          cacheCsrf(pr?.data?.csrf_token);
        } catch (err) {
          if (err?.response?.status !== 401) throw err;
          toast.error("That email and password don't match a Partner account.", {
            description: "Use the password you created after confirming your email (your browser may have filled a different saved one). Supplier accounts sign in under Supplier. Forgot it? Use “Forgot password?” and pick Partner.",
            duration: 12000, closeButton: true,
          });
          return;
        }
        toast.success("Signed in · partner");
        return nav("/partner/me");
      }
      if (role === "escrow") {
        try {
          const accRes = await api.post("/api/v1/escrow-accounts/auth/login", { email, password });
          cacheCsrf(accRes?.data?.csrf_token);
          toast.success("Signed in · escrow institution");
          return nav("/escrow/me");
        } catch (accErr) {
          const code = accErr?.response?.status;
          const detail = accErr?.response?.data?.detail;
          if (code === 403 && detail && typeof detail === "object" && detail.error === "unverified") {
            toast.error("Sign in failed", {
              description: detail.message || "Please verify your email before signing in.",
              duration: 10000,
              closeButton: true,
            });
            return;
          }
          if (code !== 401 && code !== 404 && !accErr?.__pmcHtmlGuard) throw accErr;
        }
        try {
          const sigRes = await api.post("/api/v1/escrow-signatories/auth/login", { email, password });
          cacheCsrf(sigRes?.data?.csrf_token);
          toast.success("Signed in · escrow signatory");
          return nav("/escrow/me");
        } catch (err) {
          // v53m — surface the backend's structured detail so the user
          // knows WHICH part failed (no-account vs no-account-only-institution
          // vs wrong-password) and what to do next.
          const code = err?.response?.status;
          const d = err?.response?.data?.detail;
          if (code === 404 && d && typeof d === "object" && d.message) {
            toast.error(d.message, { duration: 10000, closeButton: true });
            return;
          }
          toast.error("Those credentials don't match an escrow account or signatory. New institutions can register below.",
                      { duration: 8000 });
          return;
        }
      }
      if (role === "supplier") {
        try {
          const vr = await vendorApi.login(email, password);
          toast.success("Signed in · vendor");
          if (vr && vr.must_change_password) return nav("/vendor/change-password");
          return nav(next.startsWith("/vendor") ? next : "/vendor");
        } catch (err) {
          console.warn("[SignIn] supplier login failed:", err?.response?.data || err?.message);
          toast.error(
            "Sign-in failed for the Supplier portal. Check your email, password, and that you picked the right role.",
            { duration: 8000 }
          );
          return;
        }
      }
      // v53o — try all active staff roles for the staff sign-in card
      const allStaffRoles = [
        "reviewer", "escrow_agent", "certifier", "legal_counsel", "accounting",
        "committee_member", "auditor", "support", "management", "partner", "agent",
      ];
      // The "PMC staff" card must NEVER sign a user in as admin — that would
      // let an escrow/specialist account escalate to the admin console. Admin
      // sign-in is only via the "Administrator" card (roleCandidates=["admin"]).
      const roleCandidates = role === "admin" ? ["admin"] : role === "buyer" ? ["buyer"] : allStaffRoles;
      let lastErr = null;
      let mfaDetail = null;
      for (const rc of roleCandidates) {
        try {
          const r = await staffApi.login(email, password, rc, undefined);
          // A genuine login result is a JSON OBJECT from our API. Guard against
          // anything else (belt-and-suspenders with the HTML-response guard in
          // api.js) so a masked error can never look like a successful sign-in.
          const isLoginJson = r && typeof r === "object" && !Array.isArray(r);
          if (isLoginJson && r.active_role) {
            toast.success(`Signed in · ${r.active_role}`);
            if (r.active_role === "admin") return nav(next.startsWith("/admin") ? next : "/admin");
            if (r.active_role === "buyer") return nav(next.startsWith("/market") || next.startsWith("/buyer") ? next : "/buyer");
            return nav(next.startsWith("/staff") ? next : "/staff");
          }
          if (isLoginJson && r.mfa_required) {
            toast.info("MFA required — use the admin portal for 2FA.");
            return;
          }
          // Otherwise (wrong role for this account) keep probing the next role.
        } catch (err) {
          lastErr = err;
          // Remember a high-risk-role MFA 403 even if later candidates overwrite lastErr.
          const d = err?.response?.data?.detail;
          if (err?.response?.status === 403 && typeof d === "string" && /MFA|confirm your email/i.test(d)) mfaDetail = d;
          // try next candidate
        }
      }
      // Legacy admin cookie realm fallback for the admin card only.
      if (role === "admin") {
        try {
          await adminApi.login(email, password);
          toast.success("Signed in · admin");
          return nav(next.startsWith("/admin") ? next : "/admin");
        } catch (err) {
          lastErr = err;
          // fall through to the generic error below
        }
      }
      // v54p — if the only matching role is high-risk (escrow_agent /
      // legal_counsel / accounting) the backend returns a 403 explaining that
      // MFA must be enabled from the admin portal first. Surface that exact
      // guidance instead of the generic "sign-in failed" message.
      if (mfaDetail) {
        toast.error(mfaDetail, { duration: 12000, closeButton: true });
        return;
      }
      // v50g bug #124 — show a clear role-aware error toast (duration 8s) so
      // testers never think a wrong-credentials sign-in silently succeeded.
      const roleLabel = role === "admin" ? "Administrator" : role === "buyer" ? "Buyer organisation" : "PMC staff";
      toast.error(
        `Sign-in failed for the ${roleLabel} portal. Check your email, password, and that you picked the right role.`,
        { duration: 8000 }
      );
      if (lastErr) {
        // Log the backend-reported reason to the console for debugging but
        // keep the user-facing toast consistent to avoid user-enumeration.
        console.warn("[SignIn] backend error:", lastErr?.response?.data || lastErr?.message);
      }
    } catch (err) {
      showApiError(err);
    } finally {
      setBusy(false);
    }
  };

  const RoleRadio = ({ value, label, sub, icon }) => (
    <label
      className={`pmc-radio ${role === value ? "on" : ""}`}
      style={{ padding: "14px 16px", cursor: "pointer" }}
      data-testid={`signin-role-${value}`}
      onClick={() => { setRole(value); try { const u = new URL(window.location.href); u.searchParams.set("role", value); window.history.replaceState(window.history.state, "", u); } catch { /* ignore */ } }}
    >
      <svg className="pmc-ico" aria-hidden="true"><use href={`#${icon}`} /></svg>
      <div>
        <b>{label}</b>
        <div className="pmc-muted" style={{ fontSize: "13px" }}>{sub}</div>
      </div>
    </label>
  );

  return (
    <div data-testid="sign-in-e" data-pmc-e-page="sign-in-e">
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)", minHeight: "100vh" }}>
        <section className="pmc-chrome" style={{ position: "relative", overflow: "hidden", padding: "48px 64px", display: "flex", flexDirection: "column" }}>
          <Link to="/" className="pmc-brand">
            <span className="pmc-brand__n">PMC Managers</span>
            <span className="pmc-brand__s">Global Tender Grid</span>
          </Link>
          <svg viewBox="0 0 400 400" style={{ position: "absolute", right: "-140px", top: "120px", width: "560px", height: "560px", opacity: ".55" }} aria-hidden="true">
            <circle cx="200" cy="200" r="188" fill="none" stroke="var(--chrome-line)" />
            <circle cx="200" cy="200" r="140" fill="none" stroke="var(--brass-on-chrome)" />
            <circle cx="200" cy="200" r="92" fill="none" stroke="var(--chrome-line)" />
          </svg>
          <div style={{ marginTop: "auto", position: "relative", maxWidth: "520px" }}>
            <div className="pmc-eyebrow">Welcome back</div>
            <h1 className="pmc-display" style={{ fontSize: "64px", lineHeight: "64px", margin: "12px 0 16px", color: "var(--on-chrome)" }}>
              Pick up exactly <em style={{ color: "var(--brass-on-chrome)" }}>where you left off.</em>
            </h1>
            <p className="pmc-muted" style={{ fontSize: "17px", lineHeight: "28px", margin: "0 0 28px" }}>
              Your drafts, sealed envelopes and deadlines are waiting. Every sign-in is recorded on the audit ledger.
            </p>
            <div style={{ display: "grid", gap: "10px", fontSize: "14px" }}>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>
                Two-factor sign-in for every staff account
              </div>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>
                Face ID or fingerprint on the mobile app
              </div>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>
                Sign-in events chained to the ledger
              </div>
            </div>
          </div>
        </section>

        <section style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr)", placeItems: "center", padding: "48px" }}>
          <form onSubmit={submit} style={{ width: "440px", maxWidth: "100%", minWidth: 0 }} data-testid="signin-e-form">
            <h2 style={{ fontSize: "28px", lineHeight: "34px", margin: "0 0 6px" }}>Sign in</h2>
            {next && (
              <div data-testid="signin-next-notice" style={{ background: "#FFF8E6", border: "1px solid #E8C873", padding: "10px 12px", fontSize: "13px", margin: "8px 0 12px" }}>
                The page you opened{next.startsWith("/admin") ? " (from a PMC admin email)" : ""} is private. Sign in{nextRole === "admin" ? " as Administrator" : ""} with your email and password and we'll take you straight there.
              </div>
            )}
            <p className="pmc-muted" style={{ margin: "0 0 24px" }}>
              {role === "partner" ? (
                <>New partner? <Link to="/partner/register" data-testid="signin-register-link">Apply to become a PMC partner</Link></>
              ) : role === "escrow" ? (
                <>New escrow institution? <Link to="/escrow/register" data-testid="signin-register-link">Register your bank or trustee firm</Link></>
              ) : role === "buyer" ? (
                <>New buyer? <Link to="/buyers/register" data-testid="signin-register-link">Register as a buyer — free</Link></>
              ) : (
                <>New supplier? <Link to="/register" data-testid="signin-register-link">Register in about 15 minutes</Link></>
              )}
            </p>

            <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}>
              <RoleRadio value="supplier" label="Supplier" sub="Bid, pay EMD, sign contracts" icon="i-users" />
              <RoleRadio value="buyer" label="Buyer organisation" sub="Bid, offer and buy on the marketplace" icon="i-box" />
              <RoleRadio value="staff" label="PMC staff" sub="Tender desk, evaluation, escrow" icon="i-file" />
              <RoleRadio value="admin" label="Administrator" sub="Configuration and audit" icon="i-shield" />
              <RoleRadio value="escrow" label="Escrow Institution" sub="Banks & trustees · dual-signature sign-off" icon="i-link" />
              <RoleRadio value="partner" label="Partner" sub="Onboard suppliers and earn commission" icon="i-flag" />
            </div>

            <div style={{ display: "grid", gap: "14px", gridTemplateColumns: "minmax(0,1fr)" }}>
              <div className="pmc-field">
                <label>Work email</label>
                <input
                  className="pmc-input"
                  type="email"
                  required
                  autoFocus
                  autoComplete="email"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  placeholder="name@company.com"
                  style={{ height: "44px" }}
                  data-testid="signin-e-email"
                />
              </div>
              <div className="pmc-field">
                <div style={{ display: "flex", justifyContent: "space-between" }}>
                  <label>Password</label>
                  <Link to="/forgot-password" style={{ fontSize: "13px" }} data-testid="signin-forgot-link">
                    Forgot password?
                  </Link>
                </div>
                <PasswordInput
                  className="pmc-input"
                  type="password"
                  required
                  autoComplete="current-password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  style={{ height: "44px" }}
                  data-testid="signin-e-password"
                />
              </div>
              <button
                type="submit"
                disabled={busy}
                className="pmc-btn pmc-btn--primary pmc-btn--lg"
                style={{ width: "100%" }}
                data-testid="signin-e-submit"
              >
                {busy ? "Signing in…" : "Continue"}
              </button>
              {googleOn && role !== "escrow" && role !== "partner" && (
                <button type="button" onClick={() => startGoogleLogin(role)} className="pmc-btn pmc-btn--secondary pmc-btn--lg"
                        style={{ width: "100%" }} data-testid="signin-google">
                  <svg width="18" height="18" viewBox="0 0 48 48" aria-hidden="true"><path fill="#FFC107" d="M43.6 20.5H42V20H24v8h11.3C33.7 32.7 29.2 36 24 36c-6.6 0-12-5.4-12-12s5.4-12 12-12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 12.9 4 4 12.9 4 24s8.9 20 20 20 20-8.9 20-20c0-1.3-.1-2.4-.4-3.5z"/><path fill="#FF3D00" d="M6.3 14.7l6.6 4.8C14.7 15.1 19 12 24 12c3.1 0 5.8 1.2 7.9 3.1l5.7-5.7C34 6.1 29.3 4 24 4 16.3 4 9.7 8.3 6.3 14.7z"/><path fill="#4CAF50" d="M24 44c5.2 0 9.9-2 13.4-5.2l-6.2-5.2C29.2 35.1 26.7 36 24 36c-5.2 0-9.6-3.3-11.3-8l-6.5 5C9.5 39.6 16.2 44 24 44z"/><path fill="#1976D2" d="M43.6 20.5H42V20H24v8h11.3c-.8 2.2-2.2 4.2-4.1 5.6l6.2 5.2C37 39.2 44 34 44 24c0-1.3-.1-2.4-.4-3.5z"/></svg>
                  Continue with Google
                </button>
              )}
              <LinkedInSignIn role={role} />

              <div style={{ display: "flex", alignItems: "center", gap: "12px", color: "var(--ink-muted, #5B6B63)", fontSize: "12px", textTransform: "uppercase", letterSpacing: "1.5px" }}>
                <span style={{ flex: 1, height: "1px", background: "rgba(15,59,46,.15)" }} />
                {role === "escrow" ? "New escrow institution?" : role === "partner" ? "New partner?" : role === "buyer" ? "New buyer?" : "New supplier?"}
                <span style={{ flex: 1, height: "1px", background: "rgba(15,59,46,.15)" }} />
              </div>
              <Link
                to={role === "escrow" ? "/escrow/register" : role === "partner" ? "/partner/register" : role === "buyer" ? "/buyers/register" : "/register"}
                className="pmc-btn pmc-btn--lg"
                style={{ width: "100%", textAlign: "center", display: "block", border: "1px solid var(--primary, #0F3B2E)", color: "var(--primary, #0F3B2E)", fontWeight: 600, textDecoration: "none", lineHeight: "44px" }}
                data-testid="signin-register-btn"
              >
                {role === "escrow"
                  ? "Register as an escrow institution — bank / trustee onboarding"
                  : role === "partner"
                    ? "Register as a partner — onboard suppliers & earn commission"
                    : role === "buyer"
                      ? "Register as a buyer — free"
                      : "Register as a supplier — free, ~15 minutes"}
              </Link>
            </div>

            <div className="pmc-muted" style={{ fontSize: "12px", marginTop: "24px", display: "flex", justifyContent: "space-between" }}>
              <span>© 2026 PMC Managers Limited</span>
              <span>
                <Link to="/help" data-testid="signin-help-link">Help</Link> · <Link to="/privacy">Privacy</Link>
              </span>
            </div>
          </form>
        </section>
      </div>
    </div>
  );
}
