import { useEffect, useMemo, useState } from "react";
import { Link, useParams, useSearchParams } from "react-router-dom";
import { publicApi, formatApiError } from "@/lib/api";
import { contractTypeOptions } from "@/components/taxonomy";
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
  // v56s — deep-linkable filters: Sector / Contract type / UNSPSC-category /
  // Country / free text are all restored from (and written back to) the query
  // string so a filtered board can be shared or survive a refresh.
  const [searchParams, setSearchParams] = useSearchParams();
  const [notices, setNotices] = useState([]);
  const [q, setQ] = useState(searchParams.get("q") || "");
  const [country, setCountry] = useState((searchParams.get("country") || "").toUpperCase());
  const [sector, setSector] = useState(searchParams.get("sector") || "");
  const [contractType, setContractType] = useState(searchParams.get("contract") || "");
  const [category, setCategory] = useState(searchParams.get("category") || "");
  const [sectors, setSectors] = useState([]);
  const [contractTypes, setContractTypes] = useState([]);
  const [err, setErr] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    publicApi.listNotices({ limit: 200 })
      .then((r) => setNotices(r.items || r || []))
      .catch((e) => setErr(formatApiError(e)))
      .finally(() => setLoading(false));
    publicApi.listSectorsPublic().then((r) => setSectors(Array.isArray(r) ? r : [])).catch(() => setSectors([]));
    publicApi.listContractTypesPublic().then((r) => setContractTypes(Array.isArray(r) ? r : [])).catch(() => setContractTypes([]));
  }, []);

  // Mirror live filter state into the URL query string (deep-link / shareable).
  useEffect(() => {
    const next = {};
    if (q) next.q = q;
    if (country) next.country = country;
    if (sector) next.sector = sector;
    if (contractType) next.contract = contractType;
    if (category) next.category = category;
    setSearchParams(next, { replace: true });
  }, [q, country, sector, contractType, category, setSearchParams]);

  const clearFilters = () => { setQ(""); setCountry(""); setSector(""); setContractType(""); setCategory(""); };
  const activeCount = [q, country, sector, contractType, category].filter(Boolean).length;

  const now = new Date().toISOString();
  const filtered = useMemo(() => {
    return (notices || []).filter((n) => {
      if (!n.is_published) return false;
      const past = (n.submission_deadline || "9999") <= now;
      if (mode === "live" && past) return false;
      if (mode === "completed" && !past && n.award_status !== "awarded") return false;
      if (country && (n.delivery_country || "").toUpperCase() !== country.toUpperCase()) return false;
      if (sector && (n.sector_code || "") !== sector) return false;
      if (contractType && (n.contract_type_code || "") !== contractType) return false;
      if (category) {
        const c = category.toLowerCase();
        if (!(n.category || "").toLowerCase().includes(c) &&
            !(n.category_code || "").toLowerCase().includes(c)) return false;
      }
      if (q) {
        const s = q.toLowerCase();
        if (!(n.title || "").toLowerCase().includes(s) &&
            !(n.notice_ref || "").toLowerCase().includes(s) &&
            !(n.category || "").toLowerCase().includes(s)) return false;
      }
      return true;
    });
  }, [notices, mode, q, country, sector, contractType, category, now]);

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
                  {mode === "completed" ? <>Completed <em>tenders</em></>
                    : mode === "all" ? <>All <em>notices</em></>
                    : <>Live <em>tenders</em></>}
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
        {isE ? (
          <div className="grid gap-6 lg:gap-10 lg:grid-cols-[240px_minmax(0,1fr)] items-start">
            {/* Refine aside — matches E-Tenders.html */}
            <aside className="e-refine-aside" data-testid="tenders-refine-aside" aria-label="Filters">
              <div className="e-refine-head">
                <h2 className="e-refine-title">Refine</h2>
                <span className="text-sm text-[#4F5C55]">{activeCount ? `${activeCount} applied` : "0 applied"}</span>
              </div>
              <div className="flex flex-col gap-2">
                <div className="e-refine-label">
                  <span className="e-numeral">I</span>
                  <span className="e-tag">Search</span>
                </div>
                <input value={q} onChange={(e) => setQ(e.target.value)} data-testid="tenders-search"
                       placeholder="Keyword, ref…" className="h-11 px-4 rounded-full border border-[#C9C1AA] bg-[#FBF9F3] text-sm outline-none focus:border-[#0F3B2E]" />
              </div>
              <div className="flex flex-col gap-2">
                <label className="e-refine-label" htmlFor="e-f-sector">
                  <span className="e-numeral">II</span>
                  <span className="e-tag">Sector</span>
                </label>
                <select id="e-f-sector" value={sector}
                        onChange={(e) => setSector(e.target.value)}
                        data-testid="tenders-sector-filter"
                        className="h-11 px-4 rounded-full border border-[#C9C1AA] bg-[#FBF9F3] text-sm outline-none focus:border-[#0F3B2E]">
                  <option value="">All sectors</option>
                  {sectors.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="e-refine-label" htmlFor="e-f-contract">
                  <span className="e-numeral">III</span>
                  <span className="e-tag">Contract type</span>
                </label>
                <select id="e-f-contract" value={contractType}
                        onChange={(e) => setContractType(e.target.value)}
                        data-testid="tenders-contract-filter"
                        className="h-11 px-4 rounded-full border border-[#C9C1AA] bg-[#FBF9F3] text-sm outline-none focus:border-[#0F3B2E]">
                  <option value="">All contract types</option>
                  {contractTypeOptions(contractTypes)}
                </select>
              </div>
              <div className="flex flex-col gap-2">
                <label className="e-refine-label" htmlFor="e-f-category">
                  <span className="e-numeral">IV</span>
                  <span className="e-tag">Category (UNSPSC)</span>
                </label>
                <input id="e-f-category" value={category} onChange={(e) => setCategory(e.target.value)}
                       placeholder="e.g. solar, construction…"
                       data-testid="tenders-category-filter"
                       className="h-11 px-4 rounded-full border border-[#C9C1AA] bg-[#FBF9F3] text-sm outline-none focus:border-[#0F3B2E]" />
              </div>
              <div className="flex flex-col gap-2">
                <label className="e-refine-label" htmlFor="e-f-country">
                  <span className="e-numeral">V</span>
                  <span className="e-tag">Country</span>
                </label>
                <input id="e-f-country" value={country} onChange={(e) => setCountry(e.target.value.toUpperCase())}
                       placeholder="KZ, IN, GB…" maxLength={2}
                       data-testid="tenders-country-filter"
                       className="h-11 px-4 rounded-full border border-[#C9C1AA] bg-[#FBF9F3] text-sm outline-none uppercase focus:border-[#0F3B2E]" />
              </div>
              <button
                type="button"
                onClick={clearFilters}
                data-testid="tenders-clear-filters"
                className="h-11 rounded-full border border-[#14261F] text-sm font-medium hover:bg-[#14261F] hover:text-[#F3EFE4] transition-colors"
              >
                Clear all filters
              </button>
              <div className="border-t border-[#C9C1AA] pt-4 flex flex-col gap-3 text-sm text-[#14261F]">
                <h3 className="m-0 text-xs font-medium tracking-[0.2em] text-[#3B4A43] uppercase">Status key</h3>
                <span className="flex gap-3 items-center"><span className="w-2 h-2 rounded-full bg-[#0F3B2E]" style={{boxShadow:"0 0 0 4px rgba(15,59,46,0.14)"}} />Open for bids</span>
                <span className="flex gap-3 items-center"><span className="w-2 h-2 rounded-full bg-[#B8741A]" style={{boxShadow:"0 0 0 4px #F6E6CC"}} />Closing within 7 days</span>
                <span className="flex gap-3 items-center"><span className="inline-block w-3 h-3 rounded-full" style={{border:"1.5px dashed #4F5C55"}} />Under evaluation</span>
                <span className="flex gap-3 items-center"><span className="w-3.5 h-3.5 rounded-full bg-[#0F3B2E] flex items-center justify-center"><svg width="8" height="8" fill="none" stroke="#D2B46A" strokeWidth="3" viewBox="0 0 24 24"><path d="M5 12l5 5L19 7" /></svg></span>Awarded</span>
              </div>
            </aside>

            <div className="flex flex-col gap-6 min-w-0">
              {/* Tab-pill switcher — All / Live / Completed */}
              <div className="flex justify-between items-center flex-wrap gap-3">
                <div className="e-tab-pill-wrap" role="tablist" aria-label="Tender status">
                  {[["live","Live"], ["completed","Completed"], ["all","All"]].map(([m, l]) => (
                    <Link key={m} to={`/tenders/${m}`} data-testid={`tenders-mode-${m}`}
                          className={"e-tab-pill" + (mode === m ? " active" : "")}>
                      {l}
                    </Link>
                  ))}
                </div>
                <span className="font-mono text-xs tracking-widest text-[#4F5C55]">
                  <span className="text-[#14261F]">{String(filtered.length).padStart(2,"0")}</span> ENTRIES · SORTED BY CLOSING
                </span>
              </div>

              {err && <div className="text-red-700 bg-red-50 border border-red-200 px-4 py-2 text-sm">{err}</div>}
              {loading ? (
                <div className="text-[#4F5C55] text-sm">Loading tenders…</div>
              ) : filtered.length === 0 ? (
                <div className="e-cream-card p-14 text-center text-[#4F5C55]">
                  No {mode === "completed" ? "completed" : mode === "all" ? "" : "live"} tenders match this filter.
                </div>
              ) : (
                <div className="e-register-wrap overflow-x-auto">
                  <div className="e-register-inner min-w-[720px] md:min-w-0">
                    <div className="e-register-head">
                      <span className="e-title">{title}</span>
                      <span className="e-meta"><span className="text-[#14261F]">{String(filtered.length).padStart(2,"0")}</span> ENTRIES</span>
                    </div>
                    <table className="e-register-table" data-testid="tenders-grid">
                      <thead>
                        <tr>
                          <th className="w-11">No.</th>
                          <th className="min-w-[240px]">Ref · Tender · Buyer</th>
                          <th className="w-36">Sector · Country</th>
                          <th className="w-28">Est. Value</th>
                          <th className="w-40">Time Left</th>
                          <th className="w-32 text-right">Status</th>
                        </tr>
                      </thead>
                      <tbody>
                        {filtered.slice(0, 20).map((n, idx) => {
                          const roman = ["i","ii","iii","iv","v","vi","vii","viii","ix","x","xi","xii","xiii","xiv","xv","xvi","xvii","xviii","xix","xx"][idx] || String(idx+1);
                          const past = (n.submission_deadline || "9999") <= now;
                          const isAwarded = n.award_status === "awarded";
                          const rem = n.submission_deadline ? new Date(n.submission_deadline) - new Date() : 0;
                          const days = Math.max(0, Math.floor(rem / (1000*60*60*24)));
                          const hours = Math.max(0, Math.floor((rem / (1000*60*60)) % 24));
                          const mins = Math.max(0, Math.floor((rem / (1000*60)) % 60));
                          const closingSoon = rem > 0 && rem < 1000*60*60*24*7;
                          return (
                            <tr key={n.id} data-testid={`tender-card-${n.notice_ref}`}>
                              <td className="e-roman">{roman}</td>
                              <td>
                                <Link to={`/notices/${n.notice_ref}`} className="e-title-cell">
                                  <span className="e-ref">{n.notice_ref}</span>
                                  <span>{n.title}</span>
                                </Link>
                              </td>
                              <td>
                                <span className="flex flex-col gap-1 text-sm text-[#3B4A43]">
                                  <span className="text-[#14261F]">{n.sector_name || n.category || "General"}</span>
                                  <span>{n.delivery_country || "—"}</span>
                                </span>
                              </td>
                              <td className="text-[15px] font-semibold text-[#14261F] pt-6">
                                {n.budget_amount ? `${n.budget_currency || ""} ${Number(n.budget_amount).toLocaleString()}` : "—"}
                                {Number(n.emd_amount) > 0 && (
                                  <div className="text-[11px] font-normal text-[#B8741A] mt-1"
                                       data-testid={`tender-emd-${n.notice_ref}`}>
                                    EMD {n.emd_currency || n.budget_currency || ""} {Number(n.emd_amount).toLocaleString()}
                                  </div>
                                )}
                              </td>
                              <td>
                                <span className="flex flex-col gap-1.5 items-start pt-4">
                                  {rem > 0 ? (
                                    <span className="e-countdown-chip">
                                      {String(days).padStart(2,"0")}d {String(hours).padStart(2,"0")}:{String(mins).padStart(2,"0")}
                                    </span>
                                  ) : (
                                    <span className="e-countdown-chip" style={{background:"#E7E1D0",color:"#4F5C55"}}>Closed</span>
                                  )}
                                  <span className="text-xs text-[#4F5C55]">
                                    {n.submission_deadline ? `Closes ${new Date(n.submission_deadline).toLocaleDateString("en-GB", { day:"2-digit", month:"short", year:"numeric" })}` : ""}
                                  </span>
                                </span>
                              </td>
                              <td className="text-right pt-6">
                                {isAwarded ? (
                                  <span className="e-status-chip awarded">★ Awarded</span>
                                ) : closingSoon ? (
                                  <span className="e-status-chip closing-soon">Closing soon</span>
                                ) : past ? (
                                  <span className="e-status-chip" style={{color:"#4F5C55",background:"#E7E1D0"}}>Closed</span>
                                ) : (
                                  <span className="e-status-chip open">Open for bids</span>
                                )}
                              </td>
                            </tr>
                          );
                        })}
                      </tbody>
                    </table>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          /* Legacy layout */
        <div className="legacy-layout">
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
        <div className="mt-3 grid gap-3 md:grid-cols-[1fr_1fr_1fr_auto] items-stretch">
          <select value={sector} onChange={(e) => setSector(e.target.value)}
                  data-testid="tenders-sector-filter"
                  className="px-4 py-3 border border-brand-navy/20 bg-white text-sm">
            <option value="">All sectors</option>
            {sectors.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
          </select>
          <select value={contractType} onChange={(e) => setContractType(e.target.value)}
                  data-testid="tenders-contract-filter"
                  className="px-4 py-3 border border-brand-navy/20 bg-white text-sm">
            <option value="">All contract types</option>
            {contractTypeOptions(contractTypes)}
          </select>
          <input value={category} onChange={(e) => setCategory(e.target.value)}
                 placeholder="Category (UNSPSC): solar, construction…"
                 data-testid="tenders-category-filter"
                 className="px-4 py-3 border border-brand-navy/20 bg-white text-sm" />
          <button type="button" onClick={clearFilters} data-testid="tenders-clear-filters"
                  className="px-4 py-3 border border-brand-navy text-brand-navy text-[11px] uppercase tracking-widest hover:bg-brand-navy hover:text-white">
            Clear
          </button>
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
                    {/* v52cp — public card now shows EMD too (users complained
                        it wasn't visible on the Live tenders list). */}
                    {Number(n.emd_amount) > 0 && (
                      <div data-testid={`tender-emd-${n.notice_ref}`}>
                        <span className="pmc-label">EMD</span>
                        <div className="text-brand-navy font-semibold mt-0.5">{n.emd_currency || n.budget_currency || ""} {Number(n.emd_amount).toLocaleString()}</div>
                      </div>)}
                    {n.submission_deadline && (
                      <div><span className="pmc-label">Deadline</span>
                        <div className="text-brand-navy font-mono mt-0.5">{n.submission_deadline.slice(0, 10)}</div>
                      </div>)}
                    {n.category && (
                      <div><span className="pmc-label">Category</span>
                        <div className="text-brand-navy mt-0.5">{n.category}</div>
                      </div>)}
                    {n.delivery_country && (
                      <div data-testid={`tender-country-${n.notice_ref}`}>
                        <span className="pmc-label">Country</span>
                        <div className="text-brand-navy mt-0.5 font-mono">{n.delivery_country}</div>
                      </div>)}
                  </div>
                </Link>
              );
            })}
          </div>
        )}
        </div>
        )}
      </main>
      <PmcFooter />
    </div>
  );
}
