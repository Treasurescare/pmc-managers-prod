import { useRef, useState } from "react";
import { toast } from "sonner";
import { uploadsApi, showApiError } from "@/lib/api";

/**
 * v51bd — Reusable evidence-file manager used by:
 *   • admin blacklist modal (full CRUD + print)
 *   • vendor appeal panel (vendor-side upload + view + delete)
 *
 * Accepts either a document (pdf/image) OR a camera-captured photo
 * (uses <input accept="image/*" capture="environment"> which opens the
 * device camera on mobile and falls back to the file picker on desktop).
 *
 * Props:
 *   items        : [{ key, filename, content_type, size_bytes, note, added_by,
 *                      added_at, source }]
 *   readOnly     : hide add/delete buttons (viewer-only)
 *   onAdd(entry) : called after successful upload with the new evidence entry
 *   onDelete(i)  : called when the delete button is clicked
 *   title        : section heading
 *   scope        : upload scope (default "blacklist-evidence")
 */
export default function EvidenceManager({
  items = [],
  readOnly = false,
  onAdd,
  onDelete,
  title = "Evidence",
  scope = "blacklist-evidence",
  testIdPrefix = "ev",
}) {
  const fileRef = useRef(null);
  const camRef = useRef(null);
  const [busy, setBusy] = useState(false);
  const [note, setNote] = useState("");

  const upload = async (file) => {
    if (!file) return;
    if (file.size > 10 * 1024 * 1024) {
      toast.error("File too large — keep evidence under 10 MB");
      return;
    }
    setBusy(true);
    try {
      const p = await uploadsApi.presign(file.name, file.type || "application/octet-stream", scope, file.size);
      await uploadsApi.direct(p.key, file);
      const entry = {
        key: p.key, filename: file.name,
        content_type: file.type || "application/octet-stream",
        size_bytes: file.size, note: note.trim() || null,
      };
      await onAdd?.(entry);
      setNote("");
      toast.success(`Attached ${file.name}`);
    } catch (e) {
      showApiError(e, { fallbackTitle: "Could not attach evidence" });
    } finally {
      setBusy(false);
      if (fileRef.current) fileRef.current.value = "";
      if (camRef.current) camRef.current.value = "";
    }
  };

  const printItem = (item) => {
    uploadsApi.openInNewTab(item.key, { filename: item.filename })
      .catch((e) => showApiError(e, { fallbackTitle: "Could not open file" }));
    // Hint to the user — the opened tab has the browser's native print.
    setTimeout(() => toast.info("Press Ctrl/⌘+P in the opened tab to print."), 400);
  };

  return (
    <div data-testid={`${testIdPrefix}-wrap`} className="border border-slate-200 bg-slate-50 p-3">
      <div className="flex items-center justify-between gap-2 mb-2">
        <div className="text-[11px] uppercase tracking-widest text-slate-600 font-semibold">{title}</div>
        <span className="text-[11px] text-slate-500">{items.length} attached</span>
      </div>

      {!readOnly && (
        <div className="mb-3 bg-white border border-slate-200 p-2 space-y-2">
          <input
            value={note}
            onChange={(e) => setNote(e.target.value)}
            placeholder="Optional note for this piece of evidence"
            className="w-full px-2 py-1.5 border border-slate-300 text-sm"
            data-testid={`${testIdPrefix}-note`}
          />
          <div className="flex gap-2 flex-wrap">
            <input ref={fileRef} type="file" hidden
              accept="application/pdf,image/*,.doc,.docx,.xls,.xlsx"
              onChange={(e) => upload(e.target.files?.[0])}
              data-testid={`${testIdPrefix}-file-input`} />
            <input ref={camRef} type="file" hidden
              accept="image/*" capture="environment"
              onChange={(e) => upload(e.target.files?.[0])}
              data-testid={`${testIdPrefix}-cam-input`} />
            <button type="button" disabled={busy}
              onClick={() => fileRef.current?.click()}
              className="text-[11px] uppercase tracking-widest px-3 py-1.5 border border-slate-800 text-slate-800 hover:bg-slate-800 hover:text-white disabled:opacity-50"
              data-testid={`${testIdPrefix}-upload-btn`}>
              {busy ? "Uploading…" : "Upload document"}
            </button>
            <button type="button" disabled={busy}
              onClick={() => camRef.current?.click()}
              className="text-[11px] uppercase tracking-widest px-3 py-1.5 border border-emerald-700 text-emerald-800 hover:bg-emerald-700 hover:text-white disabled:opacity-50"
              data-testid={`${testIdPrefix}-capture-btn`}>
              Capture photo
            </button>
          </div>
        </div>
      )}

      {items.length === 0 ? (
        <div className="text-xs text-slate-500 italic py-2" data-testid={`${testIdPrefix}-empty`}>
          No evidence attached yet.
        </div>
      ) : (
        <ul className="divide-y divide-slate-200 bg-white border border-slate-200">
          {items.map((it, i) => (
            <li key={`${it.key}-${i}`}
                className="flex items-center justify-between gap-3 p-2 text-sm"
                data-testid={`${testIdPrefix}-row-${i}`}>
              <div className="min-w-0 flex-1">
                <div className="font-medium text-slate-800 truncate">{it.filename || it.key}</div>
                <div className="text-[11px] text-slate-500">
                  {(it.content_type || "file")}
                  {it.size_bytes ? ` · ${(it.size_bytes / 1024).toFixed(1)} KB` : ""}
                  {it.added_by ? ` · by ${it.added_by}` : ""}
                  {it.added_at ? ` · ${(it.added_at || "").slice(0, 19).replace("T", " ")}` : ""}
                  {it.source ? ` · ${it.source}` : ""}
                </div>
                {it.note && (
                  <div className="text-xs text-slate-600 italic mt-0.5">“{it.note}”</div>
                )}
              </div>
              <div className="flex gap-1 shrink-0">
                <button type="button"
                  onClick={() => uploadsApi.openInNewTab(it.key, { filename: it.filename })
                                            .catch((e) => showApiError(e, { fallbackTitle: "Could not open file" }))}
                  className="text-[11px] uppercase tracking-widest px-2 py-1 border border-slate-400 text-slate-700 hover:bg-slate-100"
                  data-testid={`${testIdPrefix}-view-${i}`}>View</button>
                <button type="button"
                  onClick={() => uploadsApi.openInNewTab(it.key, { download: true, filename: it.filename })
                                            .catch((e) => showApiError(e, { fallbackTitle: "Could not download" }))}
                  className="text-[11px] uppercase tracking-widest px-2 py-1 border border-slate-400 text-slate-700 hover:bg-slate-100"
                  data-testid={`${testIdPrefix}-dl-${i}`}>Download</button>
                <button type="button"
                  onClick={() => printItem(it)}
                  className="text-[11px] uppercase tracking-widest px-2 py-1 border border-slate-400 text-slate-700 hover:bg-slate-100"
                  data-testid={`${testIdPrefix}-print-${i}`}>Print</button>
                {!readOnly && (
                  <button type="button"
                    onClick={() => onDelete?.(i)}
                    className="text-[11px] uppercase tracking-widest px-2 py-1 border border-red-500 text-red-600 hover:bg-red-50"
                    data-testid={`${testIdPrefix}-del-${i}`}>Delete</button>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
