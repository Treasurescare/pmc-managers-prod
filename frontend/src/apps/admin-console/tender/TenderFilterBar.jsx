/**
 * v45 · Phase A — Filter + sort bar for the Tender Builder drafts list.
 * Client-side filtering keeps things fast for < 500 drafts and needs no
 * backend change. All filter state lives in the parent so the sidebar
 * stays a pure render.
 */
export default function TenderFilterBar({
  filters, setFilters, industries = [], countries = [],
}) {
  const patch = (p) => setFilters({ ...filters, ...p });
  return (
    <div className="border border-brand-navy/10 bg-white p-3 space-y-2 text-xs"
         data-testid="tb-filter-bar">
      <div className="flex items-center gap-1">
        <span className="text-brand-navy/50 select-none" aria-hidden>🔍</span>
        <input value={filters.q || ""}
               onChange={(e) => patch({ q: e.target.value })}
               placeholder="Search drafts + in-progress + tender-ref…"
               data-testid="tb-filter-q"
               className="flex-1 px-2 py-1.5 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft" />
      </div>
      <div className="grid grid-cols-2 gap-2">
        <select value={filters.country || ""} onChange={(e) => patch({ country: e.target.value })}
                data-testid="tb-filter-country"
                className="px-2 py-1.5 border border-brand-navy/20 bg-white">
          <option value="">All countries</option>
          {countries.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
        <select value={filters.industry || ""} onChange={(e) => patch({ industry: e.target.value })}
                data-testid="tb-filter-industry"
                className="px-2 py-1.5 border border-brand-navy/20 bg-white">
          <option value="">All industries</option>
          {industries.map((i) => <option key={i} value={i}>{i}</option>)}
        </select>
      </div>
      {filters.country && (
        <div className="flex items-center gap-2 pt-1" data-testid="tb-filter-country-mode">
          <span className="text-brand-navy/60 text-[11px]">Show for {filters.country}:</span>
          <label className="flex items-center gap-1 text-[11px] cursor-pointer">
            <input type="radio" name="country-mode"
                   checked={(filters.country_mode || "only") === "only"}
                   onChange={() => patch({ country_mode: "only" })}
                   data-testid="tb-filter-country-mode-only" />
            This country only
          </label>
          <label className="flex items-center gap-1 text-[11px] cursor-pointer">
            <input type="radio" name="country-mode"
                   checked={filters.country_mode === "all"}
                   onChange={() => patch({ country_mode: "all" })}
                   data-testid="tb-filter-country-mode-all" />
            All templates
          </label>
        </div>
      )}
      <select value={filters.sort || "date-desc"} onChange={(e) => patch({ sort: e.target.value })}
              data-testid="tb-filter-sort"
              className="w-full px-2 py-1.5 border border-brand-navy/20 bg-white">
        <option value="date-desc">Newest first</option>
        <option value="date-asc">Oldest first</option>
        <option value="name-asc">Name A → Z</option>
        <option value="name-desc">Name Z → A</option>
        <option value="industry-asc">Industry A → Z</option>
      </select>
    </div>
  );
}

// Utility used by the sidebar to actually apply the filter state.
export function applyTenderFilters(drafts, filters) {
  let out = [...drafts];
  const q = (filters?.q || "").trim().toLowerCase();
  if (q) {
    out = out.filter((d) =>
      (d.name || "").toLowerCase().includes(q) ||
      (d.industry || "").toLowerCase().includes(q) ||
      (d.header?.tender_reference_number || "").toLowerCase().includes(q) ||
      (d.header?.tender_id || "").toLowerCase().includes(q));
  }
  if (filters?.country) {
    const cu = filters.country.toUpperCase();
    out = out.filter((d) => {
      const rowCountry = (d.country || d.header?.country || "").toUpperCase();
      if (filters?.country_mode === "all") return true;
      // "only" (default) — strict match on the selected country
      return rowCountry === cu;
    });
  }
  if (filters?.industry) out = out.filter((d) => (d.industry || "") === filters.industry);
  const sort = filters?.sort || "date-desc";
  out.sort((a, b) => {
    if (sort === "date-asc")     return (a.created_at || "").localeCompare(b.created_at || "");
    if (sort === "name-asc")     return (a.name || "").localeCompare(b.name || "");
    if (sort === "name-desc")    return (b.name || "").localeCompare(a.name || "");
    if (sort === "industry-asc") return (a.industry || "").localeCompare(b.industry || "");
    return (b.created_at || "").localeCompare(a.created_at || "");
  });
  return out;
}
