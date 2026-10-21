import { useEffect, useState } from "react";
import { publicApi } from "@/lib/api";

let _cache = null;

// Shared country master (ISO-2 code + name), fetched once and cached.
export function useCountries() {
  const [countries, setCountries] = useState(_cache || []);
  useEffect(() => {
    if (_cache) return;
    publicApi.countries()
      .then((rows) => { _cache = rows || []; setCountries(_cache); })
      .catch(() => setCountries([]));
  }, []);
  return countries;
}

// Single optional country <select> sourced from the master.
export function CountrySelect({ value, onChange, testId, allLabel = "All countries", className = "" }) {
  const countries = useCountries();
  return (
    <select value={value || ""} onChange={(e) => onChange(e.target.value)}
            data-testid={testId}
            className={className || "mt-1 w-full px-3 py-2 border normal-case tracking-normal"}>
      <option value="">{allLabel}</option>
      {countries.map((c) => <option key={c.code} value={c.code}>{c.code} — {c.name}</option>)}
    </select>
  );
}

// Multi-select country scope — scrollable checkbox list. value is string[] of codes.
export function CountryMultiSelect({ value = [], onChange, testId }) {
  const countries = useCountries();
  const [q, setQ] = useState("");
  const set = new Set(value || []);
  const toggle = (code) => {
    const next = new Set(set);
    if (next.has(code)) next.delete(code); else next.add(code);
    onChange(Array.from(next));
  };
  const query = q.trim().toLowerCase();
  const shown = query
    ? countries.filter((c) => c.name.toLowerCase().includes(query) || c.code.toLowerCase().includes(query))
    : countries;
  return (
    <div data-testid={testId} className="mt-1">
      <input value={q} onChange={(e) => setQ(e.target.value)}
             placeholder="Search countries… (blank list = all)"
             data-testid={testId ? `${testId}-search` : undefined}
             className="w-full px-3 py-2 border normal-case tracking-normal text-sm" />
      {(value || []).length > 0 && (
        <div className="flex flex-wrap gap-1 mt-2">
          {value.map((code) => (
            <span key={code} className="inline-flex items-center gap-1 text-[11px] bg-brand-navy text-white px-2 py-0.5">
              {code}
              <button type="button" onClick={() => toggle(code)} className="font-bold" aria-label={`remove ${code}`}>×</button>
            </span>
          ))}
        </div>
      )}
      <div className="mt-2 max-h-40 overflow-y-auto border border-brand-navy/15 bg-white">
        {shown.map((c) => (
          <label key={c.code} className="flex items-center gap-2 px-3 py-1.5 text-sm hover:bg-brand-pale/40 cursor-pointer">
            <input type="checkbox" checked={set.has(c.code)} onChange={() => toggle(c.code)} />
            <span>{c.code} — {c.name}</span>
          </label>
        ))}
        {shown.length === 0 && <div className="px-3 py-2 text-xs text-brand-navy/50">No match.</div>}
      </div>
    </div>
  );
}
