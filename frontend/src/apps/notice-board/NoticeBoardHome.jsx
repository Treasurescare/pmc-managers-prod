import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { publicApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";
import { toast } from "sonner";

function StatCard({ label, value }) {
  return (
    <div className="border border-brand-navy/10 bg-white p-6" data-testid={`stat-${label}`}>
      <div className="pmc-label">{label}</div>
      <div className="pmc-stat-lg mt-2 text-brand-navy">{value ?? "—"}</div>
    </div>
  );
}

function NoticeRow({ notice, t }) {
  const budget = notice.budget_amount
    ? new Intl.NumberFormat("en-US", { style: "currency", currency: notice.budget_currency || "USD", maximumFractionDigits: 0 }).format(notice.budget_amount)
    : null;
  const deadline = notice.submission_deadline ? new Date(notice.submission_deadline) : null;
  const days = deadline ? Math.max(0, Math.round((deadline - new Date()) / (1000 * 60 * 60 * 24))) : null;
  return (
    <Link
      to={`/notices/${notice.notice_ref}`}
      data-testid={`notice-row-${notice.notice_ref}`}
      className="block border border-brand-navy/10 bg-white p-6 lg:p-8 hover:border-brand-navy-soft/60 transition-colors group"
    >
      <div className="flex flex-wrap items-baseline gap-3">
        <span className="pmc-pill-navy uppercase">{notice.document_type}</span>
        <span className="pmc-label text-brand-navy-soft">{notice.notice_ref}</span>
        <span className="pmc-label text-brand-navy/60">{notice.category}</span>
        {days !== null && (
          <span className={`ml-auto text-xs font-mono tabular-nums px-2 py-0.5 border ${days <= 14 ? "border-red-500/40 text-red-600 bg-red-50" : "border-brand-navy/20 text-brand-navy/70"}`}>
            {days} {days === 1 ? "day" : "days"} left
          </span>
        )}
      </div>
      <h3 className="font-display text-xl lg:text-2xl mt-3 text-brand-navy group-hover:text-brand-navy-soft transition-colors">
        {notice.title}
      </h3>
      <p className="text-sm text-brand-navy/70 mt-2 line-clamp-2">{notice.description}</p>
      <div className="mt-4 flex flex-wrap items-center gap-x-6 gap-y-1 text-xs text-brand-navy/60">
        <span><span className="pmc-label">{t("notice.country")}:</span> {notice.delivery_country}</span>
        {budget && <span><span className="pmc-label">{t("notice.budget")}:</span> <span className="font-mono">{budget}</span></span>}
        {deadline && (
          <span>
            <span className="pmc-label">{t("notice.submission_deadline")}:</span>{" "}
            <span className="font-mono">{deadline.toISOString().split("T")[0]}</span>
          </span>
        )}
      </div>
    </Link>
  );
}

export default function NoticeBoardHome() {
  const { t } = useI18n();
  const [notices, setNotices] = useState([]);
  const [stats, setStats] = useState(null);
  const [filter, setFilter] = useState("all");
  const [country, setCountry] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    const params = {};
    if (filter !== "all") params.document_type = filter;
    if (country) params.country = country;
    Promise.all([
      publicApi.listNotices(params),
      publicApi.publicStats().catch(() => ({})),
    ])
      .then(([lst, s]) => {
        if (cancelled) return;
        setNotices(lst.items || []);
        setStats(s);
      })
      .catch((e) => !cancelled && toast.error(formatApiError(e)))
      .finally(() => !cancelled && setLoading(false));
    return () => { cancelled = true; };
  }, [filter, country]);

  const countries = useMemo(() => {
    const set = new Set(notices.map((n) => n.delivery_country).filter(Boolean));
    return Array.from(set).sort();
  }, [notices]);

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />

      {/* Hero */}
      <section className="border-b border-brand-navy/10 bg-brand-navy text-white">
        <div className="max-w-7xl mx-auto px-6 lg:px-10 py-16 lg:py-24 grid gap-10 lg:grid-cols-[5fr_7fr] lg:gap-16 items-start">
          <div>
            <div className="pmc-label" style={{ color: "rgba(255,255,255,0.5)" }}>{t("home.hero_kicker")}</div>
            <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl leading-tight mt-4">
              {t("home.hero_headline")}
            </h1>
            <p className="text-white/70 mt-6 text-base max-w-xl">{t("home.hero_lede")}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <a href="#notices" data-testid="hero-cta-notices" className="bg-brand-navy-soft text-white px-8 py-4 uppercase tracking-widest text-[0.8125rem] font-semibold shadow-brand-btn hover:bg-brand-navy-soft/90 transition-colors">
                {t("home.cta_view_notices")}
              </a>
              <Link to="/register" data-testid="hero-cta-register" className="border border-white/40 text-white px-8 py-4 uppercase tracking-widest text-[0.8125rem] font-semibold hover:bg-white/10 transition-colors">
                {t("home.cta_register")}
              </Link>
            </div>
          </div>
          <div className="grid grid-cols-3 gap-4">
            <StatCard label={t("home.stats_notices")} value={stats?.notices_published ?? 0} />
            <StatCard label={t("home.stats_suppliers")} value={stats?.suppliers_approved ?? 0} />
            <StatCard label={t("home.stats_packages")} value={stats?.packages_total ?? 0} />
          </div>
        </div>
      </section>

      {/* Filters + list */}
      <section id="notices" className="flex-1 max-w-7xl mx-auto w-full px-6 lg:px-10 py-14">
        <div className="flex flex-wrap items-center justify-between gap-4">
          <div>
            <div className="pmc-label">Open notices</div>
            <h2 className="font-display text-3xl mt-1 text-brand-navy">All published tender notices</h2>
          </div>
          <div className="flex items-center gap-2 flex-wrap">
            {[
              { code: "all", label: t("home.filters_all") },
              { code: "tender", label: t("home.filters_tender") },
              { code: "rfp", label: t("home.filters_rfp") },
              { code: "rfq", label: t("home.filters_rfq") },
            ].map((f) => (
              <button
                key={f.code}
                type="button"
                data-testid={`filter-${f.code}`}
                onClick={() => setFilter(f.code)}
                className={
                  "px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border transition-colors " +
                  (filter === f.code
                    ? "bg-brand-navy text-white border-brand-navy"
                    : "bg-white text-brand-navy border-brand-navy/20 hover:border-brand-navy-soft/60")
                }
              >
                {f.label}
              </button>
            ))}
            <select
              value={country}
              onChange={(e) => setCountry(e.target.value)}
              data-testid="filter-country"
              className="px-3 py-2 text-[12px] uppercase tracking-widest border border-brand-navy/20 bg-white text-brand-navy focus:outline-none focus:border-brand-navy-soft"
            >
              <option value="">{t("home.filters_country_all")}</option>
              {countries.map((c) => (<option key={c} value={c}>{c}</option>))}
            </select>
          </div>
        </div>

        <div className="mt-8 grid gap-4" data-testid="notice-list">
          {loading && <div className="text-brand-navy/60 py-16 text-center">{t("common.loading")}</div>}
          {!loading && notices.length === 0 && (
            <div className="border border-dashed border-brand-navy/20 bg-white p-16 text-center text-brand-navy/60">
              {t("home.empty_state")}
            </div>
          )}
          {notices.map((n) => (<NoticeRow key={n.id} notice={n} t={t} />))}
        </div>
      </section>

      <Footer />
    </div>
  );
}
