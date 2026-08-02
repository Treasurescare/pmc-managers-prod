import { useEffect, useState } from "react";
import { useNavigate, Link } from "react-router-dom";
import { toast } from "sonner";
import { staffApi, formatApiError } from "@/lib/api";

const ROLE_LABELS = {
  admin: "Admin", reviewer: "Reviewer",
  escrow_agent: "Escrow Agent", certifier: "Site Certifier",
  legal_counsel: "Legal Counsel", accounting: "Accounting Team",
  committee_member: "Bid Committee", auditor: "Auditor", support: "Support",
};

export default function StaffLogin() {
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("admin");
  const [roles, setRoles] = useState(Object.keys(ROLE_LABELS));
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    staffApi.roleChoices().then((r) => setRoles(r.roles || [])).catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    setLoading(true);
    try {
      const res = await staffApi.login(email, password, role);
      toast.success(`Signed in as ${ROLE_LABELS[role] || role}`);
      // Route to role-specific home
      if (["admin", "reviewer"].includes(res.active_role)) nav("/admin");
      else nav("/staff");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="min-h-screen flex" data-testid="staff-login-page" style={{ background: "#0b1e3f" }}>
      <div className="hidden md:flex md:w-1/2 items-center justify-center p-16">
        <div className="max-w-md text-white">
          <div className="text-xs tracking-[0.35em] uppercase text-amber-300 mb-4">Staff Portal</div>
          <h1 className="text-5xl font-serif font-light leading-tight mb-6">Run the pipeline.</h1>
          <p className="text-white/70 leading-relaxed">
            Escrow, Certifier, Legal, Accounting, Committee — one sign-in, pick the role you're
            acting as. Staff who hold multiple roles can switch by signing back in.
          </p>
        </div>
      </div>
      <div className="flex-1 flex items-center justify-center bg-white p-8">
        <form onSubmit={submit} className="w-full max-w-md space-y-5" data-testid="staff-login-form">
          <div>
            <h2 className="text-2xl font-serif">Staff sign in</h2>
            <p className="text-sm text-slate-500 mt-1">PMC Managers — internal roles</p>
          </div>
          <label className="block text-sm">
            <span>Email</span>
            <input type="email" required value={email} onChange={(e) => setEmail(e.target.value)}
              className="mt-1 w-full border rounded-md px-3 py-2 text-sm" data-testid="staff-login-email" />
          </label>
          <label className="block text-sm">
            <span>Password</span>
            <input type="password" required value={password} onChange={(e) => setPassword(e.target.value)}
              className="mt-1 w-full border rounded-md px-3 py-2 text-sm" data-testid="staff-login-password" />
          </label>
          <label className="block text-sm">
            <span>Sign in as</span>
            <select value={role} onChange={(e) => setRole(e.target.value)}
              className="mt-1 w-full border rounded-md px-3 py-2 text-sm bg-white"
              data-testid="staff-login-role">
              {roles.map((r) => <option key={r} value={r}>{ROLE_LABELS[r] || r}</option>)}
            </select>
          </label>
          <button type="submit" disabled={loading}
            className="w-full bg-slate-900 text-white rounded-md py-2.5 text-sm hover:bg-slate-800 disabled:opacity-60"
            data-testid="staff-login-submit">
            {loading ? "Signing in…" : "Sign in"}
          </button>
          <div className="text-xs text-slate-500 flex justify-between">
            <Link to="/admin/login" className="hover:underline">Admin-only login</Link>
            <Link to="/" className="hover:underline">Back to notices</Link>
          </div>
        </form>
      </div>
    </div>
  );
}
