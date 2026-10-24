import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useUiTheme } from "@/context/UiThemeContext";
import { publicApi, showApiError } from "@/lib/api";
import { useListPager } from "@/components/ListPager";
import VendorPortalChrome from "./VendorPortalChrome";

function fmtMoney(amount, currency) {
  if (amount == null) return "—";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency", currency: currency || "USD", maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${currency || ""} ${Number(amount).toLocaleString()}`;
  }
}

function fmtEmd(n) {
  if (n.emd_amount != null) return fmtMoney(n.emd_amount, n.emd_currency);
  if (n.emd_percentage) return `${n.emd_percentage}% of bid`;
  return "See notice";
}

function fmtCountdown(iso) {
  if (!iso) return "—";
  const secs = Math.max(0, Math.floor((new Date(iso) - new Date()) / 1000));
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (secs === 0) return "Closed";
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

const SORTS = [
  { value: "deadline_asc", label: "Closing soonest" },
  { value: "deadline_desc", label: "Closing latest" },
  { value: "budget_desc", label: "Budget: high to low" },
  { value: "budget_asc", label: "Budget: low to high" },
];

export default function VendorFindTendersE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState("");
  const [sortBy, setSortBy] = useState("deadline_asc");
  const [fCountry, setFCountry] = useState("");
  const [fSector, setFSector] = useState("");
  const [fContract, setFContract] = useState("");
  const [fCategory, setFCategory] = useState("");
  const [maps, setMaps] = useState({ country: {}, sector: {}, contract: {} });

  useEffect(() => {
    if (!isE) return;
    setLoading(true);
    publicApi.listNotices({ limit: 100, offset: 0 })
      .then((res) => setItems(res.items || []))
      .catch(showApiError)
      .finally(() => setLoading(false));
  }, [isE]);

  // Labels for the filter dropdowns (code -> friendly name). Best-effort.
  useEffect(() => {
    if (!isE) return;
    Promise.all([
      publicApi.countries().catch(() => []),
      publicApi.listSectorsPublic().catch(() => []),
      publicApi.listContractTypesPublic().catch(() => []),
    ]).then(([countries, sectors, contracts]) => {
      const country = {}, sector = {}, contract = {};
      (countries || []).forEach((c) => { if (c.code) country[String(c.code).toUpperCase()] = c.name || c.code; });
      (sectors || []).forEach((s) => { if (s.code) sector[s.code] = s.name || s.code; });
      (contracts || []).forEach((c) => { if (c.code) contract[c.code] = c.name || c.code; });
      setMaps({ country, sector, contract });
    });
  }, [isE]);

  const countryLabel = (code) => (code ? (maps.country[String(code).toUpperCase()] || code) : "—");

  // Distinct filter options derived from the loaded notices (so every option
  // actually has results). Labelled via the master maps where available.
  const opts = useMemo(() => {
    const uniq = (arr) => Array.from(new Set(arr.filter(Boolean)));
    return {
      countries: uniq(items.map((n) => (n.delivery_country || n.country || "").toUpperCase()))
        .map((code) => ({ code, label: maps.country[code] || code }))
        .sort((a, b) => a.label.localeCompare(b.label)),
      sectors: uniq(items.map((n) => n.sector_code))
        .map((code) => ({ code, label: maps.sector[code] || code }))
        .sort((a, b) => a.label.localeCompare(b.label)),
      contracts: uniq(items.map((n) => n.contract_type_code))
        .map((code) => ({ code, label: maps.contract[code] || code }))
        .sort((a, b) => a.label.localeCompare(b.label)),
      categories: uniq(items.map((n) => n.category)).sort((a, b) => a.localeCompare(b)),
    };
  }, [items, maps]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    let out = items.filter((n) => {
      if (q && !(
        (n.title || "").toLowerCase().includes(q) ||
        (n.notice_ref || "").toLowerCase().includes(q) ||
        (n.category || "").toLowerCase().includes(q)
      )) return false;
      if (fCountry && (n.delivery_country || n.country || "").toUpperCase() !== fCountry) return false;
      if (fSector && n.sector_code !== fSector) return false;
      if (fContract && n.contract_type_code !== fContract) return false;
      if (fCategory && n.category !== fCategory) return false;
      return true;
    });
    const now = Date.now();
    const dl = (n) => (n.submission_deadline ? new Date(n.submission_deadline).getTime() : null);
    const bud = (n) => (n.budget_amount != null ? Number(n.budget_amount) : null);
    out = [...out].sort((a, b) => {
      if (sortBy === "budget_desc" || sortBy === "budget_asc") {
        const av = bud(a), bv = bud(b);
        if (av == null && bv == null) return 0;
        if (av == null) return 1;
        if (bv == null) return -1;
        return sortBy === "budget_desc" ? bv - av : av - bv;
      }
      // deadline sorts — open tenders always rank above closed ones
      const ad = dl(a), bd = dl(b);
      const aClosed = ad != null && ad < now;
      const bClosed = bd != null && bd < now;
      if (aClosed !== bClosed) return aClosed ? 1 : -1;
      if (ad == null && bd == null) return 0;
      if (ad == null) return 1;
      if (bd == null) return -1;
      return sortBy === "deadline_desc" ? bd - ad : ad - bd;
    });
    return out;
  }, [items, search, sortBy, fCountry, fSector, fContract, fCategory]);

  const { paged, controls } = useListPager(filtered, { defaultSize: 10, testid: "vft-pager" });

  const clearAll = () => {
    setSearch(""); setSortBy("deadline_asc");
    setFCountry(""); setFSector(""); setFContract(""); setFCategory("");
  };
  const hasFilters = search || fCountry || fSector || fContract || fCategory || sortBy !== "deadline_asc";

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="vendor-find-tenders-e" data-pmc-e-page="vendor-find-tenders-e">
      <VendorPortalChrome active="/vendor/tenders">
        <div className="sp-head">
          <div>
            <div className="pmc-eyebrow">Find tenders</div>
            <h1 data-testid="vft-count-heading">
              {loading ? "Loading tenders…" : `${filtered.length} tender${filtered.length === 1 ? "" : "s"} available`}
            </h1>
          </div>
        </div>

        <div className="pmc-filter" style={{ margin: "0 0 8px", flexWrap: "wrap" }}>
          <label className="pmc-search" style={{ flex: "1 1 240px" }}>
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>
            <input placeholder="Keyword, reference or category"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              data-testid="vft-search" />
          </label>

          <select value={sortBy} onChange={(e) => setSortBy(e.target.value)}
                  aria-label="Sort tenders" data-testid="vft-sort">
            {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
          </select>

          <select value={fCountry} onChange={(e) => setFCountry(e.target.value)}
                  aria-label="Filter by country" data-testid="vft-filter-country">
            <option value="">All countries</option>
            {opts.countries.map((o) => <option key={o.code} value={o.code}>{o.label}</option>)}
          </select>

          <select value={fSector} onChange={(e) => setFSector(e.target.value)}
                  aria-label="Filter by sector" data-testid="vft-filter-sector">
            <option value="">All sectors</option>
            {opts.sectors.map((o) => <option key={o.code} value={o.code}>{o.label}</option>)}
          </select>

          <select value={fContract} onChange={(e) => setFContract(e.target.value)}
                  aria-label="Filter by contract type" data-testid="vft-filter-contract">
            <option value="">All contract types</option>
            {opts.contracts.map((o) => <option key={o.code} value={o.code}>{o.label}</option>)}
          </select>

          <select value={fCategory} onChange={(e) => setFCategory(e.target.value)}
                  aria-label="Filter by category" data-testid="vft-filter-category">
            <option value="">All categories</option>
            {opts.categories.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>

          {hasFilters && (
            <button className="pmc-btn pmc-btn--ghost pmc-btn--sm" onClick={clearAll}
                    data-testid="vft-clear-filters">Clear</button>
          )}
        </div>

        {loading && (
          <div className="pmc-callout" style={{ marginBottom: "16px" }}
               data-testid="vft-loading">
            Loading live tenders from the public board…
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="pmc-callout" style={{ marginBottom: "16px" }}
               data-testid="vft-empty">
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>
            <div>
              <b>No tenders match your filters.</b>{" "}
              Try <button className="pmc-linkbtn" onClick={clearAll} data-testid="vft-empty-clear"
                          style={{ background: "none", border: 0, padding: 0, color: "var(--brass-on-chrome, #B08E4A)", cursor: "pointer", textDecoration: "underline" }}>clearing filters</button>{" "}
              or <Link to="/vendor/categories">add more categories</Link> to broaden your match.
            </div>
          </div>
        )}

        <div className="pmc-grid3" data-testid="vft-grid">
          {paged.map((n) => (
            <article className="pmc-tender" key={n.notice_ref || n.id}
                     data-testid={`vft-card-${n.notice_ref || n.id}`}>
              <div className="pmc-tender__top">
                <span className="pmc-tag">{(n.document_type || n.notice_type || "TENDER").toUpperCase()}</span>
                <span className="pmc-ref">{n.notice_ref}</span>
                <span style={{ marginLeft: "auto" }} className="pmc-countdown">
                  {fmtCountdown(n.submission_deadline)}
                </span>
              </div>
              <h3 className="pmc-tender__title">{n.title}</h3>
              <dl className="pmc-tender__meta" style={{ margin: 0 }}>
                <div className="is-budget">
                  <dt>Indicative budget</dt>
                  <dd>{fmtMoney(n.budget_amount, n.budget_currency)}</dd>
                </div>
                <div>
                  <dt>EMD</dt>
                  <dd style={{ fontWeight: 500 }} data-testid={`vft-emd-${n.notice_ref}`}>{fmtEmd(n)}</dd>
                </div>
                <div>
                  <dt>Delivery</dt>
                  <dd style={{ fontWeight: 500 }} data-testid={`vft-country-${n.notice_ref}`}>
                    {countryLabel(n.delivery_country || n.country)}
                    {n.category ? ` · ${n.category}` : ""}
                  </dd>
                </div>
              </dl>
              <div className="pmc-tender__foot">
                <Link to={`/notices/${n.notice_ref}`}
                      className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                      data-testid={`vft-view-${n.notice_ref}`}>View</Link>
                {(() => {
                  const closed = n.submission_deadline && new Date(n.submission_deadline) < new Date();
                  return closed ? (
                    <span className="pmc-pill pmc-pill--warning"
                          data-testid={`vft-closed-${n.notice_ref}`}>Closed</span>
                  ) : (
                    <Link to={`/vendor/bid/new/${n.notice_ref}`}
                          className="pmc-btn pmc-btn--primary pmc-btn--sm"
                          data-testid={`vft-bid-${n.notice_ref}`}>Start bid</Link>
                  );
                })()}
              </div>
            </article>
          ))}
        </div>

        {filtered.length > 0 && (
          <div style={{ marginTop: 20, border: "1px solid var(--line, #0001)",
                        borderRadius: "var(--radius-sm, 4px)", overflow: "hidden" }}
               data-testid="vft-pager-wrap">
            {controls}
          </div>
        )}
      </VendorPortalChrome>
    </div>
  );
}
