import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { mastersApi, showApiError } from "@/lib/api";
import { InfoDot } from "@/components/InfoDot";
import { useListPager } from "@/components/ListPager";

// v50g — Categories master (Masters → Categories).
// Backed by /api/v1/masters/categories, pre-seeded from UNSPSC taxonomy.
export default function CategoriesTab() {
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState("");
  const [countryFilter, setCountryFilter] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [draft, setDraft] = useState({
    code: "", name: "", name_ru: "", name_kz: "",
    country_scope: "", required_licences: "",
    parent_code: "", unspsc_code: "",
    source: "manual", is_active: true,
  });

  const load = useCallback(() => {
    mastersApi
      .listCategories(undefined, { includeInactive: true })
      .then((r) => setRows(Array.isArray(r) ? r : []))
      .catch(showApiError);
  }, []);
  useEffect(() => { load(); }, [load]);

  const filtered = rows.filter((r) => {
    if (!showInactive && r.is_active === false) return false;
    if (sourceFilter && (r.source || "manual") !== sourceFilter) return false;
    if (countryFilter) {
      const cu = countryFilter.toUpperCase();
      const scope = r.country_scope;
      const scoped = scope && scope.length > 0;
      if (scoped && !scope.map((s) => s.toUpperCase()).includes(cu)) return false;
    }
    const q = query.trim().toLowerCase();
    if (!q) return true;
    return [r.code, r.name, r.name_ru, r.name_kz, r.unspsc_code]
      .filter(Boolean)
      .some((s) => String(s).toLowerCase().includes(q));
  });

  const pager = useListPager(filtered, { testid: "categories-pager", pageSize: 50 });

  const create = async () => {
    if (!draft.code || !draft.name) {
      toast.error("Code and name are required.");
      return;
    }
    const payload = {
      ...draft,
      country_scope: draft.country_scope
        ? draft.country_scope.split(",").map((s) => s.trim().toUpperCase()).filter(Boolean)
        : null,
      required_licences: draft.required_licences
        ? draft.required_licences.split(",").map((s) => s.trim()).filter(Boolean)
        : null,
      parent_code: draft.parent_code || null,
      unspsc_code: draft.unspsc_code || null,
    };
    try {
      await mastersApi.createCategory(payload);
      toast.success(`Category "${draft.name}" added.`);
      setShowNew(false);
      setDraft({
        code: "", name: "", name_ru: "", name_kz: "",
        country_scope: "", required_licences: "",
        parent_code: "", unspsc_code: "", source: "manual", is_active: true,
      });
      load();
    } catch (e) { showApiError(e); }
  };

  const toggleActive = async (row) => {
    try {
      if (row.is_active === false) {
        await mastersApi.updateCategory(row.id, {
          ...row,
          is_active: true,
          country_scope: row.country_scope || null,
          required_licences: row.required_licences || null,
        });
        toast.success(`Reactivated · ${row.name}`);
      } else {
        await mastersApi.deactivateCategory(row.id);
        toast.success(`Deactivated · ${row.name}`);
      }
      load();
    } catch (e) { showApiError(e); }
  };

  const total = rows.length;
  const activeCount = rows.filter((r) => r.is_active !== false).length;
  const unspsc = rows.filter((r) => (r.source || "") === "unspsc").length;

  return (
    <div data-testid="categories-tab">
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <strong className="text-sm">{activeCount} active · {total} total</strong>
        <span className="text-xs text-slate-500">({unspsc} UNSPSC-seeded)</span>
        <div className="ml-auto flex gap-2 flex-wrap">
          <input placeholder="Search by name, code or UNSPSC…"
            value={query} onChange={(e) => setQuery(e.target.value)}
            className="px-3 py-2 border text-sm w-72"
            data-testid="categories-search" />
          <input placeholder="Country (e.g. KZ)" value={countryFilter}
            onChange={(e) => setCountryFilter(e.target.value)}
            className="px-3 py-2 border text-sm w-32"
            data-testid="categories-country" />
          <select value={sourceFilter} onChange={(e) => setSourceFilter(e.target.value)}
            className="px-3 py-2 border text-sm bg-white"
            data-testid="categories-source">
            <option value="">All sources</option>
            <option value="manual">Manual</option>
            <option value="unspsc">UNSPSC</option>
            <option value="legacy">Legacy (KZ)</option>
          </select>
          <label className="text-xs flex items-center gap-1 px-2">
            <input type="checkbox" checked={showInactive}
              onChange={(e) => setShowInactive(e.target.checked)}
              data-testid="categories-show-inactive" />
            Show inactive
          </label>
          <button onClick={() => setShowNew((v) => !v)}
            className="px-3 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white"
            data-testid="categories-new-btn">
            {showNew ? "Cancel" : "+ New category"}
          </button>
        </div>
      </div>

      {showNew && (
        <div className="bg-white border p-4 mb-4 grid gap-3 md:grid-cols-3" data-testid="category-new-form">
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Code<InfoDot tip="Unique short code (lowercase, kebab-case). Used in URLs and bid tags." />
            <input value={draft.code}
              onChange={(e) => setDraft({ ...draft, code: e.target.value.toLowerCase().replace(/[^a-z0-9-]+/g, "-") })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="cat-code" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60 md:col-span-2">
            Name (English)<InfoDot tip="Display name shown on the public Notice Board and in the Create Notice form." />
            <input value={draft.name}
              onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="cat-name" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Name (Russian)<InfoDot tip="Optional. Shown when the UI is switched to Russian." />
            <input value={draft.name_ru}
              onChange={(e) => setDraft({ ...draft, name_ru: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="cat-name-ru" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Name (Kazakh)<InfoDot tip="Optional. Shown when the UI is switched to Kazakh." />
            <input value={draft.name_kz}
              onChange={(e) => setDraft({ ...draft, name_kz: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="cat-name-kz" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Country scope<InfoDot tip="Comma-separated ISO-2 country codes (e.g. KZ,RU). Leave blank for all countries." />
            <input value={draft.country_scope}
              onChange={(e) => setDraft({ ...draft, country_scope: e.target.value })}
              placeholder="KZ, RU, UZ"
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="cat-countries" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60 md:col-span-2">
            Required licences<InfoDot tip="Comma-separated. Used by vendor matching so only licensed bidders see this category." />
            <input value={draft.required_licences}
              onChange={(e) => setDraft({ ...draft, required_licences: e.target.value })}
              placeholder="Electrical installation, HSE compliance"
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="cat-licences" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            UNSPSC code<InfoDot tip="Optional. UNSPSC segment/family/class code for spend analytics." />
            <input value={draft.unspsc_code}
              onChange={(e) => setDraft({ ...draft, unspsc_code: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal font-mono"
              data-testid="cat-unspsc" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Parent category code<InfoDot tip="Optional. Parent category code (for hierarchy)." />
            <input value={draft.parent_code}
              onChange={(e) => setDraft({ ...draft, parent_code: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal"
              data-testid="cat-parent" />
          </label>
          <div className="md:col-span-3 flex gap-2">
            <button onClick={create} data-testid="cat-create"
              className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
              Add category
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
              <th className="text-left px-3 py-2">UNSPSC</th>
              <th className="text-left px-3 py-2">Source</th>
              <th className="text-left px-3 py-2">Status</th>
              <th className="text-right px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 && (
              <tr><td colSpan={7} className="p-6 text-slate-500">No categories match the filters.</td></tr>
            )}
            {pager.paged.map((r) => (
              <tr key={r.id || r.code} className="border-t"
                data-testid={`cat-row-${r.code}`}>
                <td className="px-3 py-2 font-mono text-xs">{r.code}</td>
                <td className="px-3 py-2">
                  <div className="font-medium">{r.name}</div>
                  {r.name_ru && <div className="text-xs text-slate-500">{r.name_ru}</div>}
                </td>
                <td className="px-3 py-2 text-xs">
                  {(r.country_scope && r.country_scope.length) ? r.country_scope.join(", ") : "All"}
                </td>
                <td className="px-3 py-2 font-mono text-xs">{r.unspsc_code || "—"}</td>
                <td className="px-3 py-2 text-xs">{r.source || "manual"}</td>
                <td className="px-3 py-2">
                  <span className={`text-[10px] px-2 py-0.5 ${r.is_active === false ? "bg-slate-200 text-slate-600" : "bg-emerald-100 text-emerald-800"}`}>
                    {r.is_active === false ? "Inactive" : "Active"}
                  </span>
                </td>
                <td className="px-3 py-2 text-right">
                  <button onClick={() => toggleActive(r)}
                    className="text-xs underline text-brand-navy"
                    data-testid={`cat-toggle-${r.code}`}>
                    {r.is_active === false ? "Reactivate" : "Deactivate"}
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        {pager.controls}
      </div>
    </div>
  );
}
