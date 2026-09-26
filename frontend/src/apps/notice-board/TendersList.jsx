import { useEffect, useMemo, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { publicApi, formatApiError } from "@/lib/api";
import { useUiTheme } from "@/context/UiThemeContext";
import TopBar from "@/apps/shared/TopBar";
import PmcFooter from "@/components/PmcFooter";

/** Live vs Completed tenders — public list page.  Route: /tenders/:mode
 *  mode = "live"       → publish=true AND deadline > now
 *  mode = "completed"  → publish=true AND (deadline <= now OR award_status=='awarded')
 *  mode = "all"        → any published */
export default function TendersList() {
  const { mode = "live" } = useParams();
  const { isE } = useUiTheme();
  const [notices, setNotices] = useState([]);
  const [q, setQ] = useState("");
  const [country, setCountry] = useState("");
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    publicApi.listNotices({ limit: 200 })
      .then((r) => setNotices(r.items || r || []))
      .catch((e) => setErr(formatApiError(e)))
      .finally(() => setLoading(false));
  }, []);

  const now = new Date().toISOString();
  const filtered = useMemo(() => {
    return (notices || []).filter((n) => {
      if (!n.is_published) return false;
      const past = (n.submission_deadline || "9999") <= now;
      if (mode === "live" && past) return false;
      if (mode === "completed" && !past && n.award_status !== "awarded") return false;
      if (country && (n.delivery_country || "").toUpperCase() !== country.toUpperCase()) return false;
      if (q) {
        const s = q.toLowerCase();
        if (!(n.title || "").toLowerCase().includes(s) &&
            !(n.notice_ref || "").toLowerCase().includes(s) &&
            !(n.category || "").toLowerCase().includes(s)) return false;
      }
      return true;
    });
  }, [notices, mode, q, country, now]);

  const title = mode === "completed" ? "Completed tenders"
              : mode === "all"       ? "All published notices"
              : "Live tenders";
  const subtitle = mode === "completed"
    ? "Past deadline or already awarded — kept public for audit + benchmarking"
    : mode === "all"
      ? "Everything that has ever been published"
      : "Open for bidding right now — click any card for full documents";

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col" data-testid={`page-tenders-${mode}`} data-ui={isE ? "e" : undefined}>
      <TopBar />

      {/* Option E — hero band (opt-in) matching E-Tenders.html */}
      {isE && (
        <section className="e-hero-band" data-testid="tenders-hero-e">
          <svg aria-hidden="true" fill="none" viewBox="0 0 1440 440" className="absolute right-0 top-0 h-full w-full pointer-events-none opacity-90" preserveAspectRatio="xMaxYMid slice">
            <circle stroke="rgba(210,180,106,0.20)" r="170" cy="250" cx="1180" />
            <circle stroke="rgba(210,180,106,0.14)" r="270" cy="250" cx="1180" />
            <circle stroke="rgba(210,180,106,0.09)" r="390" cy="250" cx="1180" />
            <circle stroke="rgba(210,180,106,0.05)" r="530" cy="250" cx="1180" />
          </svg>
          <div className="e-hero-inner">
            <div className="grid gap-10 lg:grid-cols-[1fr_420px] lg:gap-16 items-end">
              <div className="flex flex-col gap-4">
                <span className="e-hero-kicker">The register · Open to all bidders</span>
                <h1 className="e-hero-title text-5xl md:text-6xl lg:text-[72px]">
                  Live <em>tenders</em>
                </h1>
                <p className="e-hero-sub">Every notice is published to all registered vendors at the same moment. Deadlines are fixed to server time and recorded on the audit log.</p>
              </div>
              {(() => {
                const upcoming = (notices || [])
                  .filter((n) => n.is_published && n.submission_deadline && (new Date(n.submission_deadline) - new Date()) > 0)
                  .sort((a, b) => new Date(a.submission_deadline) - new Date(b.submission_deadline))[0];
                if (!upcoming) return <div />;
                const rem = new Date(upcoming.submission_deadline) - new Date();
                const days = Math.floor(rem / (1000*60*60*24));
                const hours = Math.floor((rem / (1000*60*60)) % 24);
                const mins = Math.floor((rem / (1000*60)) % 60);
                return (
                  <div className="e-live-board" data-testid="tenders-next-to-close">
                    <div className="e-live-head">
                      <span>Next to close</span>
                      <span className="inline-flex items-center gap-1.5 text-[#8FD9C4] normal-case tracking-normal">
                        <span className="e-live-dot" /> LIVE
                      </span>
                    </div>
                    <Link to={`/notices/${upcoming.notice_ref}`} className="e-live-row" style={{gridTemplateColumns:"1fr auto"}}>
                      <span className="min-w-0">
                        <span className="e-live-ref block">{upcoming.notice_ref} · {(upcoming.category || "—").slice(0,10).toUpperCase()} · {upcoming.delivery_country || "—"}</span>
                        <span className="e-live-title block mt-1">{upcoming.title}</span>
                      </span>
                      <span className="e-live-count font-mono text-lg">
                        {String(days).padStart(2,"0")}d {String(hours).padStart(2,"0")}:{String(mins).padStart(2,"0")}
                      </span>
                    </Link>
                  </div>
                );
              })()}
            </div>
          </div>
        </section>
      )}

      <main className="flex-1 max-w-6xl mx-auto w-full px-6 lg:px-10 pt-12 pb-16">
        <div className="pmc-label text-brand-gold">Public Notice Board</div>
        <h1 className="font-display text-4xl lg:text-5xl text-brand-navy mt-2">{title}</h1>
        <p className="mt-3 text-brand-navy/70 max-w-2xl">{subtitle}</p>

        {/* Mode switcher */}
        <div className="mt-6 flex flex-wrap gap-2 text-[11px] uppercase tracking-widest">
          {[["live","Live"], ["completed","Completed"], ["all","All notices"]].map(([m, l]) => (
            <Link key={m} to={`/tenders/${m}`} data-testid={`tenders-mode-${m}`}
              className={"px-4 py-2 border " + (mode === m
                ? "bg-brand-navy text-white border-brand-navy"
                : "bg-white text-brand-navy/70 border-brand-navy/20 hover:border-brand-navy")}>
              {l}
            </Link>
          ))}
        </div>

        {/* Filter */}
        <div className="mt-4 grid gap-3 md:grid-cols-[2fr_1fr] items-stretch">
          <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search title, reference, category…"
                 data-testid="tenders-search"
                 className="px-4 py-3 border border-brand-navy/20 bg-white text-sm" />
          <input value={country} onChange={(e) => setCountry(e.target.value.toUpperCase())}
                 placeholder="Country (KZ, IN, GB…)" maxLength={2}
                 data-testid="tenders-country-filter"
                 className="px-4 py-3 border border-brand-navy/20 bg-white text-sm uppercase" />
        </div>

        {err && <div className="mt-6 text-red-700 bg-red-50 border border-red-200 px-4 py-2 text-sm">{err}</div>}
        {loading ? (
          <div className="mt-14 text-brand-navy/50 text-sm">Loading tenders…</div>
        ) : filtered.length === 0 ? (
          <div className="mt-14 border border-dashed border-brand-navy/20 bg-white p-14 text-center text-brand-navy/50">
            No {mode === "completed" ? "completed" : mode === "all" ? "" : "live"} tenders match this filter.
          </div>
        ) : (
          <div className="mt-8 grid gap-5 md:grid-cols-2" data-testid="tenders-grid">
            {filtered.map((n) => {
              const past = (n.submission_deadline || "9999") <= now;
              const isAwarded = n.award_status === "awarded";
              const chip = isAwarded ? ["bg-brand-navy text-white", "Awarded"]
                        : past       ? ["bg-slate-200 text-slate-700", "Closed"]
                                     : ["bg-emerald-100 text-emerald-800", "Live"];
              return (
                <Link key={n.id} to={`/notices/${n.notice_ref}`}
                      data-testid={`tender-card-${n.notice_ref}`}
                      className="group block bg-white border border-brand-navy/10 hover:border-brand-navy/40 hover:shadow-lg transition-all p-6">
                  <div className="flex items-baseline gap-3 flex-wrap">
                    <span className="font-mono text-xs text-brand-navy-soft">{n.notice_ref}</span>
                    <span className="pmc-pill uppercase text-[10px]">{n.document_type}</span>
                    <span className={`text-[10px] uppercase tracking-widest px-2 py-0.5 ${chip[0]}`}>● {chip[1]}</span>
                    <span className="ml-auto text-xs text-brand-navy/50">{n.delivery_country || "—"}</span>
                  </div>
                  <div className="font-display text-xl text-brand-navy mt-3 group-hover:text-brand-navy-soft">
                    {n.title}
                  </div>
                  <div className="mt-2 text-sm text-brand-navy/70 line-clamp-2">
                    {(n.description || "").slice(0, 180)}{(n.description || "").length > 180 ? "…" : ""}
                  </div>
                  <div className="mt-4 flex items-baseline flex-wrap gap-4 text-xs text-brand-navy/60">
                    {n.budget_amount != null && (
                      <div><span className="pmc-label">Budget</span>
                        <div className="text-brand-navy font-semibold mt-0.5">{n.budget_currency} {Number(n.budget_amount).toLocaleString()}</div>
                      </div>)}
                    {n.submission_deadline && (
                      <div><span className="pmc-label">Deadline</span>
                        <div className="text-brand-navy font-mono mt-0.5">{n.submission_deadline.slice(0, 10)}</div>
                      </div>)}
                    {n.category && (
                      <div><span className="pmc-label">Category</span>
                        <div className="text-brand-navy mt-0.5">{n.category}</div>
                      </div>)}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
      </main>
      <PmcFooter />
    </div>
  );
}
