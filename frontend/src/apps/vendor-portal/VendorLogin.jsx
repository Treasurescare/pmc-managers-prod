import { useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { vendorApi, formatApiError } from "@/lib/api";

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
      else nav("/vendor");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex" data-testid="vendor-login-page" style={{ background: "#0b1e3f" }}>
      <div className="hidden md:flex md:w-1/2 items-center justify-center p-16">
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
            <p className="text-sm text-slate-500 mt-1">PMC Managers — Vendor Portal</p>
          </div>
          <label className="block text-sm">
            <span className="text-slate-700">Email</span>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full border rounded-md px-3 py-2 text-sm"
              data-testid="vendor-login-email" />
          </label>
          <label className="block text-sm">
            <span className="text-slate-700">Password</span>
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full border rounded-md px-3 py-2 text-sm"
              data-testid="vendor-login-password" />
          </label>
          <button type="submit" disabled={loading}
            className="w-full bg-slate-900 text-white rounded-md py-2.5 text-sm hover:bg-slate-800 disabled:opacity-60"
            data-testid="vendor-login-submit">
            {loading ? "Signing in…" : "Sign in"}
          </button>
          <div className="text-xs text-slate-500 flex justify-between">
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
