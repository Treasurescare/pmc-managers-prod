import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { vendorApi, formatApiError } from "@/lib/api";

export default function VendorChangePassword() {
  const nav = useNavigate();
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    vendorApi.me().catch(() => nav("/vendor/login"));
  }, [nav]);

  const submit = async (e) => {
    e.preventDefault();
    if (next !== confirm) return toast.error("Passwords don't match");
    if (next.length < 8) return toast.error("Password must be at least 8 characters");
    setLoading(true);
    try {
      await vendorApi.changePassword(current, next);
      toast.success("Password updated");
      nav("/vendor");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-slate-50 flex items-center justify-center p-8" data-testid="vendor-change-password">
      <form onSubmit={submit} className="bg-white rounded-lg shadow-sm border w-full max-w-md p-6 space-y-4">
        <h2 className="text-xl font-serif">Set your new password</h2>
        <p className="text-sm text-slate-500">You must change your temporary password before continuing.</p>
        <label className="block text-sm">
          <span>Current (temporary) password</span>
          <input type="password" required value={current} onChange={(e) => setCurrent(e.target.value)}
            className="mt-1 w-full border rounded-md px-3 py-2 text-sm" data-testid="vcp-current" />
        </label>
        <label className="block text-sm">
          <span>New password</span>
          <input type="password" required minLength={8} value={next} onChange={(e) => setNext(e.target.value)}
            className="mt-1 w-full border rounded-md px-3 py-2 text-sm" data-testid="vcp-new" />
        </label>
        <label className="block text-sm">
          <span>Confirm new password</span>
          <input type="password" required value={confirm} onChange={(e) => setConfirm(e.target.value)}
            className="mt-1 w-full border rounded-md px-3 py-2 text-sm" data-testid="vcp-confirm" />
        </label>
        <button type="submit" disabled={loading}
          className="w-full bg-slate-900 text-white rounded-md py-2.5 text-sm hover:bg-slate-800 disabled:opacity-60"
          data-testid="vcp-submit">
          {loading ? "Updating…" : "Set new password"}
        </button>
      </form>
    </div>
  );
}
