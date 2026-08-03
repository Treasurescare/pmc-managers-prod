import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { publicApi, registrationApi, vendorInviteApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";

export default function RegistrationStart() {
  const { t } = useI18n();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [country, setCountry] = useState("KZ");
  const [countries, setCountries] = useState([{ code: "KZ", name: "Kazakhstan" }]);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(null);
  const [template, setTemplate] = useState({ available: false });

  useEffect(() => {
    publicApi.countries().then(setCountries).catch(() => {});
    vendorInviteApi.templateMeta().then(setTemplate).catch(() => {});
  }, []);

  const submit = async (e) => {
    e.preventDefault();
    if (!email) return;
    setBusy(true);
    try {
      const r = await registrationApi.createDraft({ email, company_name: companyName || undefined, country });
      setSent(r);
      toast.success(t("register.start_success"));
      // In pilot: redirect to the resume link so the user can continue immediately
      setTimeout(() => navigate(`/register/resume?token=${r.magic_token}`), 800);
    } catch (err) {
      toast.error(formatApiError(err));
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 lg:px-10 py-16">
        <div className="pmc-label">{t("register.kicker")}</div>
        <h1 className="font-display text-4xl lg:text-5xl mt-2 text-brand-navy leading-tight">{t("register.title")}</h1>
        <p className="text-brand-navy/70 mt-3 max-w-2xl">{t("register.lede")}</p>

        {template.available && (
          <div className="mt-6 flex flex-wrap items-center gap-3 p-4 border border-brand-navy/10 bg-white max-w-2xl"
               data-testid="reg-template-block">
            <div className="flex-1">
              <div className="pmc-label">{t("register.template_title")}</div>
              <div className="text-sm text-brand-navy/70 mt-1">
                {t("register.template_lede")}
              </div>
            </div>
            <a href={vendorInviteApi.templateDownloadUrl()} target="_blank" rel="noreferrer"
               data-testid="reg-template-download"
               className="px-5 py-2.5 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white">
              {t("register.template_download")}
            </a>
          </div>
        )}

        <form onSubmit={submit} className="mt-10 bg-white border border-brand-navy/10 p-8 lg:p-10 grid gap-6 max-w-2xl" data-testid="registration-start-form">
          <div>
            <label className="pmc-label">{t("register.start_email_label")}</label>
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              data-testid="reg-start-email"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white"
              placeholder="you@company.com"
            />
          </div>
          <div>
            <label className="pmc-label">{t("register.start_company_label")}</label>
            <input
              type="text"
              value={companyName}
              onChange={(e) => setCompanyName(e.target.value)}
              data-testid="reg-start-company"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white"
            />
          </div>
          <div>
            <label className="pmc-label">{t("register.start_country_label")}</label>
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              data-testid="reg-start-country"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white"
            >
              {countries.map((c) => (<option key={c.code} value={c.code}>{c.name}</option>))}
            </select>
          </div>

          <button
            type="submit"
            disabled={busy}
            data-testid="reg-start-submit"
            className="bg-brand-navy text-white px-8 py-4 uppercase tracking-widest text-[0.8125rem] font-semibold hover:bg-brand-navy-deep transition-colors disabled:opacity-60"
          >
            {busy ? t("common.loading") : t("register.start_submit")}
          </button>

          {sent && (
            <div className="text-xs text-brand-navy/60 mt-2" data-testid="reg-start-sent">
              Draft created · <Link className="underline" to={`/register/resume?token=${sent.magic_token}`}>continue now</Link>
            </div>
          )}
        </form>
      </main>
      <Footer />
    </div>
  );
}
