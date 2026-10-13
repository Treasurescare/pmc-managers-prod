import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { mastersGeoApi, showApiError } from "@/lib/api";
import { useListPager } from "@/components/ListPager";

/**
 * v52cn — Country Licenses CRUD for admins.
 *
 * Lists every country that has a license-requirements entry in the
 * masters_country_licenses collection. Admins can:
 *  - Add a brand-new country entry (pick any ISO-2 code from the master)
 *  - Edit the license list inline (code, display name, mandatory flag)
 *  - Delete a row (clears the entry's licenses so vendors from that
 *    country are not prompted for anything).
 *
 * Backed by:
 *   GET  /api/v1/masters/country-licenses
 *   PUT  /api/v1/masters/country-licenses/{cc}
 */
export default function CountryLicensesTab() {
  const [rows, setRows] = useState([]);
  const [countries, setCountries] = useState([]);
  const [query, setQuery] = useState("");
  const [editCc, setEditCc] = useState(null);
  const [draftLicenses, setDraftLicenses] = useState([]);
  const [newCc, setNewCc] = useState("");

  const load = useCallback(() => {
    mastersGeoApi.listCountryLicenses()
      .then((r) => setRows(Array.isArray(r) ? r : []))
      .catch(showApiError);
    mastersGeoApi.countries()
      .then((r) => setCountries(Array.isArray(r) ? r : []))
      .catch(() => {});
  }, []);

  useEffect(() => { load(); }, [load]);

  const nameByCc = useMemo(() => {
    const m = new Map();
    for (const c of countries) m.set(c.code, c.name);
    return m;
  }, [countries]);

  const filtered = rows.filter((r) => {
    if (!query.trim()) return true;
    const q = query.trim().toLowerCase();
    return (r.country_code || "").toLowerCase().includes(q)
        || (nameByCc.get(r.country_code) || "").toLowerCase().includes(q);
  });
  const pager = useListPager(filtered, { testid: "country-lic-pager", pageSize: 25 });

  const beginEdit = (row) => {
    setEditCc(row.country_code);
    setDraftLicenses([...(row.licenses || [])]);
  };
  const cancelEdit = () => { setEditCc(null); setDraftLicenses([]); };

  const save = async () => {
    try {
      const clean = draftLicenses
        .filter((l) => l.code && l.name)
        .map((l) => ({ code: l.code.trim(), name: l.name.trim(), mandatory: !!l.mandatory }));
      await mastersGeoApi.putCountryLicenses(editCc, clean);
      toast.success(`${editCc} licenses saved (${clean.length} entries)`);
      cancelEdit();
      load();
    } catch (e) { showApiError(e); }
  };

  const addRow = () => setDraftLicenses([...draftLicenses, { code: "", name: "", mandatory: false }]);
  const removeRow = (i) => setDraftLicenses(draftLicenses.filter((_, idx) => idx !== i));
  const patchRow = (i, patch) => {
    const next = [...draftLicenses];
    next[i] = { ...next[i], ...patch };
    setDraftLicenses(next);
  };

  const addNew = async () => {
    const cc = newCc.trim().toUpperCase();
    if (!cc || cc.length < 2) { toast.error("Pick a country first"); return; }
    try {
      await mastersGeoApi.putCountryLicenses(cc, []);
      toast.success(`${cc} added`);
      setNewCc("");
      load();
      beginEdit({ country_code: cc, licenses: [] });
    } catch (e) { showApiError(e); }
  };

  return (
    <div data-testid="country-licenses-tab" className="space-y-4">
      <div className="bg-white border border-brand-navy/10 p-4 flex flex-wrap gap-3 items-end">
        <div>
          <div className="text-[10px] uppercase tracking-widest text-brand-navy/60 mb-1">
            Add a country
          </div>
          <select value={newCc} onChange={(e) => setNewCc(e.target.value)}
                  data-testid="country-lic-new-cc"
                  className="px-3 py-2 border border-brand-navy/20 bg-white text-sm min-w-[16rem]">
            <option value="">Pick a country…</option>
            {countries.map((c) => (
              <option key={c.code} value={c.code}>
                {c.emoji ? `${c.emoji} ` : ""}{c.code} — {c.name}
              </option>
            ))}
          </select>
        </div>
        <button onClick={addNew} data-testid="country-lic-new-add"
                className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          + Add country
        </button>
        <input value={query} onChange={(e) => setQuery(e.target.value)}
               placeholder="Search by country code or name…"
               data-testid="country-lic-search"
               className="flex-1 min-w-[12rem] px-3 py-2 border border-brand-navy/20 bg-white text-sm" />
      </div>

      <div className="bg-white border border-brand-navy/10">
        {filtered.length === 0 ? (
          <div className="p-6 text-sm text-brand-navy/50" data-testid="country-lic-empty">
            No country license requirements configured yet.
          </div>
        ) : pager.paged.map((row) => (
          <div key={row.country_code} className="border-b border-brand-navy/10 p-4"
               data-testid={`country-lic-row-${row.country_code}`}>
            <div className="flex items-center justify-between gap-3 flex-wrap">
              <div>
                <span className="font-mono text-xs text-brand-navy/60 mr-2">{row.country_code}</span>
                <strong className="text-brand-navy">{nameByCc.get(row.country_code) || "—"}</strong>
                <span className="ml-3 text-xs text-brand-navy/50">
                  {(row.licenses || []).length} license(s)
                </span>
                {row.seeded && (
                  <span className="ml-2 text-[10px] uppercase tracking-widest bg-emerald-50 text-emerald-800 border border-emerald-200 px-2 py-0.5">
                    seeded
                  </span>
                )}
              </div>
              {editCc !== row.country_code && (
                <button onClick={() => beginEdit(row)}
                        data-testid={`country-lic-edit-${row.country_code}`}
                        className="px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white">
                  Edit
                </button>
              )}
            </div>

            {editCc === row.country_code ? (
              <div className="mt-3 space-y-2" data-testid={`country-lic-editor-${row.country_code}`}>
                {draftLicenses.map((l, i) => (
                  <div key={i} className="grid gap-2 md:grid-cols-[8rem_1fr_6rem_auto] items-center"
                       data-testid={`country-lic-draft-row-${i}`}>
                    <input value={l.code}
                           onChange={(e) => patchRow(i, { code: e.target.value })}
                           placeholder="code (e.g. gst)"
                           data-testid={`country-lic-draft-code-${i}`}
                           className="px-2 py-1.5 border border-brand-navy/20 text-sm font-mono" />
                    <input value={l.name}
                           onChange={(e) => patchRow(i, { name: e.target.value })}
                           placeholder="display name"
                           data-testid={`country-lic-draft-name-${i}`}
                           className="px-2 py-1.5 border border-brand-navy/20 text-sm" />
                    <label className="flex items-center gap-1 text-xs text-brand-navy/70">
                      <input type="checkbox" checked={!!l.mandatory}
                             onChange={(e) => patchRow(i, { mandatory: e.target.checked })}
                             data-testid={`country-lic-draft-mand-${i}`} />
                      Mandatory
                    </label>
                    <button onClick={() => removeRow(i)} type="button"
                            data-testid={`country-lic-draft-del-${i}`}
                            className="text-[10px] uppercase tracking-widest px-2 py-1 border border-red-500 text-red-700 hover:bg-red-50">
                      Remove
                    </button>
                  </div>
                ))}
                <div className="flex gap-2 flex-wrap pt-2 border-t border-brand-navy/10">
                  <button type="button" onClick={addRow}
                          data-testid="country-lic-draft-add"
                          className="px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
                    + Add license
                  </button>
                  <button type="button" onClick={save}
                          data-testid="country-lic-draft-save"
                          className="px-4 py-1.5 text-[10px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
                    Save
                  </button>
                  <button type="button" onClick={cancelEdit}
                          data-testid="country-lic-draft-cancel"
                          className="px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy/70">
                    Cancel
                  </button>
                </div>
              </div>
            ) : (
              <div className="mt-2 flex flex-wrap gap-2">
                {(row.licenses || []).map((l) => (
                  <span key={l.code}
                        className={`text-[11px] px-2 py-1 border ${l.mandatory ? "bg-amber-50 border-amber-200 text-amber-900" : "bg-slate-50 border-slate-200 text-slate-700"}`}
                        data-testid={`country-lic-chip-${row.country_code}-${l.code}`}>
                    <span className="font-mono mr-1">{l.code}</span>· {l.name}
                    {l.mandatory ? " ★" : ""}
                  </span>
                ))}
              </div>
            )}
          </div>
        ))}
        {pager.controls}
      </div>
    </div>
  );
}
