import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { mastersApi, showApiError } from "@/lib/api";
import { useCountries } from "@/components/CountryPicker";
import { useCurrencies } from "@/components/CurrencySelect";
import { InfoDot } from "@/components/InfoDot";
import { useListPager } from "@/components/ListPager";

const up = (v) => String(v || "").toUpperCase();

/**
 * v56t — Country currencies master. Each country has a set of accepted
 * currencies with one marked primary (the default pre-loaded on notice/bid/
 * EMD currency pickers). Any active currency remains selectable on those
 * forms; this only controls the per-country default set.
 */
export default function CountryCurrenciesTab() {
  const countries = useCountries();
  const currencies = useCurrencies();
  const [query, setQuery] = useState("");
  const [work, setWork] = useState({});

  useEffect(() => {
    if (!countries.length) return;
    setWork((prev) => {
      const next = { ...prev };
      countries.forEach((c) => {
        if (!next[c.code]) {
          const acc = (c.accepted_currencies && c.accepted_currencies.length)
            ? c.accepted_currencies.map(up)
            : (c.currency ? [up(c.currency)] : []);
          next[c.code] = { accepted: acc, primary: up(c.currency || acc[0] || "") };
        }
      });
      return next;
    });
  }, [countries]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return countries;
    return countries.filter((c) =>
      c.name.toLowerCase().includes(q) || c.code.toLowerCase().includes(q));
  }, [countries, query]);
  const pager = useListPager(filtered, { testid: "country-currencies-pager", pageSize: 20 });

  const setRow = (code, patch) =>
    setWork((w) => ({ ...w, [code]: { ...w[code], ...patch } }));

  const addCurrency = (code, cur) => {
    if (!cur) return;
    const w = work[code] || { accepted: [], primary: "" };
    if (w.accepted.includes(up(cur))) return;
    const accepted = [...w.accepted, up(cur)];
    setRow(code, { accepted, primary: w.primary || up(cur) });
  };
  const removeCurrency = (code, cur) => {
    const w = work[code];
    const accepted = w.accepted.filter((x) => x !== up(cur));
    const primary = w.primary === up(cur) ? (accepted[0] || "") : w.primary;
    setRow(code, { accepted, primary });
  };
  const save = async (code) => {
    const w = work[code];
    if (!w || !w.accepted.length) { toast.error("Add at least one currency"); return; }
    try {
      await mastersApi.setCountryCurrencies(code, {
        accepted_currencies: w.accepted, primary: w.primary || w.accepted[0],
      });
      toast.success(`${code} currencies saved`);
    } catch (e) { showApiError(e); }
  };

  return (
    <div data-testid="masters-country-currencies-tab" className="space-y-4">
      <p className="text-xs text-brand-navy/70 max-w-3xl">
        Set the currencies each country accepts and mark one as primary. The primary is
        pre-loaded by default on Notice / Bid / EMD currency pickers for that country —
        users can still pick any active currency.
        <InfoDot tip="This does not restrict currency choice; it only changes which currency loads by default when a country is selected." />
      </p>
      <input value={query} onChange={(e) => setQuery(e.target.value)}
             placeholder="Search by country name or code…"
             data-testid="country-currencies-search"
             className="w-full max-w-md px-3 py-2 border border-brand-navy/20 text-sm bg-white" />

      <div className="bg-white border border-brand-navy/10 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-brand-navy text-white uppercase text-xs tracking-widest">
            <tr>
              <th className="px-3 py-2 text-left">Country</th>
              <th className="px-3 py-2 text-left">Accepted currencies</th>
              <th className="px-3 py-2 text-left">Primary (default)</th>
              <th className="px-3 py-2 text-left">Add</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {pager.paged.map((c) => {
              const w = work[c.code] || { accepted: [], primary: "" };
              const avail = currencies.filter((x) => !w.accepted.includes(up(x.code)));
              return (
                <tr key={c.code} className="border-b border-brand-navy/10"
                    data-testid={`country-currencies-row-${c.code}`}>
                  <td className="px-3 py-2 whitespace-nowrap">
                    <span className="font-mono">{c.code}</span> · {c.name}
                  </td>
                  <td className="px-3 py-2">
                    <div className="flex flex-wrap gap-1">
                      {w.accepted.length === 0 && <span className="text-brand-navy/40 text-xs">None</span>}
                      {w.accepted.map((cur) => (
                        <span key={cur} className="inline-flex items-center gap-1 text-[11px] bg-brand-navy text-white px-2 py-0.5 font-mono">
                          {cur}
                          <button type="button" onClick={() => removeCurrency(c.code, cur)}
                                  className="font-bold" aria-label={`remove ${cur}`}
                                  data-testid={`country-currencies-remove-${c.code}-${cur}`}>×</button>
                        </span>
                      ))}
                    </div>
                  </td>
                  <td className="px-3 py-2">
                    <select value={w.primary} onChange={(e) => setRow(c.code, { primary: e.target.value })}
                            data-testid={`country-currencies-primary-${c.code}`}
                            className="px-2 py-1 border bg-white font-mono text-xs">
                      {w.accepted.length === 0 && <option value="">—</option>}
                      {w.accepted.map((cur) => <option key={cur} value={cur}>{cur}</option>)}
                    </select>
                  </td>
                  <td className="px-3 py-2">
                    <select value="" onChange={(e) => { addCurrency(c.code, e.target.value); e.target.value = ""; }}
                            data-testid={`country-currencies-add-${c.code}`}
                            className="px-2 py-1 border bg-white text-xs max-w-[180px]">
                      <option value="">+ add currency…</option>
                      {avail.map((x) => <option key={x.code} value={x.code}>{x.code} · {x.name}</option>)}
                    </select>
                  </td>
                  <td className="px-3 py-2 text-right">
                    <button type="button" onClick={() => save(c.code)}
                            data-testid={`country-currencies-save-${c.code}`}
                            className="text-xs uppercase tracking-widest text-brand-navy font-semibold hover:underline">
                      Save
                    </button>
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr><td colSpan={5} className="text-center py-10 text-brand-navy/60">
                No countries match. Try clearing the search.
              </td></tr>
            )}
          </tbody>
        </table>
        {pager.controls}
      </div>
    </div>
  );
}
