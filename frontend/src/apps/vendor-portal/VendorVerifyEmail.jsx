import { useEffect, useState } from "react";
import { useParams, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";

/**
 * Vendor email-verify + set-password landing page.
 * Reached from the invite email link `/vendor/verify/:token`.
 */
export default function VendorVerifyEmail() {
  const { token } = useParams();
  const nav = useNavigate();
  const [meta, setMeta] = useState(null);
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState("");

  useEffect(() => {
    api.get(`/api/v1/vendors/verify/${token}`)
      .then((r) => setMeta(r.data))
      .catch((e) => setError(formatApiError(e)));
  }, [token]);

  const submit = async (e) => {
    e.preventDefault();
    if (password.length < 8) return toast.error("Password must be at least 8 characters");
    if (password !== confirm) return toast.error("Passwords do not match");
    setBusy(true);
    try {
      await api.post(`/api/v1/vendors/verify/${token}/complete`, { password });
      toast.success("Email verified — please sign in with your new password");
      nav("/vendor/login");
    } catch (e2) { toast.error(formatApiError(e2)); }
    finally { setBusy(false); }
  };

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6">
        <div className="max-w-md w-full bg-white border rounded-lg p-8 text-center">
          <h1 className="font-serif text-2xl text-red-700">Link invalid or expired</h1>
          <p className="text-sm text-slate-600 mt-3">{error}</p>
          <button onClick={() => nav("/vendor/login")}
                  className="mt-6 px-4 py-2 bg-slate-900 text-white text-sm rounded">Go to sign-in</button>
        </div>
      </div>
    );
  }
  if (!meta) return <div className="p-10 text-slate-500">Loading…</div>;

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 p-6"
         data-testid="vendor-verify-page">
      <form onSubmit={submit} className="max-w-md w-full bg-white border rounded-lg p-8 space-y-4">
        <div className="pmc-label">Vendor onboarding</div>
        <h1 className="font-serif text-2xl">Welcome, {meta.company_name || meta.email}</h1>
        <p className="text-sm text-slate-600">
          You've been invited as vendor <strong>{meta.vendor_ref}</strong>.
          Set a password below to activate your account.
        </p>
        <div className="text-xs bg-slate-100 rounded p-2 font-mono">Email: {meta.email}</div>
        <label className="block text-sm">
          <span>New password (min 8 chars)</span>
          <input type="password" required value={password}
                 onChange={(e) => setPassword(e.target.value)}
                 data-testid="verify-password"
                 className="mt-1 w-full px-3 py-2 border rounded" />
        </label>
        <label className="block text-sm">
          <span>Confirm password</span>
          <input type="password" required value={confirm}
                 onChange={(e) => setConfirm(e.target.value)}
                 data-testid="verify-confirm"
                 className="mt-1 w-full px-3 py-2 border rounded" />
        </label>
        <button type="submit" disabled={busy} data-testid="verify-submit"
                className="w-full bg-slate-900 text-white py-3 text-sm font-semibold rounded disabled:opacity-50">
          {busy ? "Activating…" : "Verify email & activate"}
        </button>
      </form>
    </div>
  );
}
