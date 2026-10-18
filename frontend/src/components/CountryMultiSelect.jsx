import { useEffect, useMemo, useRef, useState } from "react";
import { mastersGeoApi } from "@/lib/api";

/**
 * v56 — reusable multi-country picker. Shows country NAMES (not ISO codes) as
 * removable chips; a searchable checkbox dropdown toggles selection. The value
 * is still an array of ISO-2 codes (so the backend contract is unchanged).
 * Empty selection means "all countries / global".
 */
let _countryCache = null;

export default function CountryMultiSelect({ value = [], onChange, testid = "country-multiselect" }) {
  const [countries, setCountries] = useState(_countryCache || []);
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const boxRef = useRef(null);

  useEffect(() => {
    if (_countryCache) { setCountries(_countryCache); return; }
    mastersGeoApi.countries()
      .then((r) => { _countryCache = Array.isArray(r) ? r : []; setCountries(_countryCache); })
      .catch(() => setCountries([]));
  }, []);

  useEffect(() => {
    const onDoc = (e) => { if (boxRef.current && !boxRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", onDoc);
    return () => document.removeEventListener("mousedown", onDoc);
  }, []);

  const byCode = useMemo(() => {
    const m = new Map();
    for (const c of countries) m.set(c.code, c);
    return m;
  }, [countries]);
  const selected = value || [];
  const toggle = (code) =>
    onChange(selected.includes(code) ? selected.filter((c) => c !== code) : [...selected, code]);

  const query = q.trim().toLowerCase();
  const filtered = useMemo(() => {
    if (!query) return countries;
    return countries.filter((c) =>
      (c.name || "").toLowerCase().includes(query) || (c.code || "").toLowerCase().includes(query));
  }, [countries, query]);

  return (
    <div className="relative" ref={boxRef} data-testid={testid}>
      <button type="button" onClick={() => setOpen((o) => !o)} data-testid={`${testid}-toggle`}
        className="mt-1 w-full min-h-[40px] px-3 py-2 border bg-white text-left flex flex-wrap gap-1 items-center">
        {selected.length === 0 ? (
          <span className="text-brand-navy/40 normal-case tracking-normal">All countries (global)</span>
        ) : selected.map((code) => (
          <span key={code}
            className="inline-flex items-center gap-1 bg-brand-navy/10 text-brand-navy px-2 py-0.5 text-xs rounded normal-case tracking-normal">
            {byCode.get(code)?.emoji ? byCode.get(code).emoji + " " : ""}{byCode.get(code)?.name || code}
            <span onClick={(e) => { e.stopPropagation(); toggle(code); }}
              data-testid={`${testid}-chip-remove-${code}`}
              className="cursor-pointer text-brand-navy/50 hover:text-red-600">✕</span>
          </span>
        ))}
      </button>
      {open && (
        <div className="absolute z-40 left-0 right-0 mt-1 bg-white border border-brand-navy/25 shadow-lg">
          <input autoFocus value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search country…"
            data-testid={`${testid}-search`}
            className="w-full px-3 py-2 border-b text-sm normal-case tracking-normal" />
          <div className="max-h-56 overflow-y-auto">
            {filtered.map((c) => (
              <label key={c.code} data-testid={`${testid}-option-${c.code}`}
                className="flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-brand-navy/5 cursor-pointer normal-case tracking-normal">
                <input type="checkbox" checked={selected.includes(c.code)} onChange={() => toggle(c.code)} />
                <span>{c.emoji ? c.emoji + " " : ""}{c.name} <span className="text-brand-navy/40">({c.code})</span></span>
              </label>
            ))}
            {filtered.length === 0 && <div className="px-3 py-2 text-xs text-brand-navy/50 italic">No match</div>}
          </div>
          <div className="flex justify-between items-center px-3 py-2 border-t text-xs">
            <button type="button" onClick={() => onChange([])} data-testid={`${testid}-clear`}
              className="text-brand-navy/60 hover:underline">Clear (all countries)</button>
            <button type="button" onClick={() => setOpen(false)}
              className="px-3 py-1 bg-brand-navy text-white uppercase tracking-widest text-[10px]">Done</button>
          </div>
        </div>
      )}
    </div>
  );
}
