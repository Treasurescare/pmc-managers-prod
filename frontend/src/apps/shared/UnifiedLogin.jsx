import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { adminApi, staffApi, vendorApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";

const ROLE_KEYS = [
  "admin", "escrow_agent", "certifier", "legal_counsel", "accounting",
  "committee_member", "reviewer", "auditor", "support", "vendor",
];

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
    if (!email || !password) return toast.error(t("login.email_pwd_required"));
    setBusy(true);
    try {
      try {
        const r = await staffApi.login(email, password, role, undefined);
        if (r && !r.mfa_required) {
          toast.success(`${t("login.signed_in_as")} ${r.active_role}`);
          if (role === "vendor") return nav("/vendor");
          if (["admin", "reviewer"].includes(r.active_role)) return nav("/admin");
          return nav("/staff");
        }
      } catch (err) {
        // Expected 401 when this login isn't a staff account — fall through.
        if (process.env.NODE_ENV !== "production") console.debug("staff login skipped:", err?.response?.status);
      }
      try {
        await adminApi.login(email, password);
        toast.success(`${t("login.signed_in_as")} admin`);
        return nav("/admin");
      } catch (err) {
        if (process.env.NODE_ENV !== "production") console.debug("admin login skipped:", err?.response?.status);
      }
      try {
        await vendorApi.login(email, password);
        toast.success(`${t("login.signed_in_as")} vendor`);
        return nav("/vendor");
      } catch (err) {
        if (process.env.NODE_ENV !== "production") console.debug("vendor login skipped:", err?.response?.status);
      }
      toast.error(t("login.no_match"));
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col" data-testid="unified-login-page">
      <TopBar />
      <main className="flex-1 flex items-center justify-center px-6 py-12">
        <form onSubmit={submit} className="w-full max-w-md bg-white border border-brand-navy/10 p-8 lg:p-10 space-y-4">
          <div>
            <div className="pmc-label">{t("login.kicker")}</div>
            <h1 className="font-display text-3xl text-brand-navy mt-1">{t("login.title")}</h1>
            <p className="text-sm text-brand-navy/60 mt-2">
              {t("login.intro_before")}
              <a href="/admin/login" className="underline">{t("login.intro_admin")}</a>,{" "}
              <a href="/staff/login" className="underline">{t("login.intro_staff")}</a>, or{" "}
              <a href="/vendor/login" className="underline">{t("login.intro_vendor")}</a>.
            </p>
          </div>
          <label className="block text-sm">
            <span className="pmc-label">{t("login.email")}</span>
            <input type="email" required value={email}
                   onChange={(e) => setEmail(e.target.value)}
                   data-testid="unified-login-email"
                   autoComplete="email"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
          </label>
          <label className="block text-sm">
            <span className="pmc-label">{t("login.password")}</span>
            <input type="password" required value={password}
                   onChange={(e) => setPassword(e.target.value)}
                   data-testid="unified-login-password"
                   autoComplete="current-password"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
          </label>
          <label className="block text-sm">
            <span className="pmc-label">{t("login.role")}</span>
            <select value={role} onChange={(e) => setRole(e.target.value)}
                    data-testid="unified-login-role"
                    className="mt-1 w-full px-4 py-3 border border-brand-navy/20 text-brand-navy bg-white">
              {ROLE_KEYS.map((r) => (
                <option key={r} value={r}>{t(`login.role_options.${r}`)}</option>
              ))}
            </select>
          </label>
          <button type="submit" disabled={busy} data-testid="unified-login-submit"
                  className="w-full px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
            {busy ? t("common.loading") : t("login.submit")}
          </button>
          <div className="text-xs text-brand-navy/50 border-t border-brand-navy/10 pt-3 mt-2">
            {t("login.register_prompt")} <a href="/register" className="underline">{t("login.register_link")}</a> ·{" "}
            <a href="/" className="underline">{t("login.browse_notices")}</a>
          </div>
        </form>
      </main>
    </div>
  );
}
