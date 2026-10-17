import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { publicApi, registrationApi, vendorInviteApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";

export default function RegistrationStart() {
  const { t, lang } = useI18n();
  const navigate = useNavigate();
  const [email, setEmail] = useState("");
  const [companyName, setCompanyName] = useState("");
  const [country, setCountry] = useState("KZ");
  const [countries, setCountries] = useState([{ code: "KZ", name: "Kazakhstan" }]);
  const [busy, setBusy] = useState(false);
  const [sent, setSent] = useState(null);
  const [template, setTemplate] = useState({ available: false });
  const [tplBusy, setTplBusy] = useState(null); // 'view' | 'download' | null
  const revokeRef = useRef([]);

  useEffect(() => {
    publicApi.countries().then(setCountries).catch(() => {});
    vendorInviteApi.templateMeta().then(setTemplate).catch(() => {});
    return () => { revokeRef.current.forEach((u) => { try { URL.revokeObjectURL(u); } catch {} }); };
  }, []);

  /**
   * BUG-FIX (v48c-rev6) — bulletproof PDF fetch:
   * A plain `<a href download>` fails on Android Chrome / WebViews / corporate
   * proxies because they mangle Content-Disposition or refuse cross-origin
   * downloads. Instead we fetch the endpoint, materialise a Blob, and either
   * open it in a new tab (View) or trigger a real download via a blob: URL
   * (Download). This works everywhere the fetch itself succeeds.
   */
  const fetchTemplateBlob = async () => {
    const res = await fetch(vendorInviteApi.templateDownloadUrl() + "?inline=false", {
      credentials: "omit",
      cache: "no-store",
      headers: { "Accept": "application/pdf, application/octet-stream, */*" },
    });
    if (!res.ok) throw new Error(`Server returned ${res.status}`);
    const blob = await res.blob();
    if (blob.size === 0) throw new Error("Empty PDF response");
    const url = URL.createObjectURL(blob);
    revokeRef.current.push(url);
    return { url, type: blob.type || "application/pdf" };
  };

  const filename = template.file_name || "pmc-registration-form.pdf";

  const handleView = async (e) => {
    e.preventDefault();
    if (tplBusy) return;
    setTplBusy("view");
    try {
      const { url } = await fetchTemplateBlob();
      const w = window.open(url, "_blank", "noopener,noreferrer");
      if (!w) {
        // Popup blocked — fall back to same-tab navigation
        window.location.href = url;
      }
    } catch (err) {
      toast.error(`Could not fetch form: ${err.message}. Try Download instead.`);
    } finally {
      setTplBusy(null);
    }
  };

  const handleDownload = async (e) => {
    e.preventDefault();
    if (tplBusy) return;
    setTplBusy("download");
    try {
      const { url } = await fetchTemplateBlob();
      const a = document.createElement("a");
      a.href = url;
      a.download = filename;
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      a.remove();
      toast.success("Downloading blank form…");
    } catch (err) {
      toast.error(`Download failed: ${err.message}`);
    } finally {
      setTplBusy(null);
    }
  };

  const submit = async (e) => {
    e.preventDefault();
    if (!email) return;
    setBusy(true);
    try {
      const r = await registrationApi.createDraft({ email, company_name: companyName || undefined, country });
      setSent(r);
      toast.success(t("register.start_success"));
      if (r.magic_token) {
        // Fresh draft — continue immediately via the one-time token.
        setTimeout(() => navigate(`/register/resume?token=${r.magic_token}`), 800);
      } else {
        // v54f — SEC-002 path: a draft already exists for this email, so the
        // API deliberately omits the token. Navigating with it undefined sent
        // users to /register/resume?token=undefined which 404'd, bounced them
        // back here with an empty email field, and broke uploads. Instead
        // tell them to use the fresh link we just emailed.
        toast.info("A draft already exists for this email — we've re-sent your private resume link. Please continue from that email.", { duration: 12000 });
      }
    } catch (err) {
      showApiError(err);
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
              {/* v52cz — surface the canonical filename so vendors see what
                  they're about to download. Prevents repeats of the "chaman
                  raj resume.docx" leak where a stray admin upload sat here. */}
              <div className="mt-1 text-[11px] uppercase tracking-widest text-brand-navy/60 font-mono"
                   data-testid="reg-template-filename">
                {filename}
              </div>
            </div>
            <button type="button" onClick={handleView} disabled={tplBusy === "view"}
                    data-testid="reg-template-view"
                    className="px-5 py-2.5 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-50">
              {tplBusy === "view" ? "Opening…" : "View"}
            </button>
            <button type="button" onClick={handleDownload} disabled={tplBusy === "download"}
                    data-testid="reg-template-download"
                    className="px-5 py-2.5 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-soft disabled:opacity-50">
              {tplBusy === "download" ? "Downloading…" : t("register.template_download")}
            </button>
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
              {countries.map((c) => (<option key={c.code} value={c.code}>{c[`name_${lang}`] || c.name_en || c.name}</option>))}
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

          <div className="text-sm text-brand-navy/70 border-t border-brand-navy/10 pt-5" data-testid="reg-start-signin-note">
            Already registered?{" "}
            <Link to="/login" className="underline font-semibold text-brand-navy" data-testid="reg-start-signin-link">
              Sign in to your supplier account
            </Link>
          </div>

          {sent && (
            <div className="text-xs text-brand-navy/60 mt-2" data-testid="reg-start-sent">
              {sent.magic_token
                ? <>Draft created · <Link className="underline" to={`/register/resume?token=${sent.magic_token}`}>continue now</Link></>
                : <>Resume link sent to <span className="font-mono">{email}</span> — open it from your inbox to continue.</>}
            </div>
          )}
        </form>
      </main>
      <Footer />
    </div>
  );
}
