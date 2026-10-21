import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { mastersApi, showApiError } from "@/lib/api";
import { InfoDot } from "@/components/InfoDot";
import { useListPager } from "@/components/ListPager";
import { useCountries } from "@/components/CountryPicker";

/**
 * v52bl — Currencies master (Masters → Currencies).
 * Backed by /api/v1/masters/currencies. Admins can add, edit (name/symbol/
 * decimals), activate/deactivate ISO-4217 currencies without a redeploy.
 */
export default function CurrenciesTab() {
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [draft, setDraft] = useState({
    code: "", name: "", symbol: "", decimals: 2, is_active: true,
  });
  const [editing, setEditing] = useState(null);
  // #d — currency↔country: a currency is a shared catalogue; the link lives on
  // the country master (each country has a default currency). "Used by" is
  // derived read-only so shared currencies (EUR/USD) list every country.
  const allCountries = useCountries();
  const usedBy = (code) => allCountries.filter((c) => (c.currency || "").toUpperCase() === code).map((c) => c.code);

  const load = useCallback(() => {
    mastersApi
      .listCurrencies({ includeInactive: true })
      .then((r) => setRows(Array.isArray(r) ? r : []))
      .catch(showApiError);
  }, []);
  useEffect(() => { load(); }, [load]);

  const filtered = rows.filter((r) => {
    if (!showInactive && r.is_active === false) return false;
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return [r.code, r.name, r.symbol].filter(Boolean).some((s) =>
      String(s).toLowerCase().includes(q));
  });
  const pager = useListPager(filtered, { testid: "currencies-pager", pageSize: 25 });

  const create = async () => {
    if (!draft.code || draft.code.length !== 3) {
      toast.error("ISO-4217 code is required (3 letters, e.g. USD)");
      return;
    }
    if (!draft.name) {
      toast.error("Currency name is required");
      return;
    }
    try {
      await mastersApi.createCurrency({ ...draft, code: draft.code.toUpperCase() });
      toast.success(`Currency ${draft.code.toUpperCase()} added`);
      setDraft({ code: "", name: "", symbol: "", decimals: 2, is_active: true });
      setShowNew(false);
      load();
    } catch (e) { showApiError(e); }
  };

  const save = async (row) => {
    try {
      await mastersApi.updateCurrency(row.id, {
        code: row.code.toUpperCase(),
        name: row.name,
        symbol: row.symbol || null,
        decimals: Number(row.decimals) || 2,
        is_active: !!row.is_active,
      });
      toast.success(`Currency ${row.code} updated`);
      setEditing(null);
      load();
    } catch (e) { showApiError(e); }
  };

  const deactivate = async (row) => {
    if (!window.confirm(`Deactivate ${row.code}? It will no longer appear in notice/bid dropdowns, but historical records keep the code.`)) return;
    try {
      await mastersApi.deactivateCurrency(row.id);
      toast.success(`Currency ${row.code} deactivated`);
      load();
    } catch (e) { showApiError(e); }
  };

  return (
    <div data-testid="masters-currencies-tab" className="space-y-4">
      <div className="flex flex-wrap gap-3 items-center">
        <input value={query} onChange={(e) => setQuery(e.target.value)}
               placeholder="Search by ISO code, name or symbol…"
               data-testid="currencies-search"
               className="flex-1 min-w-[220px] px-3 py-2 border border-brand-navy/20 text-sm bg-white" />
        <label className="text-xs text-brand-navy/70 flex items-center gap-1">
          <input type="checkbox" checked={showInactive}
                 onChange={(e) => setShowInactive(e.target.checked)}
                 data-testid="currencies-show-inactive" />
          Show inactive
        </label>
        <button type="button" onClick={() => setShowNew(!showNew)}
                data-testid="currencies-new-toggle"
                className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          {showNew ? "Cancel" : "Add currency"}
        </button>
      </div>

      {showNew && (
        <div className="bg-white border border-brand-navy-soft/40 p-4 grid gap-3 md:grid-cols-5" data-testid="currencies-new-form">
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            ISO-4217 <span className="text-red-600">*</span><InfoDot tip="Three-letter ISO code, e.g. USD, EUR, KZT." />
            <input value={draft.code} maxLength={3}
                   onChange={(e) => setDraft({ ...draft, code: e.target.value.toUpperCase() })}
                   data-testid="currencies-new-code"
                   className="mt-1 w-full px-3 py-2 border font-mono tracking-widest normal-case" />
          </label>
          <label className="md:col-span-2 text-xs uppercase tracking-widest text-brand-navy/60">
            Name <span className="text-red-600">*</span>
            <input value={draft.name}
                   onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                   data-testid="currencies-new-name"
                   placeholder="e.g. US Dollar"
                   className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Symbol<InfoDot tip="Display symbol (e.g. $, €, ₸). Optional." />
            <input value={draft.symbol} maxLength={8}
                   onChange={(e) => setDraft({ ...draft, symbol: e.target.value })}
                   data-testid="currencies-new-symbol"
                   className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Decimals
            <input type="number" min="0" max="4" value={draft.decimals}
                   onChange={(e) => setDraft({ ...draft, decimals: e.target.value })}
                   data-testid="currencies-new-decimals"
                   className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
          </label>
          <div className="md:col-span-5 flex justify-end">
            <button type="button" onClick={create} data-testid="currencies-new-save"
                    className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white">
              Add currency
            </button>
          </div>
        </div>
      )}

      <div className="bg-white border border-brand-navy/10 overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="bg-brand-navy text-white uppercase text-xs tracking-widest">
            <tr>
              <th className="px-3 py-2 text-left">Code</th>
              <th className="px-3 py-2 text-left">Name</th>
              <th className="px-3 py-2 text-left">Symbol</th>
              <th className="px-3 py-2 text-center">Decimals</th>
              <th className="px-3 py-2 text-left">Used by (default)</th>
              <th className="px-3 py-2 text-center">Active</th>
              <th className="px-3 py-2 text-right">Actions</th>
            </tr>
          </thead>
          <tbody>
            {pager.paged.map((row) => {
              const isEdit = editing?.id === row.id;
              const r = isEdit ? editing : row;
              return (
                <tr key={row.id} className="border-b border-brand-navy/10"
                    data-testid={`currencies-row-${row.code}`}>
                  <td className="px-3 py-2 font-mono tracking-widest">{row.code}</td>
                  <td className="px-3 py-2">
                    {isEdit ? (
                      <input value={r.name}
                             onChange={(e) => setEditing({ ...r, name: e.target.value })}
                             className="w-full px-2 py-1 border" />
                    ) : row.name}
                  </td>
                  <td className="px-3 py-2 font-mono">
                    {isEdit ? (
                      <input value={r.symbol || ""} maxLength={8}
                             onChange={(e) => setEditing({ ...r, symbol: e.target.value })}
                             className="w-20 px-2 py-1 border" />
                    ) : (row.symbol || "—")}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {isEdit ? (
                      <input type="number" min="0" max="4" value={r.decimals}
                             onChange={(e) => setEditing({ ...r, decimals: e.target.value })}
                             className="w-14 px-2 py-1 border text-center" />
                    ) : (row.decimals ?? 2)}
                  </td>
                  <td className="px-3 py-2 text-xs text-brand-navy/70" data-testid={`currencies-usedby-${row.code}`}>
                    {(() => { const u = usedBy(row.code); return u.length ? (u.length > 6 ? `${u.slice(0, 6).join(", ")} +${u.length - 6}` : u.join(", ")) : "—"; })()}
                  </td>
                  <td className="px-3 py-2 text-center">
                    {row.is_active
                      ? <span className="text-emerald-700 text-xs uppercase tracking-widest">● Active</span>
                      : <span className="text-brand-navy/40 text-xs uppercase tracking-widest">○ Inactive</span>}
                  </td>
                  <td className="px-3 py-2 text-right space-x-2">
                    {isEdit ? (
                      <>
                        <button onClick={() => setEditing(null)}
                                className="text-xs uppercase tracking-widest text-brand-navy/60">Cancel</button>
                        <button onClick={() => save(r)}
                                data-testid={`currencies-save-${row.code}`}
                                className="text-xs uppercase tracking-widest text-brand-navy font-semibold hover:underline">Save</button>
                      </>
                    ) : (
                      <>
                        <button onClick={() => setEditing(row)}
                                data-testid={`currencies-edit-${row.code}`}
                                className="text-xs uppercase tracking-widest text-brand-navy hover:underline">Edit</button>
                        {row.is_active && (
                          <button onClick={() => deactivate(row)}
                                  data-testid={`currencies-deactivate-${row.code}`}
                                  className="text-xs uppercase tracking-widest text-red-700 hover:underline">Deactivate</button>
                        )}
                      </>
                    )}
                  </td>
                </tr>
              );
            })}
            {filtered.length === 0 && (
              <tr><td colSpan={7} className="text-center py-10 text-brand-navy/60">
                No currencies match. Try clearing the filter.
              </td></tr>
            )}
          </tbody>
        </table>
        {pager.controls}
      </div>
    </div>
  );
}
