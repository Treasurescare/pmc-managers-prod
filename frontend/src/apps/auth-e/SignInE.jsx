import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { useUiTheme } from "@/context/UiThemeContext";
import { adminApi, api, staffApi, vendorApi, showApiError, cacheCsrf } from "@/lib/api";

// v50-login-fix (Feb 2026) — Made the Option E sign-in form fully functional.
// Previously this was a pure static template (hardcoded password value, no
// onSubmit, no state) which is why users could not sign in from /login. The
// legacy portal-scoped routes (/vendor/login, /admin/login, /staff/login)
// continue to serve their own components; this page is the unified entry.
export default function SignInE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const nav = useNavigate();
  const [role, setRole] = useState("supplier"); // supplier | staff | admin
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

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
          if (code !== 401 && code !== 404) throw accErr;
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
          return nav("/vendor");
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
      const roleCandidates = role === "admin" ? ["admin"] : allStaffRoles;
      let lastErr = null;
      for (const rc of roleCandidates) {
        try {
          const r = await staffApi.login(email, password, rc, undefined);
          if (r && !r.mfa_required) {
            toast.success(`Signed in · ${r.active_role}`);
            if (role === "admin" || r.active_role === "admin") return nav("/admin");
            return nav("/staff");
          }
          if (r && r.mfa_required) {
            toast.info("MFA required — use the admin portal for 2FA.");
            return;
          }
        } catch (err) {
          lastErr = err;
          // try next candidate
        }
      }
      // Legacy admin cookie realm fallback for the admin card only.
      if (role === "admin") {
        try {
          await adminApi.login(email, password);
          toast.success("Signed in · admin");
          return nav("/admin");
        } catch (err) {
          lastErr = err;
          // fall through to the generic error below
        }
      }
      // v50g bug #124 — show a clear role-aware error toast (duration 8s) so
      // testers never think a wrong-credentials sign-in silently succeeded.
      const roleLabel = role === "admin" ? "Administrator" : "PMC staff";
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
      onClick={() => setRole(value)}
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
            <span className="pmc-brand__s">Global Tender Board</span>
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

        <section style={{ display: "grid", placeItems: "center", padding: "48px" }}>
          <form onSubmit={submit} style={{ width: "440px", maxWidth: "100%" }} data-testid="signin-e-form">
            <h2 style={{ fontSize: "28px", lineHeight: "34px", margin: "0 0 6px" }}>Sign in</h2>
            <p className="pmc-muted" style={{ margin: "0 0 24px" }}>
              {role === "escrow" ? (
                <>New escrow institution? <Link to="/escrow/register" data-testid="signin-register-link">Register your bank or trustee firm</Link></>
              ) : (
                <>New supplier? <Link to="/register" data-testid="signin-register-link">Register in about 15 minutes</Link></>
              )}
            </p>

            <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}>
              <RoleRadio value="supplier" label="Supplier" sub="Bid, pay EMD, sign contracts" icon="i-users" />
              <RoleRadio value="staff" label="PMC staff" sub="Tender desk, evaluation, escrow" icon="i-file" />
              <RoleRadio value="admin" label="Administrator" sub="Configuration and audit" icon="i-shield" />
              <RoleRadio value="escrow" label="Escrow Institution" sub="Banks & trustees · dual-signature sign-off" icon="i-link" />
            </div>

            <div style={{ display: "grid", gap: "14px" }}>
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
                <input
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

              <div style={{ display: "flex", alignItems: "center", gap: "12px", color: "var(--ink-muted, #5B6B63)", fontSize: "12px", textTransform: "uppercase", letterSpacing: "1.5px" }}>
                <span style={{ flex: 1, height: "1px", background: "rgba(15,59,46,.15)" }} />
                {role === "escrow" ? "New escrow institution?" : "New supplier?"}
                <span style={{ flex: 1, height: "1px", background: "rgba(15,59,46,.15)" }} />
              </div>
              <Link
                to={role === "escrow" ? "/escrow/register" : "/register"}
                className="pmc-btn pmc-btn--lg"
                style={{ width: "100%", textAlign: "center", display: "block", border: "1px solid var(--primary, #0F3B2E)", color: "var(--primary, #0F3B2E)", fontWeight: 600, textDecoration: "none", lineHeight: "44px" }}
                data-testid="signin-register-btn"
              >
                {role === "escrow"
                  ? "Register as an escrow institution — bank / trustee onboarding"
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
