import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { vendorApi, formatApiError, showApiError} from "@/lib/api";

export default function VendorLogin() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await vendorApi.login(email, password);
      toast.success(`Welcome, ${res.company_name || res.email}`);
      if (res.must_change_password) nav("/vendor/change-password");
      else nav(window.history.state?.usr?.next || "/vendor");
    } catch (err) {
      showApiError(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex" data-testid="vendor-login-page" style={{ background: "#ffffff" }}>
      <div className="hidden md:flex md:w-1/2 items-center justify-center p-16" style={{ background: "#0b1e3f" }}>
        <div className="max-w-md text-white">
          <div className="text-xs tracking-[0.35em] uppercase text-amber-300 mb-4">Vendor Portal</div>
          <h1 className="text-5xl font-serif font-light leading-tight mb-6">Bid on live tenders.</h1>
          <p className="text-white/70 leading-relaxed">
            Sign in with the credentials sent when your registration was approved. Once inside,
            you can browse published notices, submit bids, upload technical and commercial
            proposals, and settle the EMD securely via Stripe.
          </p>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center bg-white p-8">
        <form onSubmit={submit} className="w-full max-w-md space-y-5" data-testid="vendor-login-form">
          <div>
            <h2 className="text-2xl font-serif">Vendor sign in</h2>
            <p className="text-sm mt-1" style={{ color: "#64748b" }}>PMC Managers — Vendor Portal</p>
          </div>
          <label className="block text-sm">
            <span style={{ color: "#334155", fontWeight: 600 }}>Email</span>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full border rounded-md px-3 py-2 text-sm"
              style={{ color: "#0f172a", background: "#ffffff" }}
              data-testid="vendor-login-email" />
          </label>
          <label className="block text-sm">
            <span style={{ color: "#334155", fontWeight: 600 }}>Password</span>
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full border rounded-md px-3 py-2 text-sm"
              style={{ color: "#0f172a", background: "#ffffff" }}
              data-testid="vendor-login-password" />
          </label>
          <button type="submit" disabled={loading}
            className="w-full bg-slate-900 text-white rounded-md py-2.5 text-sm hover:bg-slate-800 disabled:opacity-60"
            data-testid="vendor-login-submit">
            {loading ? "Signing in…" : "Sign in"}
          </button>
          <div className="text-xs flex justify-between" style={{ color: "#64748b" }}>
            <Link to="/register" className="hover:underline" data-testid="vendor-login-register-link">
              Register as new vendor
            </Link>
            <Link to="/" className="hover:underline">Back to notices</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
