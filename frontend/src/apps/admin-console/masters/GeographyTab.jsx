import { useEffect, useMemo, useState } from "react";
import { mastersGeoApi, showApiError } from "@/lib/api";
import { useListPager } from "@/components/ListPager";

/**
 * v52cn — Read-only Geography master viewer.
 *
 * Lets admins browse the imported country / state / city dataset so they
 * can confirm coverage before rolling the vendor registration out to a
 * new jurisdiction. All lists are paginated and search-backed because
 * the full city set is ~152k rows.
 */
export default function GeographyTab() {
  const [countries, setCountries] = useState([]);
  const [cc, setCc] = useState("");
  const [states, setStates] = useState([]);
  const [stateCode, setStateCode] = useState("");
  const [cityQ, setCityQ] = useState("");
  const [cities, setCities] = useState([]);

  useEffect(() => {
    mastersGeoApi.countries()
      .then((r) => setCountries(Array.isArray(r) ? r : []))
      .catch(showApiError);
  }, []);

  useEffect(() => {
    if (!cc) { setStates([]); setStateCode(""); return; }
    mastersGeoApi.states(cc).then((r) => setStates(Array.isArray(r) ? r : []))
                             .catch(() => setStates([]));
  }, [cc]);

  useEffect(() => {
    if (!cc) { setCities([]); return; }
    mastersGeoApi.cities(cc, stateCode || undefined, cityQ || undefined, 200)
      .then((r) => setCities(Array.isArray(r) ? r : []))
      .catch(() => setCities([]));
  }, [cc, stateCode, cityQ]);

  const summary = useMemo(() => ({
    countries: countries.length,
    states: states.length,
    cities: cities.length,
  }), [countries, states, cities]);

  const countriesPager = useListPager(countries, { testid: "geo-countries-pager", pageSize: 50 });

  return (
    <div className="space-y-4" data-testid="geography-tab">
      <div className="bg-white border border-brand-navy/10 p-4 grid gap-3 md:grid-cols-3"
           data-testid="geo-stats">
        <Stat label="Countries" value={summary.countries} />
        <Stat label="States / provinces loaded" value={summary.states}
              hint={cc ? `for ${cc}` : "pick a country"} />
        <Stat label="Cities loaded" value={summary.cities}
              hint={cc ? `for ${cc}${stateCode ? ` · ${stateCode}` : ""}` : "pick a country"} />
      </div>

      <div className="bg-white border border-brand-navy/10 p-4">
        <div className="text-[10px] uppercase tracking-widest text-brand-navy/60 mb-2">
          Browse geography
        </div>
        <div className="grid gap-3 md:grid-cols-3">
          <select value={cc} onChange={(e) => { setCc(e.target.value); setStateCode(""); setCityQ(""); }}
                  data-testid="geo-country-select"
                  className="px-3 py-2 border border-brand-navy/20 bg-white text-sm">
            <option value="">Pick a country…</option>
            {countries.map((c) => (
              <option key={c.code} value={c.code}>
                {c.emoji ? `${c.emoji} ` : ""}{c.code} — {c.name}
              </option>
            ))}
          </select>
          <select value={stateCode} onChange={(e) => { setStateCode(e.target.value); setCityQ(""); }}
                  disabled={!cc || states.length === 0}
                  data-testid="geo-state-select"
                  className="px-3 py-2 border border-brand-navy/20 bg-white text-sm disabled:bg-brand-pale/40">
            <option value="">
              {!cc ? "Pick a country first" : states.length ? "All states" : "No states"}
            </option>
            {states.map((s) => (
              <option key={s.state_code} value={s.state_code}>{s.name}</option>
            ))}
          </select>
          <input value={cityQ} onChange={(e) => setCityQ(e.target.value)}
                 disabled={!cc}
                 placeholder={cc ? "Filter cities by name…" : "Pick a country first"}
                 data-testid="geo-city-search"
                 className="px-3 py-2 border border-brand-navy/20 bg-white text-sm disabled:bg-brand-pale/40" />
        </div>

        {cc && (
          <div className="mt-4 grid gap-3 md:grid-cols-2">
            <div className="border border-brand-navy/10 bg-brand-pale/20 p-3"
                 data-testid="geo-states-panel">
              <div className="text-[10px] uppercase tracking-widest text-brand-navy/60 mb-2">
                States / provinces ({states.length})
              </div>
              <div className="max-h-72 overflow-y-auto">
                {states.length === 0 ? (
                  <div className="text-xs text-brand-navy/50">No states for this country</div>
                ) : states.map((s) => (
                  <div key={s.state_code} className="text-sm py-1 border-b border-brand-navy/5 flex justify-between"
                       data-testid={`geo-state-row-${s.state_code}`}>
                    <span>{s.name}</span>
                    <span className="font-mono text-[10px] text-brand-navy/40">{s.state_code}</span>
                  </div>
                ))}
              </div>
            </div>
            <div className="border border-brand-navy/10 bg-brand-pale/20 p-3"
                 data-testid="geo-cities-panel">
              <div className="text-[10px] uppercase tracking-widest text-brand-navy/60 mb-2">
                Cities ({cities.length}{cities.length === 200 ? "+ — refine search" : ""})
              </div>
              <div className="max-h-72 overflow-y-auto">
                {cities.length === 0 ? (
                  <div className="text-xs text-brand-navy/50">
                    {cityQ ? `No cities match "${cityQ}"` : "No cities loaded"}
                  </div>
                ) : cities.map((c, i) => (
                  <div key={`${c.state_code}-${c.name}-${i}`} className="text-sm py-1 border-b border-brand-navy/5 flex justify-between"
                       data-testid={`geo-city-row-${i}`}>
                    <span>{c.name}</span>
                    <span className="font-mono text-[10px] text-brand-navy/40">{c.state_name || c.state_code}</span>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      <div className="bg-white border border-brand-navy/10">
        <div className="p-3 text-[10px] uppercase tracking-widest text-brand-navy/60 border-b border-brand-navy/10">
          All countries ({countries.length})
        </div>
        {countriesPager.paged.map((c) => (
          <div key={c.code} className="border-b border-brand-navy/5 p-2 text-sm flex justify-between items-center"
               data-testid={`geo-country-row-${c.code}`}>
            <span>{c.emoji ? `${c.emoji} ` : ""}{c.name}</span>
            <span className="font-mono text-[10px] text-brand-navy/50">
              {c.code} · {c.iso3 || "—"} · {c.currency || "—"}
              {c.postal_code_format ? ` · ZIP ${c.postal_code_format}` : ""}
            </span>
          </div>
        ))}
        {countriesPager.controls}
      </div>
    </div>
  );
}

function Stat({ label, value, hint }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">{label}</div>
      <div className="text-2xl font-display text-brand-navy mt-1" data-testid={`geo-stat-${label.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
        {value.toLocaleString()}
      </div>
      {hint && <div className="text-[10px] text-brand-navy/50 mt-0.5">{hint}</div>}
    </div>
  );
}
