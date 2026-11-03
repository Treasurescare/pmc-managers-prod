import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { authApi, api, showApiError } from "@/lib/api";

// v50 — Option E "Forgot password?" request form.
// Always confirms request was received (no user enumeration).
export default function ForgotPasswordE() {
  const [email, setEmail] = useState("");
  const [qp] = useSearchParams();
  const [portal, setPortal] = useState(["vendor", "admin", "staff", "escrow", "partner"].includes(qp.get("portal")) ? qp.get("portal") : "vendor");
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!email) return toast.error("Enter your account email.");
    setBusy(true);
    try {
      if (portal === "escrow") {
        // v52i — fire both escrow forgot endpoints (account-first flow and
        // legacy signatory flow). Both always return ok, so nothing here
        // leaks whether the email exists.
        await Promise.all([
          api.post("/api/v1/escrow-accounts/auth/forgot", { email }).catch(() => null),
          api.post("/api/v1/escrow-signatories/auth/forgot-password", { email }).catch(() => null),
        ]);
      } else {
        await authApi.requestPasswordReset(email, portal);
      }
      setSent(true);
    } catch (err) {
      showApiError(err);
    } finally {
      setBusy(false);
    }
  };

  const Radio = ({ value, label, sub, icon }) => (
    <label
      className={`pmc-radio ${portal === value ? "on" : ""}`}
      style={{ padding: "12px 14px", cursor: "pointer" }}
      data-testid={`forgot-portal-${value}`}
      onClick={() => setPortal(value)}
    >
      <svg className="pmc-ico" aria-hidden="true"><use href={`#${icon}`} /></svg>
      <div>
        <b>{label}</b>
        <div className="pmc-muted" style={{ fontSize: "13px" }}>{sub}</div>
      </div>
    </label>
  );

  return (
    <div data-testid="forgot-password-e" data-pmc-e-page="forgot-password-e">
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)", minHeight: "100vh" }}>
        <section className="pmc-chrome" style={{ position: "relative", overflow: "hidden", padding: "48px 64px", display: "flex", flexDirection: "column" }}>
          <Link to="/" className="pmc-brand">
            <span className="pmc-brand__n">PMC Managers</span>
            <span className="pmc-brand__s">Global Tender Grid</span>
          </Link>
          <svg viewBox="0 0 400 400" style={{ position: "absolute", right: "-140px", top: "120px", width: "560px", height: "560px", opacity: ".55" }} aria-hidden="true">
            <circle cx="200" cy="200" r="188" fill="none" stroke="var(--chrome-line)" />
            <circle cx="200" cy="200" r="140" fill="none" stroke="var(--brass-on-chrome)" />
          </svg>
          <div style={{ marginTop: "auto", position: "relative", maxWidth: "520px" }}>
            <div className="pmc-eyebrow">Account recovery</div>
            <h1 className="pmc-display" style={{ fontSize: "56px", lineHeight: "60px", margin: "12px 0 16px", color: "var(--on-chrome)" }}>
              A one-time link, <em style={{ color: "var(--brass-on-chrome)" }}>emailed only to you.</em>
            </h1>
            <p className="pmc-muted" style={{ fontSize: "17px", lineHeight: "28px", margin: "0 0 28px" }}>
              We&rsquo;ll send a signed reset link to the address on file. The link expires in 30 minutes and can only be used once.
            </p>
            <div style={{ display: "grid", gap: "10px", fontSize: "14px" }}>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>
                Signed with your account&rsquo;s private token
              </div>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>
                Old password stays active until the link is used
              </div>
              <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>
                Every reset attempt is chained to the ledger
              </div>
            </div>
          </div>
        </section>

        <section style={{ display: "grid", placeItems: "center", padding: "48px" }}>
          <div style={{ width: "440px", maxWidth: "100%" }}>
            {sent ? (
              <div className="pmc-panel" style={{ padding: "28px" }} data-testid="forgot-sent-panel">
                <div className="pmc-eyebrow">Check your inbox</div>
                <h2 style={{ fontSize: "26px", lineHeight: "32px", margin: "6px 0 12px" }}>Reset link on its way</h2>
                <p className="pmc-muted" style={{ margin: "0 0 20px", lineHeight: "24px" }}>
                  If <b>{email}</b> matches an account, a message with a one-time reset link is on its way. It expires in <b>30 minutes</b>.
                </p>
                <p className="pmc-muted" style={{ margin: "0 0 20px", fontSize: "13px" }}>
                  Nothing arriving? Check spam, or contact <a href="mailto:adminsupport@pmcmanagers.com">adminsupport@pmcmanagers.com</a>.
                </p>
                <Link to="/login" className="pmc-btn pmc-btn--secondary" data-testid="forgot-back-to-signin">
                  Back to sign in
                </Link>
              </div>
            ) : (
              <form onSubmit={submit} data-testid="forgot-form">
                <h2 style={{ fontSize: "28px", lineHeight: "34px", margin: "0 0 6px" }}>Forgot your password?</h2>
                <p className="pmc-muted" style={{ margin: "0 0 24px" }}>
                  Pick your portal and enter your account email &mdash; we&rsquo;ll email a one-time reset link.
                </p>

                <div style={{ display: "grid", gap: "8px", marginBottom: "18px" }}>
                  <Radio value="vendor" label="Supplier" sub="Vendor portal" icon="i-users" />
                  <Radio value="admin" label="Administrator" sub="Admin console (Owner, Master Admin, Support)" icon="i-shield" />
                  <Radio value="staff" label="PMC staff" sub="Tender desk, evaluation, escrow, committee" icon="i-briefcase" />
                  <Radio value="escrow" label="Escrow Institution" sub="Banks & trustees · owner accounts and signatories" icon="i-link" />
                  <Radio value="partner" label="Partner" sub="Partner portal" icon="i-flag" />
                </div>

                <div className="pmc-field">
                  <label>Account email</label>
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
                    data-testid="forgot-email"
                  />
                </div>

                <button
                  type="submit"
                  disabled={busy}
                  className="pmc-btn pmc-btn--primary pmc-btn--lg"
                  style={{ width: "100%", marginTop: "18px" }}
                  data-testid="forgot-submit"
                >
                  {busy ? "Sending…" : "Email me a reset link"}
                </button>

                <p className="pmc-muted" style={{ fontSize: "13px", marginTop: "18px", textAlign: "center" }}>
                  Remembered it? <Link to="/login" data-testid="forgot-back-link">Back to sign in</Link>
                </p>
              </form>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
