import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api, showApiError, cacheCsrf } from "@/lib/api";

/**
 * EscrowSignatoryLogin + Claim — v51an.
 *
 * Two modes:
 *   • With `?claim=1&iid=<institutionId>&token=<magic_token>` — sets a
 *     password for a signatory (email must match the institution record).
 *   • Default — password login that drops a cookie session and routes to
 *     `/escrow/me` (which auto-redirects to the signatory dashboard).
 */
export default function EscrowSignatoryLogin() {
  const nav = useNavigate();
  const [params] = useSearchParams();
  const isClaim = params.get("claim") === "1";
  const isReset = params.get("reset") === "1";
  const resetToken = params.get("token") || "";
  const iid = params.get("iid") || "";
  const token = params.get("token") || "";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [forgotMode, setForgotMode] = useState(false);

  const submitLogin = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      // v52d — try the account-first login first (new primary-contact flow).
      // Falls back to the signatory login below for anyone who already
      // claimed a signatory password.
      try {
        const accRes = await api.post("/api/v1/escrow-accounts/auth/login", { email, password });
        cacheCsrf(accRes?.data?.csrf_token);
        toast.success("Signed in · escrow institution");
        nav("/escrow/me");
        return;
      } catch (accErr) {
        const code = accErr?.response?.status;
        const detail = accErr?.response?.data?.detail;
        // v52d bug fix (testing_agent iter 66): 403 "unverified" from the
        // account endpoint used to fall through to the signatory login and
        // surface a generic "Invalid email or password". Keep that message
        // visible instead and stop falling through.
        if (code === 403 && detail && typeof detail === "object" && detail.error === "unverified") {
          toast.error("Sign in failed", {
            description: detail.message || "Please verify your email before signing in.",
            duration: 10000, closeButton: true,
          });
          return;
        }
        // Only 401/404 are "wrong endpoint for this email" — try signatory.
        if (code !== 401 && code !== 404) throw accErr;
      }
      const sigRes2 = await api.post("/api/v1/escrow-signatories/auth/login", { email, password });
      cacheCsrf(sigRes2?.data?.csrf_token);
      toast.success("Signed in · escrow signatory");
      nav("/escrow/me");
    } catch (err) { showApiError(err, { fallbackTitle: "Sign in failed" }); }
    finally { setBusy(false); }
  };

  const submitClaim = async (e) => {
    e.preventDefault();
    if (!iid || !token) return toast.error("Claim link is incomplete.");
    if (password.length < 8) return toast.error("Password must be at least 8 characters.");
    if (password !== confirm) return toast.error("Passwords don't match.");
    setBusy(true);
    try {
      await api.post("/api/v1/escrow-signatories/claim",
                     { institution_id: iid, email, password },
                     { params: { token } });
      toast.success("Password set — you can now sign in with your email.");
      const sigRes = await api.post("/api/v1/escrow-signatories/auth/login", { email, password });
      cacheCsrf(sigRes?.data?.csrf_token);
      nav("/escrow/me");
    } catch (err) { showApiError(err); }
    finally { setBusy(false); }
  };

  const submitForgot = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      // v52i — fire BOTH account + signatory forgot endpoints. Both always
      // return ok (no user enumeration) and only the side that recognises
      // the email actually sends a link.
      await Promise.all([
        api.post("/api/v1/escrow-accounts/auth/forgot", { email }).catch(() => null),
        api.post("/api/v1/escrow-signatories/auth/forgot-password", { email }).catch(() => null),
      ]);
      toast.success("If this email is registered, a reset link has been sent.");
      setForgotMode(false);
    } catch (err) { showApiError(err); }
    finally { setBusy(false); }
  };

  const submitReset = async (e) => {
    e.preventDefault();
    if (password.length < 8) return toast.error("Password must be at least 8 characters.");
    if (password !== confirm) return toast.error("Passwords don't match.");
    setBusy(true);
    try {
      // v52i — account reset emails land here too. Try the ACCOUNT endpoint
      // first (its tokens live on escrow_accounts.reset_token), then fall
      // back to the signatory endpoint (escrow_sig_password_resets).
      try {
        await api.post("/api/v1/escrow-accounts/auth/reset",
                       { token: resetToken, new_password: password });
      } catch (accErr) {
        const code = accErr?.response?.status;
        if (code !== 400 && code !== 404) throw accErr;
        await api.post("/api/v1/escrow-signatories/auth/reset-password",
                       { token: resetToken, new_password: password });
      }
      toast.success("Password reset — please sign in with the new password.");
      nav("/escrow/login");
    } catch (err) { showApiError(err); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-6"
         data-testid="escrow-login-page">
      <div className="w-full max-w-md bg-white border border-brand-navy/15 p-6">
        <div className="text-[10px] font-mono uppercase tracking-widest text-brand-navy/50">
          Escrow institution portal
        </div>
        <h1 className="text-2xl font-semibold text-brand-navy mt-1">
          {isReset ? "Pick a new password"
            : forgotMode ? "Reset your password"
            : isClaim ? "Set your password"
            : "Signatory sign-in"}
        </h1>
        <p className="text-sm text-brand-navy/60 mt-2">
          {isReset ? "Set a new password for your escrow signatory account."
            : forgotMode ? "Enter your email and we'll send a reset link that works for 1 hour."
            : isClaim
            ? "Pick a password so you can sign off on EMD releases without needing the magic link every time."
            : "Enter your work email and the password you set from the approval magic link."}
        </p>

        <form onSubmit={isReset ? submitReset : forgotMode ? submitForgot : isClaim ? submitClaim : submitLogin}
              className="mt-5 space-y-3">
          {!isReset && (
            <label className="block">
              <span className="pmc-label text-[10px]">Email</span>
              <input type="email" required value={email} autoFocus
                     onChange={(e) => setEmail(e.target.value)}
                     data-testid="escrow-login-email"
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
            </label>
          )}
          {!forgotMode && (
            <label className="block">
              <span className="pmc-label text-[10px]">
                {(isClaim || isReset) ? "Choose a password (min 8 chars)" : "Password"}
              </span>
              <input type="password" required value={password}
                     autoFocus={isReset}
                     onChange={(e) => setPassword(e.target.value)}
                     data-testid="escrow-login-password"
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
            </label>
          )}
          {(isClaim || isReset) && (
            <label className="block">
              <span className="pmc-label text-[10px]">Confirm password</span>
              <input type="password" required value={confirm}
                     onChange={(e) => setConfirm(e.target.value)}
                     data-testid="escrow-login-confirm"
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
            </label>
          )}
          <button type="submit" disabled={busy}
                  data-testid="escrow-login-submit"
                  className="w-full px-5 py-3 text-xs uppercase tracking-widest bg-brand-navy text-white disabled:opacity-50">
            {busy ? "Working…"
              : isReset ? "Save new password"
              : forgotMode ? "Email me a reset link"
              : isClaim ? "Set password & continue"
              : "Sign in"}
          </button>
        </form>

        <div className="mt-5 pt-4 border-t border-brand-navy/10 text-xs text-brand-navy/60 space-y-1">
          {!isReset && !forgotMode && !isClaim && (
            <button type="button" onClick={() => setForgotMode(true)}
                    data-testid="escrow-login-forgot"
                    className="underline hover:text-brand-navy">
              Forgot your password?
            </button>
          )}
          {forgotMode && (
            <button type="button" onClick={() => setForgotMode(false)}
                    className="underline hover:text-brand-navy">
              Back to sign-in
            </button>
          )}
          {isClaim ? (
            <div>Already set your password? <Link to="/escrow/login" className="underline">Sign in</Link>.</div>
          ) : (
            <div>New institution? <Link to="/escrow/register" className="underline">Register here</Link>.</div>
          )}
        </div>
      </div>
    </div>
  );
}
