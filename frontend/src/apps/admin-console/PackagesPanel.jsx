import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { adminApi, api, formatApiError, showApiError, downloadAuthedFile } from "@/lib/api";
import KanbanColumn from "./packages/KanbanColumn";
import { InfoDot } from "@/components/InfoDot";
import CreatorDateFilterBar, { matchCreatorDate } from "@/components/CreatorDateFilterBar";

const COLUMNS = [
  { code: "backlog", label: "Backlog" },
  { code: "scoping", label: "Scoping" },
  { code: "sbd_draft", label: "SBD Draft" },
  { code: "ready", label: "Ready" },
  { code: "published", label: "Published" },
  { code: "cancelled", label: "Cancelled" },
];

const fmt = (v, cur = "USD") =>
  v == null ? "—" : new Intl.NumberFormat("en-US", { style: "currency", currency: cur, maximumFractionDigits: 0 }).format(v);

export default function PackagesPanel() {
  const [packages, setPackages] = useState([]);
  const [loading, setLoading] = useState(true);
  const [importing, setImporting] = useState(false);
  const [showNew, setShowNew] = useState(false);
  const [search, setSearch] = useState("");
  const [newDraft, setNewDraft] = useState({ title: "", category: "", phase: "", value: "", float_target_date: "", status: "backlog" });
  // v52v — Created by / from / to filter.
  const [cdf, setCdf] = useState({ createdBy: "", from: "", to: "" });
  const pkgCreators = useMemo(() => packages.map((p) => p.created_by_email).filter(Boolean), [packages]);
  const visiblePackages = useMemo(() => packages.filter(matchCreatorDate(cdf)), [packages, cdf]);

  const load = useCallback(() => {
    setLoading(true);
    adminApi.listPackages({ limit: 1000 })
      .then((d) => setPackages(d.items || []))
      .catch((e) => showApiError(e))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);

  const grouped = COLUMNS.reduce((acc, col) => {
    const q = search.trim().toLowerCase();
    const visible = q ? packages.filter((p) =>
      (p.title || "").toLowerCase().includes(q)
      || (p.category || "").toLowerCase().includes(q)
      || (p.phase || "").toLowerCase().includes(q)) : packages;
    acc[col.code] = visible.filter((p) => p.status === col.code);
    return acc;
  }, {});

  const onDragStart = (e, pkg) => {
    e.dataTransfer.setData("text/plain", pkg.id);
    e.dataTransfer.effectAllowed = "move";
  };
  const onDragOver = (e) => { e.preventDefault(); e.dataTransfer.dropEffect = "move"; };
  const onDrop = async (e, targetStatus) => {
    e.preventDefault();
    const id = e.dataTransfer.getData("text/plain");
    const pkg = packages.find((p) => p.id === id);
    if (!pkg || pkg.status === targetStatus) return;
    setPackages((prev) => prev.map((p) => (p.id === id ? { ...p, status: targetStatus } : p)));
    try {
      await api.post(`/api/v1/packages/${id}/status`, { status: targetStatus });
      toast.success(`Moved to ${targetStatus}`);
    } catch (err) {
      showApiError(err);
      load();
    }
  };

  const onImport = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    setImporting(true);
    try {
      const fd = new FormData();
      fd.append("file", file);
      const r = await api.post("/api/v1/packages/import", fd, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      toast.success(`Imported ${r.data.created} packages (skipped ${r.data.skipped})`);
      e.target.value = "";
      load();
    } catch (err) {
      showApiError(err);
    } finally {
      setImporting(false);
    }
  };

  const createOne = async () => {
    if (!newDraft.title || !newDraft.category) {
      toast.error("Title and category are required");
      return;
    }
    try {
      await adminApi.createPackage({
        title: newDraft.title,
        category: newDraft.category,
        phase: newDraft.phase || undefined,
        value: newDraft.value ? parseFloat(newDraft.value) : undefined,
        float_target_date: newDraft.float_target_date || undefined,
        status: newDraft.status,
      });
      toast.success("Package created");
      setShowNew(false);
      setNewDraft({ title: "", category: "", phase: "", value: "", float_target_date: "", status: "backlog" });
      load();
    } catch (err) {
      showApiError(err);
    }
  };

  return (
    <div data-testid="admin-packages-panel">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div className="text-sm text-brand-navy/70">
          {loading ? "Loading packages…" : `${packages.length} packages in pipeline · drag cards between columns to move status`}
        </div>
        <div className="flex items-center gap-2">
          <input value={search} onChange={(e) => setSearch(e.target.value)}
            placeholder="Search packages by title, category or phase…"
            data-testid="pkg-search"
            className="px-3 py-2 border border-brand-navy/20 text-sm bg-white min-w-[220px]" />
          <CreatorDateFilterBar value={cdf} onChange={setCdf} creators={pkgCreators} testid="pkg-cdf" />
          <label data-testid="pkg-import-label"
            className={"px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy bg-white hover:border-brand-navy-soft/60 cursor-pointer " + (importing ? "opacity-50" : "")}>
            {importing ? "Importing…" : "Import CSV"}
            <input type="file" accept=".csv" onChange={onImport} disabled={importing} className="hidden" data-testid="pkg-import-input" />
          </label>
          {/* v52br — authenticated blob download; raw <a href> 401'd on the
              admin-gated sample endpoint (same class as the tender PDF bug). */}
          <button type="button"
             onClick={async () => {
               try { await downloadAuthedFile("/api/v1/packages/import/sample.csv", "pmc-work-packages-sample.csv"); }
               catch (e) { showApiError(e, { fallbackTitle: "Sample download failed" }); }
             }}
             data-testid="pkg-import-sample"
             title="Download a sample CSV with the exact column headers the importer expects"
             className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy bg-white hover:border-brand-navy-soft/60">
            Sample CSV
          </button>
          <button type="button" onClick={() => setShowNew(!showNew)} data-testid="pkg-new-toggle"
            className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            {showNew ? "Cancel" : "New package"}
          </button>
        </div>
      </div>

      {showNew && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-3 md:grid-cols-6" data-testid="pkg-new-form">
          <label className="md:col-span-3 text-xs uppercase tracking-widest text-brand-navy/60">
            Title<InfoDot tip="Package name shown on the Kanban card. Free text. Example: 'Substation SS-401 civil works'." />
            <input placeholder="Title" data-testid="pkg-new-title" value={newDraft.title} onChange={(e) => setNewDraft({ ...newDraft, title: e.target.value })} className="mt-1 w-full px-3 py-2 border border-brand-navy/20 normal-case tracking-normal" />
          </label>
          <label className="md:col-span-2 text-xs uppercase tracking-widest text-brand-navy/60">
            Category<InfoDot tip="Commodity / discipline. Groups packages by trade for the Master Admin's rollup views." />
            <input placeholder="Category" data-testid="pkg-new-category" value={newDraft.category} onChange={(e) => setNewDraft({ ...newDraft, category: e.target.value })} className="mt-1 w-full px-3 py-2 border border-brand-navy/20 normal-case tracking-normal" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Phase<InfoDot tip="Optional. Project phase (e.g. FEED, EPC, O&M). Used only for reporting." />
            <input placeholder="Phase" data-testid="pkg-new-phase" value={newDraft.phase} onChange={(e) => setNewDraft({ ...newDraft, phase: e.target.value })} className="mt-1 w-full px-3 py-2 border border-brand-navy/20 normal-case tracking-normal" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Value (USD)<InfoDot tip="Estimated contract value in USD. Feeds the pipeline-total analytics widget." />
            <input placeholder="Value (USD)" data-testid="pkg-new-value" type="number" value={newDraft.value} onChange={(e) => setNewDraft({ ...newDraft, value: e.target.value })} className="mt-1 w-full px-3 py-2 border border-brand-navy/20 normal-case tracking-normal" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Float target<InfoDot tip="Planned date to publish the Notice for this package. Drives the deadline alerts on the Kanban card." />
            <input placeholder="Float target (YYYY-MM-DD)" data-testid="pkg-new-date" type="date" value={newDraft.float_target_date} onChange={(e) => setNewDraft({ ...newDraft, float_target_date: e.target.value })} className="mt-1 w-full px-3 py-2 border border-brand-navy/20 normal-case tracking-normal" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Status<InfoDot tip="Starting Kanban column. You can drag the card between columns later — the history is audited." />
            <select data-testid="pkg-new-status" value={newDraft.status} onChange={(e) => setNewDraft({ ...newDraft, status: e.target.value })} className="mt-1 w-full px-3 py-2 border border-brand-navy/20 normal-case tracking-normal">
              {COLUMNS.map((c) => (<option key={c.code} value={c.code}>{c.label}</option>))}
            </select>
          </label>
          <button type="button" onClick={createOne} data-testid="pkg-new-create" className="md:col-span-2 px-6 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">Create</button>
        </div>
      )}

      {/* Work-package Kanban: horizontal scroll instead of 6 cramped columns
         on wide screens so each card has breathing room and titles don't
         wrap into unreadable shards. v51ag. */}
      <div className="overflow-x-auto -mx-6 px-6 pb-2" data-testid="pkg-board-scroll">
        <div className="flex gap-3" data-testid="pkg-board" style={{ minWidth: "100%" }}>
          {COLUMNS.map((col) => (
            <div key={col.code} className="w-[280px] shrink-0">
              <KanbanColumn
                column={col}
                items={grouped[col.code] || []}
                onDragOver={onDragOver}
                onDrop={onDrop}
                onDragStart={onDragStart}
                fmt={fmt}
              />
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
