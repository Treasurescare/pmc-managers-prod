import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { adminApi, staffApi, vendorApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import ForgotUsernameModal from "@/apps/shared/ForgotUsernameModal";

/**
 * UnifiedLogin — two clearly-labelled cards so anyone landing here knows
 * exactly which door to enter. Left card: PMC EMPLOYEE (admin + staff roles).
 * Right card: VENDOR (suppliers). Each card owns its own email/password form.
 */

const EMPLOYEE_ROLES = [
  "admin", "escrow_agent", "certifier", "legal_counsel", "accounting",
  "committee_member", "reviewer", "auditor", "support",
];

export default function UnifiedLogin() {
  const { t } = useI18n();
  const nav = useNavigate();
  const [forgotOpen, setForgotOpen] = useState(false);

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col" data-testid="unified-login-page">
      <TopBar />
      <main className="flex-1 max-w-6xl mx-auto w-full px-6 lg:px-10 py-10 lg:py-16">
        <div className="text-center max-w-2xl mx-auto mb-10">
          <div className="pmc-label">{t("login.kicker")}</div>
          <h1 className="font-display text-3xl sm:text-4xl text-brand-navy mt-2">{t("login.title")}</h1>
          <p className="text-sm text-brand-navy/60 mt-3">{t("login.hub_lede")}</p>
        </div>

        <div className="grid gap-6 lg:gap-8 md:grid-cols-2">
          <EmployeeCard t={t} nav={nav} />
          <VendorCard t={t} nav={nav} />
        </div>

        <div className="mt-8 text-center text-sm text-brand-navy/70 flex flex-col sm:flex-row gap-3 sm:gap-6 justify-center">
          <button onClick={() => setForgotOpen(true)} data-testid="login-forgot-username"
                  className="underline hover:text-brand-navy">
            Forgot your username?
          </button>
          <a href="/" className="underline hover:text-brand-navy"
             data-testid="login-browse-notices">{t("login.browse_notices")}</a>
        </div>

        <ForgotUsernameModal open={forgotOpen} onClose={() => setForgotOpen(false)} />
      </main>
    </div>
  );
}

function EmployeeCard({ t, nav }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("admin");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!email || !password) return toast.error(t("login.email_pwd_required"));
    setBusy(true);
    try {
      // Employees: try staff login (any of the staff roles) first, then admin.
      try {
        const r = await staffApi.login(email, password, role, undefined);
        if (r && !r.mfa_required) {
          toast.success(`${t("login.signed_in_as")} ${r.active_role}`);
          if (["admin", "reviewer"].includes(r.active_role)) return nav("/admin");
          return nav("/staff");
        }
      } catch (err) {
        if (process.env.NODE_ENV !== "production") console.debug("staff login skipped:", err?.response?.status);
      }
      try {
        await adminApi.login(email, password);
        toast.success(`${t("login.signed_in_as")} admin`);
        return nav("/admin");
      } catch (err) {
        if (process.env.NODE_ENV !== "production") console.debug("admin login skipped:", err?.response?.status);
      }
      toast.error(t("login.employee_no_match"));
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <form onSubmit={submit}
          className="bg-white border-t-4 border-brand-navy border-x border-b border-brand-navy/10 p-8 lg:p-10 space-y-4 relative"
          data-testid="login-card-employee">
      <div className="absolute -top-3 left-8 bg-brand-navy text-white px-3 py-1 text-[10px] font-semibold uppercase tracking-widest">
        {t("login.badge_employee")}
      </div>
      <div>
        <h2 className="font-display text-2xl text-brand-navy">{t("login.card_employee_title")}</h2>
        <p className="text-sm text-brand-navy/60 mt-1">{t("login.card_employee_lede")}</p>
      </div>
      <label className="block text-sm">
        <span className="pmc-label">{t("login.email")}</span>
        <input type="email" required value={email}
               onChange={(e) => setEmail(e.target.value)}
               data-testid="login-employee-email" autoComplete="email"
               className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
      </label>
      <label className="block text-sm">
        <span className="pmc-label">{t("login.password")}</span>
        <input type="password" required value={password}
               onChange={(e) => setPassword(e.target.value)}
               data-testid="login-employee-password" autoComplete="current-password"
               className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
      </label>
      <label className="block text-sm">
        <span className="pmc-label">{t("login.role")}</span>
        <select value={role} onChange={(e) => setRole(e.target.value)}
                data-testid="login-employee-role"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20 text-brand-navy bg-white">
          {EMPLOYEE_ROLES.map((r) => (
            <option key={r} value={r}>{t(`login.role_options.${r}`)}</option>
          ))}
        </select>
      </label>
      <button type="submit" disabled={busy} data-testid="login-employee-submit"
              className="w-full px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
        {busy ? t("common.loading") : t("login.employee_submit")}
      </button>
      <div className="text-[11px] text-brand-navy/50 border-t border-brand-navy/10 pt-3">
        {t("login.direct_link")} <a href="/admin/login" className="underline">/admin/login</a> · <a href="/staff/login" className="underline">/staff/login</a>
      </div>
    </form>
  );
}

function VendorCard({ t, nav }) {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);

  const submit = async (e) => {
    e.preventDefault();
    if (!email || !password) return toast.error(t("login.email_pwd_required"));
    setBusy(true);
    try {
      await vendorApi.login(email, password);
      toast.success(`${t("login.signed_in_as")} vendor`);
      nav("/vendor");
    } catch (err) {
      toast.error(t("login.vendor_no_match"));
      if (process.env.NODE_ENV !== "production") console.debug("vendor login failed:", err?.response?.status);
    } finally { setBusy(false); }
  };

  return (
    <form onSubmit={submit}
          className="bg-white border-t-4 border-emerald-600 border-x border-b border-emerald-600/20 p-8 lg:p-10 space-y-4 relative"
          data-testid="login-card-vendor">
      <div className="absolute -top-3 left-8 bg-emerald-600 text-white px-3 py-1 text-[10px] font-semibold uppercase tracking-widest">
        {t("login.badge_vendor")}
      </div>
      <div>
        <h2 className="font-display text-2xl text-brand-navy">{t("login.card_vendor_title")}</h2>
        <p className="text-sm text-brand-navy/60 mt-1">{t("login.card_vendor_lede")}</p>
      </div>
      <label className="block text-sm">
        <span className="pmc-label">{t("login.email")}</span>
        <input type="email" required value={email}
               onChange={(e) => setEmail(e.target.value)}
               data-testid="login-vendor-email" autoComplete="email"
               className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-emerald-500 text-brand-navy bg-white" />
      </label>
      <label className="block text-sm">
        <span className="pmc-label">{t("login.password")}</span>
        <input type="password" required value={password}
               onChange={(e) => setPassword(e.target.value)}
               data-testid="login-vendor-password" autoComplete="current-password"
               className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-emerald-500 text-brand-navy bg-white" />
      </label>
      <button type="submit" disabled={busy} data-testid="login-vendor-submit"
              className="w-full px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-50">
        {busy ? t("common.loading") : t("login.vendor_submit")}
      </button>
      <div className="text-[11px] text-brand-navy/60 border-t border-brand-navy/10 pt-3">
        {t("login.register_prompt")} <a href="/register" className="underline font-semibold" data-testid="login-vendor-register">{t("login.register_link")}</a>
      </div>
    </form>
  );
}
