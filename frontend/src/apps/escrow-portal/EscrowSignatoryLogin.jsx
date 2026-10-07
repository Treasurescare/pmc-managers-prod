import { useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { api, showApiError } from "@/lib/api";

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
  const iid = params.get("iid") || "";
  const token = params.get("token") || "";

  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  const submitLogin = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await api.post("/api/v1/escrow-signatories/auth/login", { email, password });
      toast.success("Signed in · escrow signatory");
      nav("/escrow/me");
    } catch (err) { showApiError(err); }
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
      await api.post("/api/v1/escrow-signatories/auth/login", { email, password });
      nav("/escrow/me");
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
          {isClaim ? "Set your password" : "Signatory sign-in"}
        </h1>
        <p className="text-sm text-brand-navy/60 mt-2">
          {isClaim
            ? "Pick a password so you can sign off on EMD releases without needing the magic link every time."
            : "Enter your work email and the password you set from the approval magic link."}
        </p>

        <form onSubmit={isClaim ? submitClaim : submitLogin} className="mt-5 space-y-3">
          <label className="block">
            <span className="pmc-label text-[10px]">Email</span>
            <input type="email" required value={email} autoFocus
                   onChange={(e) => setEmail(e.target.value)}
                   data-testid="escrow-login-email"
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          <label className="block">
            <span className="pmc-label text-[10px]">
              {isClaim ? "Choose a password (min 8 chars)" : "Password"}
            </span>
            <input type="password" required value={password}
                   onChange={(e) => setPassword(e.target.value)}
                   data-testid="escrow-login-password"
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
          </label>
          {isClaim && (
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
            {busy ? "Working…" : (isClaim ? "Set password & continue" : "Sign in")}
          </button>
        </form>

        <div className="mt-5 pt-4 border-t border-brand-navy/10 text-xs text-brand-navy/60">
          {isClaim ? (
            <>Already set your password? <Link to="/escrow/login" className="underline">Sign in</Link>.</>
          ) : (
            <>New institution? <Link to="/escrow/register" className="underline">Register here</Link>.</>
          )}
        </div>
      </div>
    </div>
  );
}
