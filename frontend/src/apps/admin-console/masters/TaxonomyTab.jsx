import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { mastersApi, showApiError } from "@/lib/api";

// v56q — generic 2-level taxonomy master (Sector / Contract type) used above
// the UNSPSC commodity categories. Grouped by parent_code in the table.
const APIS = {
  sector: {
    list: (o) => mastersApi.listSectors(o), create: mastersApi.createSector,
    update: mastersApi.updateSector, deactivate: mastersApi.deactivateSector,
  },
  contract_type: {
    list: (o) => mastersApi.listContractTypes(o), create: mastersApi.createContractType,
    update: mastersApi.updateContractType, deactivate: mastersApi.deactivateContractType,
  },
};

export default function TaxonomyTab({ kind, label }) {
  const A = APIS[kind];
  const [rows, setRows] = useState([]);
  const [query, setQuery] = useState("");
  const [showInactive, setShowInactive] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [draft, setDraft] = useState({ code: "", name: "", parent_code: "" });

  const load = useCallback(() => {
    A.list({ includeInactive: true })
      .then((r) => setRows(Array.isArray(r) ? r : []))
      .catch(showApiError);
  }, [A]);
  useEffect(() => { load(); }, [load]);

  const parents = rows.filter((r) => !r.parent_code);
  const childrenOf = (code) => rows.filter((r) => r.parent_code === code);

  const q = query.trim().toLowerCase();
  const matchQ = (r) => !q || [r.code, r.name].some((s) => String(s || "").toLowerCase().includes(q));
  const visible = (r) => (showInactive || r.is_active !== false) && matchQ(r);

  const create = async () => {
    if (!draft.code || !draft.name) { toast.error("Code and name are required."); return; }
    try {
      await A.create({ code: draft.code, name: draft.name, parent_code: draft.parent_code || null, is_active: true });
      toast.success(`${label} "${draft.name}" added.`);
      setShowNew(false); setDraft({ code: "", name: "", parent_code: "" }); load();
    } catch (e) { showApiError(e); }
  };

  const toggleActive = async (row) => {
    try {
      if (row.is_active === false) {
        await A.update(row.id, { code: row.code, name: row.name, parent_code: row.parent_code || null, is_active: true });
        toast.success(`Reactivated · ${row.name}`);
      } else {
        await A.deactivate(row.id);
        toast.success(`Deactivated · ${row.name}`);
      }
      load();
    } catch (e) { showApiError(e); }
  };

  const Row = ({ r, child }) => (
    <tr className="border-t" data-testid={`${kind}-row-${r.code}`}>
      <td className="px-3 py-2 font-mono text-xs">{r.code}</td>
      <td className="px-3 py-2">
        <span className={child ? "pl-4 text-slate-700" : "font-semibold text-brand-navy"}>
          {child ? "↳ " : ""}{r.name}
        </span>
      </td>
      <td className="px-3 py-2">
        <span className={`text-[10px] px-2 py-0.5 ${r.is_active === false ? "bg-slate-200 text-slate-600" : "bg-emerald-100 text-emerald-800"}`}>
          {r.is_active === false ? "Inactive" : "Active"}
        </span>
      </td>
      <td className="px-3 py-2 text-right">
        <button onClick={() => toggleActive(r)} className="text-xs underline text-brand-navy"
          data-testid={`${kind}-toggle-${r.code}`}>
          {r.is_active === false ? "Reactivate" : "Deactivate"}
        </button>
      </td>
    </tr>
  );

  const active = rows.filter((r) => r.is_active !== false).length;

  return (
    <div data-testid={`${kind}-tab`}>
      <div className="flex items-center gap-3 mb-3 flex-wrap">
        <strong className="text-sm">{active} active · {rows.length} total</strong>
        <span className="text-xs text-slate-500">(sits above UNSPSC commodity codes)</span>
        <div className="ml-auto flex gap-2 flex-wrap">
          <input placeholder="Search name or code…" value={query}
            onChange={(e) => setQuery(e.target.value)} className="px-3 py-2 border text-sm w-64"
            data-testid={`${kind}-search`} />
          <label className="text-xs flex items-center gap-1 px-2">
            <input type="checkbox" checked={showInactive} onChange={(e) => setShowInactive(e.target.checked)}
              data-testid={`${kind}-show-inactive`} />
            Show inactive
          </label>
          <button onClick={() => setShowNew((v) => !v)}
            className="px-3 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white"
            data-testid={`${kind}-new-btn`}>
            {showNew ? "Cancel" : `+ New ${label.toLowerCase()}`}
          </button>
        </div>
      </div>

      {showNew && (
        <div className="bg-white border p-4 mb-4 grid gap-3 md:grid-cols-3" data-testid={`${kind}-new-form`}>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Code
            <input value={draft.code}
              onChange={(e) => setDraft({ ...draft, code: e.target.value.toLowerCase().replace(/[^a-z0-9-]+/g, "-") })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid={`${kind}-code`} />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60 md:col-span-2">
            Name
            <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid={`${kind}-name`} />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60 md:col-span-3">
            Parent (leave blank for a top-level {label.toLowerCase()})
            <select value={draft.parent_code} onChange={(e) => setDraft({ ...draft, parent_code: e.target.value })}
              className="mt-1 w-full px-3 py-2 border bg-white normal-case tracking-normal" data-testid={`${kind}-parent`}>
              <option value="">— top level —</option>
              {parents.map((p) => <option key={p.code} value={p.code}>{p.name}</option>)}
            </select>
          </label>
          <div className="md:col-span-3">
            <button onClick={create} data-testid={`${kind}-create`}
              className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
              Add {label.toLowerCase()}
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
              <th className="text-left px-3 py-2">Status</th>
              <th className="text-right px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={4} className="p-6 text-slate-500">No {label.toLowerCase()}s yet.</td></tr>
            )}
            {parents.filter(visible).map((p) => (
              <>
                <Row key={p.code} r={p} />
                {childrenOf(p.code).filter(visible).map((c) => <Row key={c.code} r={c} child />)}
              </>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
