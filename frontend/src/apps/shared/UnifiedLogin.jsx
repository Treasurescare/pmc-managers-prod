import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { adminApi, staffApi, vendorApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";

/**
 * Unified web login (parallel to mobile /m).
 * Auto-detects Admin / Staff / Vendor and routes to the right dashboard.
 */
export default function UnifiedLogin() {
  const { t } = useI18n();
  const nav = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("admin");
  const [busy, setBusy] = useState(false);

  useEffect(() => { document.title = "Sign in · PMC Managers"; }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!email || !password) return toast.error("Email and password are required");
    setBusy(true);
    try {
      // 1) Staff / admin unified endpoint (respects role dropdown)
      try {
        const r = await staffApi.login(email, password, role, undefined);
        if (r && !r.mfa_required) {
          toast.success(`Signed in as ${r.active_role}`);
          if (role === "vendor") return nav("/vendor");
          if (["admin", "reviewer"].includes(r.active_role)) return nav("/admin");
          return nav("/staff");
        }
      } catch { /* try next */ }
      // 2) Admin-only fallback
      try {
        await adminApi.login(email, password);
        toast.success("Signed in as admin");
        return nav("/admin");
      } catch { /* try next */ }
      // 3) Vendor fallback
      try {
        await vendorApi.login(email, password);
        toast.success("Signed in as vendor");
        return nav("/vendor");
      } catch { /* fail */ }
      toast.error("No matching account for that email + password. Check the role dropdown.");
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col" data-testid="unified-login-page">
      <TopBar />
      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <form onSubmit={submit} className="w-full max-w-md bg-white border border-brand-navy/10 p-8 lg:p-10 space-y-4">
          <div>
            <div className="pmc-label">Global sign-in</div>
            <h1 className="font-display text-3xl text-brand-navy mt-1">Welcome back</h1>
            <p className="text-sm text-brand-navy/60 mt-2">
              One door for Admin, Staff and Vendor — pick your role and enter your credentials.
              Prefer separate pages? Use{" "}
              <a href="/admin/login" className="underline">Admin</a>,{" "}
              <a href="/staff/login" className="underline">Staff</a>, or{" "}
              <a href="/vendor/login" className="underline">Vendor</a>.
            </p>
          </div>
          <label className="block text-sm">
            <span className="pmc-label">Email</span>
            <input type="email" required value={email}
                   onChange={(e) => setEmail(e.target.value)}
                   data-testid="unified-login-email"
                   autoComplete="email"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
          </label>
          <label className="block text-sm">
            <span className="pmc-label">Password</span>
            <input type="password" required value={password}
                   onChange={(e) => setPassword(e.target.value)}
                   data-testid="unified-login-password"
                   autoComplete="current-password"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
          </label>
          <label className="block text-sm">
            <span className="pmc-label">Sign in as</span>
            <select value={role} onChange={(e) => setRole(e.target.value)}
                    data-testid="unified-login-role"
                    className="mt-1 w-full px-4 py-3 border border-brand-navy/20 text-brand-navy bg-white">
              <option value="admin">Admin</option>
              <option value="escrow_agent">Escrow Agent</option>
              <option value="certifier">Site Certifier</option>
              <option value="legal_counsel">Legal Counsel</option>
              <option value="accounting">Accounting</option>
              <option value="committee_member">Bid Committee</option>
              <option value="reviewer">Reviewer</option>
              <option value="auditor">Auditor</option>
              <option value="support">Support</option>
              <option value="vendor">Vendor</option>
            </select>
          </label>
          <button type="submit" disabled={busy} data-testid="unified-login-submit"
                  className="w-full px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
            {busy ? t("common.loading") : "Sign in"}
          </button>
          <div className="text-xs text-brand-navy/50 border-t border-brand-navy/10 pt-3 mt-2">
            Not a vendor yet? <a href="/register" className="underline">Register your company</a> ·{" "}
            <a href="/" className="underline">Browse open tenders</a>
          </div>
        </form>
      </main>
    </div>
  );
}
