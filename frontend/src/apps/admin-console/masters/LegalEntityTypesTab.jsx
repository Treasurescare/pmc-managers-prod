import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { mastersApi, showApiError } from "@/lib/api";

/**
 * v50y — Legal entity types master.
 * Backs the "Legal entity type" dropdown in vendor registration Section A.
 */
export default function LegalEntityTypesTab() {
  const [rows, setRows] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [showInactive, setShowInactive] = useState(false);
  const [draft, setDraft] = useState({
    code: "", name: "", name_ru: "", name_kz: "",
    country_scope: "", description: "",
  });

  const load = useCallback(() => {
    mastersApi.listLegalEntityTypes({ includeInactive: true })
      .then((r) => setRows(Array.isArray(r) ? r : []))
      .catch(showApiError);
  }, []);
  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!draft.code || !draft.name) {
      toast.error("Code and name are required.");
      return;
    }
    const payload = {
      ...draft,
      code: draft.code.toLowerCase().replace(/[^a-z0-9_-]+/g, "_"),
      country_scope: draft.country_scope
        ? draft.country_scope.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean)
        : null,
      is_active: true,
    };
    try {
      await mastersApi.createLegalEntityType(payload);
      toast.success(`"${draft.name}" added.`);
      setShowNew(false);
      setDraft({ code: "", name: "", name_ru: "", name_kz: "", country_scope: "", description: "" });
      load();
    } catch (e) { showApiError(e); }
  };

  const toggleActive = async (row) => {
    try {
      if (row.is_active === false) {
        await mastersApi.updateLegalEntityType(row.id, {
          code: row.code, name: row.name, name_ru: row.name_ru,
          name_kz: row.name_kz, country_scope: row.country_scope,
          description: row.description, is_active: true,
        });
        toast.success(`Reactivated · ${row.name}`);
      } else {
        await mastersApi.deactivateLegalEntityType(row.id);
        toast.success(`Deactivated · ${row.name}`);
      }
      load();
    } catch (e) { showApiError(e); }
  };

  const filtered = rows.filter((r) => showInactive || r.is_active !== false);
  const total = rows.length;
  const activeCount = rows.filter((r) => r.is_active !== false).length;

  return (
    <div data-testid="legal-entity-types-tab">
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <strong className="text-sm">{activeCount} active · {total} total</strong>
        <div className="ml-auto flex gap-2 flex-wrap">
          <label className="text-xs flex items-center gap-1 px-2">
            <input type="checkbox" checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              data-testid="legal-show-inactive" />
            Show inactive
          </label>
          <button onClick={() => setShowNew((v) => !v)}
            className="px-3 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white"
            data-testid="legal-new-btn">
            {showNew ? "Cancel" : "+ New legal entity type"}
          </button>
        </div>
      </div>

      {showNew && (
        <div className="bg-white border p-4 mb-4 grid gap-3 md:grid-cols-3" data-testid="legal-new-form">
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Code
            <input value={draft.code}
              onChange={(e) => setDraft({ ...draft, code: e.target.value.toLowerCase().replace(/[^a-z0-9_-]+/g, "_") })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="legal-code" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60 md:col-span-2">
            Name (English)
            <input value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="legal-name" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Name (Russian)
            <input value={draft.name_ru}
              onChange={(e) => setDraft({ ...draft, name_ru: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="legal-name-ru" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Name (Kazakh)
            <input value={draft.name_kz}
              onChange={(e) => setDraft({ ...draft, name_kz: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="legal-name-kz" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Country scope
            <input value={draft.country_scope}
              onChange={(e) => setDraft({ ...draft, country_scope: e.target.value })}
              placeholder="KZ, RU — blank = all"
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="legal-countries" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60 md:col-span-3">
            Description
            <input value={draft.description}
              onChange={(e) => setDraft({ ...draft, description: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="legal-desc" />
          </label>
          <div className="md:col-span-3 flex gap-2">
            <button onClick={create} data-testid="legal-create"
              className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
              Add legal entity type
            </button>
          </div>
        </div>
      )}

      <div className="bg-white border overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs uppercase tracking-widest text-slate-500 bg-slate-50">
            <tr>
              <th className="text-left px-3 py-2">Code</th>
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Countries</th>
              <th className="text-left px-3 py-2">Status</th>
              <th className="text-right px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={5} className="p-6 text-slate-500">No legal entity types yet. The dropdown falls back to a sensible default list for vendors.</td></tr>
            )}
            {filtered.map((r) => (
              <tr key={r.id || r.code} className="border-t"
                data-testid={`legal-row-${r.code}`}>
                <td className="px-3 py-2 font-mono text-xs">{r.code}</td>
                <td className="px-3 py-2">
                  <div className="font-medium">{r.name}</div>
                  {r.name_ru && <div className="text-xs text-slate-500">{r.name_ru}</div>}
                  {r.description && <div className="text-xs text-slate-500 italic">{r.description}</div>}
                </td>
                <td className="px-3 py-2 text-xs">
                  {(r.country_scope && r.country_scope.length) ? r.country_scope.join(", ") : "All"}
                </td>
                <td className="px-3 py-2">
                  <span className={`text-[10px] px-2 py-0.5 ${r.is_active === false ? "bg-slate-200 text-slate-600" : "bg-emerald-100 text-emerald-800"}`}>
                    {r.is_active === false ? "Inactive" : "Active"}
                  </span>
                </td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => toggleActive(r)}
                    className="text-xs underline text-brand-navy"
                    data-testid={`legal-toggle-${r.code}`}>
                    {r.is_active === false ? "Reactivate" : "Deactivate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
