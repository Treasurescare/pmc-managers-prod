import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { adminApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import { toast } from "sonner";
import useTenantSkin from "@/apps/shared/useTenantSkin";

export default function AdminLogin() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [busy, setBusy] = useState(false);
  useTenantSkin();

  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await adminApi.login(email, password);
      toast.success("Signed in");
      navigate("/admin");
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-brand-navy text-white flex flex-col">
      <TopBar dark />
      <main className="flex-1 grid lg:grid-cols-[5fr_7fr]">
        <section className="hidden lg:flex flex-col justify-between p-14 border-r border-white/10">
          <div>
            <div className="pmc-label" style={{ color: "rgba(255,255,255,0.5)" }}>PMC Admin Console</div>
            <h1 className="font-display text-4xl lg:text-5xl mt-3 leading-tight">
              Manage registrations, packages and notices for the Kazakhstan programme.
            </h1>
          </div>
          <div className="text-white/50 text-xs">v2 · Pilot Environment · Cognito MFA activates in Phase 2 (AWS).</div>
        </section>

        <section className="flex items-center justify-center p-8">
          <form onSubmit={submit} className="w-full max-w-md bg-white border border-brand-navy/10 p-10 text-brand-navy" data-testid="admin-login-form">
            <div className="pmc-label">Access</div>
            <h2 className="font-display text-3xl mt-1">{t("admin.login_title")}</h2>

            <label className="block mt-8">
              <span className="pmc-label">{t("admin.login_email")}</span>
              <input
                type="email"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                data-testid="admin-login-email"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft"
              />
            </label>
            <label className="block mt-4">
              <span className="pmc-label">{t("admin.login_password")}</span>
              <input
                type="password"
                required
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                data-testid="admin-login-password"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft"
              />
            </label>

            <button
              type="submit"
              disabled={busy}
              data-testid="admin-login-submit"
              className="mt-8 w-full bg-brand-navy text-white px-8 py-4 uppercase tracking-widest text-[0.8125rem] font-semibold hover:bg-brand-navy-deep transition-colors disabled:opacity-60"
            >
              {busy ? t("common.loading") : t("admin.login_submit")}
            </button>
          </form>
        </section>
      </main>
    </div>
  );
}
