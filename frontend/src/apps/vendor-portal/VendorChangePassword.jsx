import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { vendorApi, showApiError } from "@/lib/api";

// v50 — Option E "First sign-in / temporary password" screen.
// Rewrote the old Navy Tailwind card into the Option E chrome so the
// first-login step matches the rest of the vendor portal.
export default function VendorChangePassword() {
  const nav = useNavigate();
  const [me, setMe] = useState(null);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    vendorApi.me()
      .then((v) => setMe(v))
      .catch(() => nav("/vendor/login"));
  }, [nav]);

  const strength = () => {
    if (!next) return { label: "—", pct: 0 };
    if (next.length < 8) return { label: "Too short", pct: 20 };
    if (next.length < 12) return { label: "OK", pct: 50 };
    if (/[^A-Za-z0-9]/.test(next) && /[A-Z]/.test(next) && /[0-9]/.test(next)) return { label: "Strong", pct: 100 };
    return { label: "Good", pct: 75 };
  };

  const submit = async (e) => {
    e.preventDefault();
    if (next !== confirm) return toast.error("Passwords don't match.");
    if (next.length < 8) return toast.error("Password must be at least 8 characters.");
    if (next === current) return toast.error("Pick a new password different from the temporary one.");
    setLoading(true);
    try {
      await vendorApi.changePassword(current, next);
      toast.success("Password updated. Welcome to the PMC Vendor Portal.");
      nav("/vendor");
    } catch (err) {
      showApiError(err);
    } finally {
      setLoading(false);
    }
  };

  const s = strength();

  return (
    <div data-testid="vendor-change-password" data-pmc-e-page="vendor-change-password">
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)", minHeight: "100vh" }}>
        <section className="pmc-chrome" style={{ position: "relative", overflow: "hidden", padding: "48px 64px", display: "flex", flexDirection: "column" }}>
          <Link to="/" className="pmc-brand">
            <span className="pmc-brand__n">PMC Managers</span>
            <span className="pmc-brand__s">Vendor portal</span>
          </Link>
          <svg viewBox="0 0 400 400" style={{ position: "absolute", right: "-140px", top: "120px", width: "560px", height: "560px", opacity: ".55" }} aria-hidden="true">
            <circle cx="200" cy="200" r="188" fill="none" stroke="var(--chrome-line)" />
            <circle cx="200" cy="200" r="140" fill="none" stroke="var(--brass-on-chrome)" />
            <circle cx="200" cy="200" r="92" fill="none" stroke="var(--chrome-line)" />
          </svg>
          <div style={{ marginTop: "auto", position: "relative", maxWidth: "520px" }}>
            <div className="pmc-eyebrow">First sign-in</div>
            <h1 className="pmc-display" style={{ fontSize: "56px", lineHeight: "60px", margin: "12px 0 16px", color: "var(--on-chrome)" }}>
              One quick step: <em style={{ color: "var(--brass-on-chrome)" }}>set your password.</em>
            </h1>
            <p className="pmc-muted" style={{ fontSize: "17px", lineHeight: "28px", margin: "0 0 28px" }}>
              You&rsquo;re signed in with a temporary password issued by PMC. Replace it before you continue &mdash; only you should know the new one.
            </p>
            <div style={{ display: "grid", gap: "10px", fontSize: "14px" }}>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>
                At least 8 characters &middot; mixing symbols reaches <b>Strong</b>
              </div>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>
                Never share your password or MFA codes over email
              </div>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>
                This change is chained to the audit ledger
              </div>
            </div>
          </div>
        </section>

        <section style={{ display: "grid", placeItems: "center", padding: "48px" }}>
          <form onSubmit={submit} style={{ width: "440px", maxWidth: "100%" }} data-testid="vcp-form">
            <h2 style={{ fontSize: "28px", lineHeight: "34px", margin: "0 0 6px" }}>Set your new password</h2>
            <p className="pmc-muted" style={{ margin: "0 0 24px" }}>
              {me?.company_name ? <>Signed in as <b>{me.company_name}</b></> : "Signed in as a vendor"}
              {me?.email ? <> &middot; {me.email}</> : null}
            </p>

            <div className="pmc-field">
              <label>Current (temporary) password</label>
              <input
                className="pmc-input"
                type="password"
                required
                autoFocus
                autoComplete="current-password"
                value={current}
                onChange={(e) => setCurrent(e.target.value)}
                placeholder="The password we sent by email"
                style={{ height: "44px" }}
                data-testid="vcp-current"
              />
            </div>

            <div className="pmc-field" style={{ marginTop: "14px" }}>
              <label>New password</label>
              <input
                className="pmc-input"
                type="password"
                required
                minLength={8}
                autoComplete="new-password"
                value={next}
                onChange={(e) => setNext(e.target.value)}
                placeholder="At least 8 characters"
                style={{ height: "44px" }}
                data-testid="vcp-new"
              />
              <div style={{ display: "flex", alignItems: "center", gap: "10px", marginTop: "8px" }}>
                <div style={{ flex: 1, height: "6px", background: "var(--surface-sunken)", borderRadius: "3px", overflow: "hidden" }}>
                  <div style={{
                    width: `${s.pct}%`,
                    height: "100%",
                    background: s.pct >= 100 ? "var(--success, #1f8a5a)" :
                                s.pct >= 75 ? "var(--brass-on-chrome, #c9a24b)" :
                                s.pct >= 50 ? "#e0b060" : "#d67373",
                    transition: "width .2s ease",
                  }} />
                </div>
                <span className="pmc-muted" style={{ fontSize: "12px", minWidth: "70px", textAlign: "right" }}>
                  {s.label}
                </span>
              </div>
            </div>

            <div className="pmc-field" style={{ marginTop: "14px" }}>
              <label>Confirm new password</label>
              <input
                className="pmc-input"
                type="password"
                required
                autoComplete="new-password"
                value={confirm}
                onChange={(e) => setConfirm(e.target.value)}
                placeholder="Re-enter the same password"
                style={{ height: "44px" }}
                data-testid="vcp-confirm"
              />
              {confirm && confirm !== next && (
                <div className="pmc-muted" style={{ fontSize: "12px", marginTop: "6px", color: "var(--danger, #b3261e)" }}>
                  Passwords don&rsquo;t match yet.
                </div>
              )}
            </div>

            <button
              type="submit"
              disabled={loading}
              className="pmc-btn pmc-btn--primary pmc-btn--lg"
              style={{ width: "100%", marginTop: "20px" }}
              data-testid="vcp-submit"
            >
              {loading ? "Updating…" : "Set new password"}
            </button>

            <p className="pmc-muted" style={{ fontSize: "13px", marginTop: "18px", textAlign: "center" }}>
              Lost the temporary password?{" "}
              <Link to="/forgot-password" data-testid="vcp-forgot-link">Request a reset link</Link>
            </p>
          </form>
        </section>
      </div>
    </div>
  );
}
