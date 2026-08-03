import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, api, formatApiError } from "@/lib/api";
import KanbanColumn from "./packages/KanbanColumn";

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
  const [newDraft, setNewDraft] = useState({ title: "", category: "", phase: "", value: "", float_target_date: "", status: "backlog" });

  const load = useCallback(() => {
    setLoading(true);
    adminApi.listPackages({ limit: 1000 })
      .then((d) => setPackages(d.items || []))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => setLoading(false));
  }, []);
  useEffect(() => { load(); }, [load]);

  const grouped = COLUMNS.reduce((acc, col) => {
    acc[col.code] = packages.filter((p) => p.status === col.code);
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
      toast.error(formatApiError(err));
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
      toast.error(formatApiError(err));
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
      toast.error(formatApiError(err));
    }
  };

  return (
    <div data-testid="admin-packages-panel">
      <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
        <div className="text-sm text-brand-navy/70">
          {loading ? "Loading packages…" : `${packages.length} packages in pipeline · drag cards between columns to move status`}
        </div>
        <div className="flex items-center gap-2">
          <label data-testid="pkg-import-label"
            className={"px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy bg-white hover:border-brand-navy-soft/60 cursor-pointer " + (importing ? "opacity-50" : "")}>
            {importing ? "Importing…" : "Import CSV"}
            <input type="file" accept=".csv" onChange={onImport} disabled={importing} className="hidden" data-testid="pkg-import-input" />
          </label>
          <button type="button" onClick={() => setShowNew(!showNew)} data-testid="pkg-new-toggle"
            className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            {showNew ? "Cancel" : "New package"}
          </button>
        </div>
      </div>

      {showNew && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-3 md:grid-cols-6" data-testid="pkg-new-form">
          <input placeholder="Title" data-testid="pkg-new-title" value={newDraft.title} onChange={(e) => setNewDraft({ ...newDraft, title: e.target.value })} className="md:col-span-3 px-3 py-2 border border-brand-navy/20" />
          <input placeholder="Category" data-testid="pkg-new-category" value={newDraft.category} onChange={(e) => setNewDraft({ ...newDraft, category: e.target.value })} className="md:col-span-2 px-3 py-2 border border-brand-navy/20" />
          <input placeholder="Phase" data-testid="pkg-new-phase" value={newDraft.phase} onChange={(e) => setNewDraft({ ...newDraft, phase: e.target.value })} className="px-3 py-2 border border-brand-navy/20" />
          <input placeholder="Value (USD)" data-testid="pkg-new-value" type="number" value={newDraft.value} onChange={(e) => setNewDraft({ ...newDraft, value: e.target.value })} className="px-3 py-2 border border-brand-navy/20" />
          <input placeholder="Float target (YYYY-MM-DD)" data-testid="pkg-new-date" type="date" value={newDraft.float_target_date} onChange={(e) => setNewDraft({ ...newDraft, float_target_date: e.target.value })} className="px-3 py-2 border border-brand-navy/20" />
          <select data-testid="pkg-new-status" value={newDraft.status} onChange={(e) => setNewDraft({ ...newDraft, status: e.target.value })} className="px-3 py-2 border border-brand-navy/20">
            {COLUMNS.map((c) => (<option key={c.code} value={c.code}>{c.label}</option>))}
          </select>
          <button type="button" onClick={createOne} data-testid="pkg-new-create" className="md:col-span-2 px-6 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">Create</button>
        </div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-3 xl:grid-cols-6 gap-3" data-testid="pkg-board">
        {COLUMNS.map((col) => (
          <KanbanColumn
            key={col.code}
            column={col}
            items={grouped[col.code] || []}
            onDragOver={onDragOver}
            onDrop={onDrop}
            onDragStart={onDragStart}
            fmt={fmt}
          />
        ))}
      </div>
    </div>
  );
}
