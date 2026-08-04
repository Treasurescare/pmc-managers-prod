import { useEffect, useState } from "react";
import { toast } from "sonner";
import { tenderTemplateApi, formatApiError } from "@/lib/api";

/**
 * VersionHistory — sidebar drawer listing every rolling snapshot of a tender
 * template. Admins pick a snapshot, get a plain-English preview, and hit
 * Restore. The restore itself is auto-snapshotted so it can be undone.
 */
export default function VersionHistory({ templateId, onRestored, onClose }) {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (!templateId) return;
    setLoading(true);
    tenderTemplateApi.listVersions(templateId)
      .then((d) => setItems(d.versions || []))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => setLoading(false));
  }, [templateId]);

  const restore = async (index) => {
    if (!confirm("Restore this snapshot? Your current draft will be saved as a new snapshot before restoring.")) return;
    setBusy(true);
    try {
      const doc = await tenderTemplateApi.restoreVersion(templateId, index);
      toast.success(`Restored — version ${doc.version || "-"}`);
      onRestored(doc);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-40 bg-slate-900/40" onClick={(e) => { if (e.target === e.currentTarget) onClose(); }}
         data-testid="version-history-drawer">
      <aside className="absolute right-0 top-0 h-full w-full max-w-md bg-white border-l border-brand-navy/10 flex flex-col shadow-2xl">
        <header className="border-b border-brand-navy/10 px-5 py-4 flex items-center justify-between">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">Version history</div>
            <h3 className="font-display text-xl text-brand-navy">Rolling snapshots</h3>
          </div>
          <button onClick={onClose} data-testid="version-history-close"
                  className="px-3 py-1 text-xs uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-pale">
            Close
          </button>
        </header>
        <div className="flex-1 overflow-auto p-5 space-y-2">
          {loading && <div className="text-sm text-brand-navy/50">Loading…</div>}
          {!loading && items.length === 0 && (
            <div className="text-sm text-brand-navy/50 italic">
              No prior snapshots — save some edits and the history will populate here.
            </div>
          )}
          {items.map((v) => (
            <div key={v.index} className="border border-brand-navy/10 p-3 text-sm bg-brand-pale/30"
                 data-testid={`version-row-${v.index}`}>
              <div className="flex items-baseline justify-between gap-3">
                <div>
                  <div className="font-semibold text-brand-navy truncate">{v.name}</div>
                  <div className="text-[11px] text-brand-navy/60 mt-0.5">
                    {v.saved_at?.slice(0, 19).replace("T", " ")} · by {v.saved_by || "system"} · {v.section_count} sections
                  </div>
                </div>
                <button onClick={() => restore(v.index)} disabled={busy}
                        data-testid={`version-restore-${v.index}`}
                        className="px-3 py-1 text-[11px] uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-40">
                  Restore
                </button>
              </div>
            </div>
          ))}
        </div>
      </aside>
    </div>
  );
}
