import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { adminApi, showApiError } from "@/lib/api";
import { contractTypeOptions } from "@/components/taxonomy";
import { useListPager } from "@/components/ListPager";
import AdminEShell from "./AdminEShell";

// v56t — Review & save Sector/Contract-type codes for legacy notices. The
// backend pre-guesses each code from the notice's category + title; the admin
// corrects as needed and saves so the public taxonomy filters return rows.
export default function AdminTaxonomyBackfillE() {
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [sectors, setSectors] = useState([]);
  const [contractTypes, setContractTypes] = useState([]);
  const [rows, setRows] = useState([]);
  const [onlyUntagged, setOnlyUntagged] = useState(false);
  const [query, setQuery] = useState("");
  const [dirty, setDirty] = useState(() => new Set());

  const load = () => {
    setLoading(true);
    setDirty(new Set());
    adminApi.taxonomyBackfillList().then((d) => {
      setSectors(d.sectors || []);
      setContractTypes(d.contract_types || []);
      setRows((d.items || []).map((n) => ({
        ...n,
        sel_sector: n.sector_code || n.suggested_sector_code || "",
        sel_contract: n.contract_type_code || n.suggested_contract_type_code || "",
      })));
    }).catch(showApiError).finally(() => setLoading(false));
  };
  useEffect(load, []);

  const filtered = useMemo(() => {
    let r = rows;
    if (onlyUntagged) r = r.filter((x) => !x.sector_code || !x.contract_type_code);
    const q = query.trim().toLowerCase();
    if (q) r = r.filter((x) =>
      (x.title || "").toLowerCase().includes(q) ||
      (x.notice_ref || "").toLowerCase().includes(q) ||
      (x.category || "").toLowerCase().includes(q));
    return r;
  }, [rows, onlyUntagged, query]);
  const pager = useListPager(filtered, { testid: "backfill-pager", pageSize: 20 });

  const setCell = (ref, patch) => {
    setRows((rs) => rs.map((x) => (x.notice_ref === ref ? { ...x, ...patch } : x)));
    setDirty((d) => new Set(d).add(ref));
  };

  const applySuggestions = () => {
    const changed = new Set();
    setRows((rs) => rs.map((x) => {
      const ns = x.suggested_sector_code || x.sel_sector;
      const nc = x.suggested_contract_type_code || x.sel_contract;
      if (ns !== x.sel_sector || nc !== x.sel_contract) changed.add(x.notice_ref);
      return { ...x, sel_sector: ns, sel_contract: nc };
    }));
    setDirty((d) => new Set([...d, ...changed]));
  };

  const saveAll = async () => {
    const items = rows.filter((x) => dirty.has(x.notice_ref)).map((x) => ({
      notice_ref: x.notice_ref, sector_code: x.sel_sector, contract_type_code: x.sel_contract,
    }));
    if (items.length === 0) { toast.message("No changes to save"); return; }
    setSaving(true);
    try {
      const res = await adminApi.taxonomyBackfillSave(items);
      toast.success(`Saved taxonomy for ${res.updated} notice${res.updated === 1 ? "" : "s"}`);
      load();
    } catch (e) { showApiError(e); } finally { setSaving(false); }
  };

  const untagged = rows.filter((x) => !x.sector_code || !x.contract_type_code).length;

  return (
    <AdminEShell active="Taxonomy backfill" crumb="Admin / Taxonomy backfill">
      <div className="pmc-card" data-testid="taxonomy-backfill-panel" style={{ padding: 20 }}>
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <h2 className="text-xl font-serif text-brand-navy">Notice taxonomy backfill</h2>
            <p className="text-xs text-brand-navy/70 max-w-2xl mt-1">
              Codes are pre-guessed from each notice's category and title. Review, correct and
              Save so the public homepage Sector / Contract-type filters return real tenders.
              {" "}<strong>{untagged}</strong> of <strong>{rows.length}</strong> notices are missing a code.
            </p>
          </div>
          <div className="flex gap-2">
            <button type="button" onClick={applySuggestions} data-testid="backfill-apply-suggestions"
                    className="px-3 py-2 text-xs uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
              Apply all guesses
            </button>
            <button type="button" onClick={saveAll} disabled={saving || loading || dirty.size === 0} data-testid="backfill-save-all"
                    className="px-4 py-2 text-xs uppercase tracking-widest bg-brand-navy text-white disabled:opacity-50">
              {saving ? "Saving…" : `Save changes${dirty.size ? ` (${dirty.size})` : ""}`}
            </button>
          </div>
        </div>

        <div className="flex items-center gap-4 mt-4 flex-wrap">
          <input value={query} onChange={(e) => setQuery(e.target.value)}
                 placeholder="Search ref, title or category…" data-testid="backfill-search"
                 className="px-3 py-2 border border-brand-navy/20 text-sm bg-white w-full max-w-sm" />
          <label className="flex items-center gap-2 text-xs text-brand-navy/80">
            <input type="checkbox" checked={onlyUntagged} onChange={(e) => setOnlyUntagged(e.target.checked)}
                   data-testid="backfill-only-untagged" />
            Only untagged
          </label>
        </div>

        <div className="mt-4 bg-white border border-brand-navy/10 overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-brand-navy text-white uppercase text-xs tracking-widest">
              <tr>
                <th className="px-3 py-2 text-left">Notice</th>
                <th className="px-3 py-2 text-left">Category</th>
                <th className="px-3 py-2 text-left">Sector</th>
                <th className="px-3 py-2 text-left">Contract type</th>
              </tr>
            </thead>
            <tbody>
              {loading && <tr><td colSpan={4} className="text-center py-10 text-brand-navy/60">Loading…</td></tr>}
              {!loading && pager.paged.map((x) => {
                const sugS = x.suggested_sector_code && x.suggested_sector_code !== x.sel_sector;
                const sugC = x.suggested_contract_type_code && x.suggested_contract_type_code !== x.sel_contract;
                return (
                  <tr key={x.notice_ref} className="border-b border-brand-navy/10 align-top"
                      data-testid={`backfill-row-${x.notice_ref}`}>
                    <td className="px-3 py-2">
                      <div className="font-mono text-xs text-brand-navy/70">{x.notice_ref}</div>
                      <div className="max-w-[320px] truncate">{x.title}</div>
                      {!x.is_published && <span className="text-[10px] uppercase text-amber-700">draft</span>}
                    </td>
                    <td className="px-3 py-2 text-brand-navy/80">{x.category || "—"}</td>
                    <td className="px-3 py-2">
                      <select value={x.sel_sector} onChange={(e) => setCell(x.notice_ref, { sel_sector: e.target.value })}
                              data-testid={`backfill-sector-${x.notice_ref}`}
                              className="px-2 py-1 border bg-white text-xs min-w-[180px]">
                        <option value="">— none —</option>
                        {sectors.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
                      </select>
                      {sugS && (
                        <button type="button" className="block mt-1 text-[11px] text-brand-brass hover:underline"
                                onClick={() => setCell(x.notice_ref, { sel_sector: x.suggested_sector_code })}
                                data-testid={`backfill-sector-sug-${x.notice_ref}`}>
                          guess: {(sectors.find((s) => s.code === x.suggested_sector_code) || {}).name || x.suggested_sector_code}
                        </button>
                      )}
                    </td>
                    <td className="px-3 py-2">
                      <select value={x.sel_contract} onChange={(e) => setCell(x.notice_ref, { sel_contract: e.target.value })}
                              data-testid={`backfill-contract-${x.notice_ref}`}
                              className="px-2 py-1 border bg-white text-xs min-w-[180px]">
                        <option value="">— none —</option>
                        {contractTypeOptions(contractTypes)}
                      </select>
                      {sugC && (
                        <button type="button" className="block mt-1 text-[11px] text-brand-brass hover:underline"
                                onClick={() => setCell(x.notice_ref, { sel_contract: x.suggested_contract_type_code })}
                                data-testid={`backfill-contract-sug-${x.notice_ref}`}>
                          guess: {(contractTypes.find((c) => c.code === x.suggested_contract_type_code) || {}).name || x.suggested_contract_type_code}
                        </button>
                      )}
                    </td>
                  </tr>
                );
              })}
              {!loading && filtered.length === 0 && (
                <tr><td colSpan={4} className="text-center py-10 text-brand-navy/60">No notices match.</td></tr>
              )}
            </tbody>
          </table>
          {pager.controls}
        </div>
      </div>
    </AdminEShell>
  );
}
