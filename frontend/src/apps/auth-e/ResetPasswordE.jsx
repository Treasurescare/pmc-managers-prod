import { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { authApi, showApiError } from "@/lib/api";
import PasswordInput from "@/components/PasswordInput";

// v50 — Option E "Set new password" screen. Consumed via the one-time link
// emailed by /api/v1/auth/password-reset/request.
export default function ResetPasswordE() {
  const [params] = useSearchParams();
  const nav = useNavigate();
  const token = params.get("token") || "";
  const [status, setStatus] = useState("verifying"); // verifying | ready | invalid | done
  const [meta, setMeta] = useState({ email: "", portal: "" });
  const [pw, setPw] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    let ignore = false;
    if (!token) {
      setStatus("invalid");
      setError("This reset link is missing its token. Request a new one.");
      return;
    }
    (async () => {
      try {
        const r = await authApi.verifyPasswordReset(token);
        if (ignore) return;
        setMeta({ email: r.email || "", portal: r.portal || "vendor" });
        setStatus("ready");
      } catch (err) {
        if (ignore) return;
        setStatus("invalid");
        setError(err?.response?.data?.detail || "This reset link is invalid or has expired.");
      }
    })();
    return () => { ignore = true; };
  }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    if (pw.length < 8) return toast.error("Password must be at least 8 characters.");
    if (pw !== confirm) return toast.error("Passwords don't match.");
    setBusy(true);
    try {
      await authApi.confirmPasswordReset(token, pw);
      setStatus("done");
      toast.success("Password updated. You can sign in with your new password.");
      setTimeout(() => nav(`/login?role=${{ vendor: "supplier", admin: "admin", staff: "staff", partner: "partner" }[meta.portal] || "supplier"}`), 1500);
    } catch (err) {
      showApiError(err);
    } finally {
      setBusy(false);
    }
  };

  const strengthLabel = () => {
    if (!pw) return "—";
    if (pw.length < 8) return "Too short";
    if (pw.length < 12) return "OK";
    if (/[^A-Za-z0-9]/.test(pw) && /[A-Z]/.test(pw) && /[0-9]/.test(pw)) return "Strong";
    return "Good";
  };

  return (
    <div data-testid="reset-password-e" data-pmc-e-page="reset-password-e">
      <div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)", minHeight: "100vh" }}>
        <section className="pmc-chrome" style={{ position: "relative", overflow: "hidden", padding: "48px 64px", display: "flex", flexDirection: "column" }}>
          <Link to="/" className="pmc-brand">
            <span className="pmc-brand__n">PMC Managers</span>
            <span className="pmc-brand__s">Global Tender Board</span>
          </Link>
          <svg viewBox="0 0 400 400" style={{ position: "absolute", right: "-140px", top: "120px", width: "560px", height: "560px", opacity: ".55" }} aria-hidden="true">
            <circle cx="200" cy="200" r="188" fill="none" stroke="var(--chrome-line)" />
            <circle cx="200" cy="200" r="140" fill="none" stroke="var(--brass-on-chrome)" />
          </svg>
          <div style={{ marginTop: "auto", position: "relative", maxWidth: "520px" }}>
            <div className="pmc-eyebrow">Set a new password</div>
            <h1 className="pmc-display" style={{ fontSize: "56px", lineHeight: "60px", margin: "12px 0 16px", color: "var(--on-chrome)" }}>
              Pick something <em style={{ color: "var(--brass-on-chrome)" }}>you&rsquo;ll remember.</em>
            </h1>
            <p className="pmc-muted" style={{ fontSize: "17px", lineHeight: "28px", margin: "0 0 24px" }}>
              Minimum 8 characters. Mixing letters, numbers and a symbol gets you to <b>Strong</b>.
            </p>
          </div>
        </section>

        <section style={{ display: "grid", placeItems: "center", padding: "48px" }}>
          <div style={{ width: "440px", maxWidth: "100%" }}>
            {status === "verifying" && (
              <div className="pmc-panel" style={{ padding: "28px" }} data-testid="reset-verifying">
                <div className="pmc-eyebrow">Verifying link…</div>
                <p className="pmc-muted" style={{ margin: "8px 0 0" }}>Checking your reset token.</p>
              </div>
            )}

            {status === "invalid" && (
              <div className="pmc-panel" style={{ padding: "28px" }} data-testid="reset-invalid">
                <div className="pmc-eyebrow" style={{ color: "var(--danger, #b3261e)" }}>Link problem</div>
                <h2 style={{ fontSize: "24px", lineHeight: "30px", margin: "6px 0 12px" }}>This reset link isn&rsquo;t usable</h2>
                <p className="pmc-muted" style={{ margin: "0 0 20px", lineHeight: "24px" }}>{error}</p>
                <Link to="/forgot-password" className="pmc-btn pmc-btn--primary" data-testid="reset-request-new">
                  Request a new link
                </Link>
              </div>
            )}

            {status === "done" && (
              <div className="pmc-panel" style={{ padding: "28px" }} data-testid="reset-done">
                <div className="pmc-eyebrow">All set</div>
                <h2 style={{ fontSize: "24px", lineHeight: "30px", margin: "6px 0 12px" }}>Password updated</h2>
                <p className="pmc-muted" style={{ margin: "0 0 20px" }}>Redirecting you to sign in…</p>
                <Link to={`/login?role=${{ vendor: "supplier", admin: "admin", staff: "staff", partner: "partner" }[meta.portal] || "supplier"}`} className="pmc-btn pmc-btn--primary" data-testid="reset-go-signin">
                  Sign in now
                </Link>
              </div>
            )}

            {status === "ready" && (
              <form onSubmit={submit} data-testid="reset-form">
                <h2 style={{ fontSize: "28px", lineHeight: "34px", margin: "0 0 6px" }}>Choose a new password</h2>
                <p className="pmc-muted" style={{ margin: "0 0 24px" }}>
                  For <b>{meta.email}</b>. Link expires 30 minutes after it was sent.
                </p>

                <div className="pmc-field">
                  <label>New password</label>
                  <PasswordInput
                    className="pmc-input"
                    type="password"
                    required
                    autoFocus
                    minLength={8}
                    autoComplete="new-password"
                    value={pw}
                    onChange={(e) => setPw(e.target.value)}
                    placeholder="At least 8 characters"
                    style={{ height: "44px" }}
                    data-testid="reset-new"
                  />
                  <div className="pmc-muted" style={{ fontSize: "12px", marginTop: "6px" }}>
                    Strength: <b>{strengthLabel()}</b>
                  </div>
                </div>

                <div className="pmc-field" style={{ marginTop: "14px" }}>
                  <label>Confirm new password</label>
                  <PasswordInput
                    className="pmc-input"
                    type="password"
                    required
                    autoComplete="new-password"
                    value={confirm}
                    onChange={(e) => setConfirm(e.target.value)}
                    placeholder="Re-enter the same password"
                    style={{ height: "44px" }}
                    data-testid="reset-confirm"
                  />
                </div>

                <button
                  type="submit"
                  disabled={busy}
                  className="pmc-btn pmc-btn--primary pmc-btn--lg"
                  style={{ width: "100%", marginTop: "18px" }}
                  data-testid="reset-submit"
                >
                  {busy ? "Updating…" : "Set new password"}
                </button>

                <p className="pmc-muted" style={{ fontSize: "13px", marginTop: "18px", textAlign: "center" }}>
                  Changed your mind? <Link to="/login">Back to sign in</Link>
                </p>
              </form>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
