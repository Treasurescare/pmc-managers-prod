import { useState } from "react";
import { toast } from "sonner";
import { tenderProApi, tenderTemplateApi, showApiError } from "@/lib/api";

/**
 * v45 · Phase C — DPR upload modal.
 * Admin uploads a project brief / DPR; the LLM extracts a header prefill
 * and section-body drafts; we clone the closest master and land the admin
 * on a ready-to-review draft.
 */
export default function DprGenerateModal({ open, onClose, kind, masters, onCloned }) {
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const [preview, setPreview] = useState(null);
  const [masterId, setMasterId] = useState("");

  if (!open) return null;

  const analyze = async () => {
    if (!file) return toast.error("Upload a DPR (PDF/DOCX/TXT) first");
    setBusy(true);
    try {
      const r = await tenderProApi.analyzeDpr(file, kind);
      setPreview(r);
      if (masters?.length && !masterId) setMasterId(masters[0].id);
      toast.success(`Extracted ${Object.keys(r.section_bodies || {}).length} section drafts`);
    } catch (e) { showApiError(e); } finally { setBusy(false); }
  };

  const cloneAndApply = async () => {
    if (!preview || !masterId) return toast.error("Analyze the DPR and pick a master template first");
    const master = masters.find((m) => m.id === masterId);
    if (!master) return;
    setBusy(true);
    try {
      const cleanSections = (master.sections || []).map((s) => ({
        code: s.code, kind: s.kind || "section", title: s.title,
        hint: s.hint ?? null,
        body: preview.section_bodies?.[s.code] || s.body || "",
        order: typeof s.order === "number" ? s.order : null,
      }));
      const created = await tenderTemplateApi.create({
        name: `${preview.header?.work_title || file.name || "AI Draft"} — ${new Date().toISOString().slice(0, 10)}`,
        kind, industry: master.industry,
        header: { ...(master.header || {}), ...(preview.header || {}) },
        sections: cleanSections,
      });
      toast.success(`AI draft created · ${created.name}`);
      onCloned?.(created);
      onClose();
    } catch (e) { showApiError(e); } finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
         data-testid="dpr-modal">
      <div className="bg-white w-full max-w-2xl max-h-[90vh] overflow-y-auto p-6">
        <div className="flex justify-between items-baseline mb-4">
          <h2 className="font-display text-xl text-brand-navy">AI-generate {kind.toUpperCase()} from DPR</h2>
          <button onClick={onClose} className="text-brand-navy/50 hover:text-brand-navy">×</button>
        </div>

        <div className="space-y-4">
          <label className="block text-sm">
            <span className="pmc-label">Upload DPR (PDF, DOCX or TXT · max 15 MB)</span>
            <input type="file" accept=".pdf,.docx,.txt"
                   onChange={(e) => setFile(e.target.files?.[0] || null)}
                   data-testid="dpr-file"
                   className="mt-2 block w-full text-sm" />
          </label>

          <button onClick={analyze} disabled={busy || !file}
                  data-testid="dpr-analyze"
                  className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
            {busy ? "Analysing…" : "Analyze with AI"}
          </button>

          {preview && (
            <div className="border border-emerald-200 bg-emerald-50 p-3 text-sm">
              <div className="pmc-label text-emerald-900 mb-2">AI Extracted</div>
              <div className="grid gap-1 text-brand-navy">
                {Object.entries(preview.header || {}).slice(0, 6).map(([k, v]) => (
                  <div key={k}><span className="font-mono text-xs text-brand-navy/60">{k}:</span> {String(v).slice(0, 80)}</div>
                ))}
              </div>
              <div className="text-xs text-brand-navy/60 mt-2">
                {Object.keys(preview.section_bodies || {}).length} section drafts ready · {preview.warnings?.length || 0} warning(s)
              </div>
            </div>
          )}

          {preview && (
            <label className="block text-sm">
              <span className="pmc-label">Base master template</span>
              <select value={masterId} onChange={(e) => setMasterId(e.target.value)}
                      data-testid="dpr-master"
                      className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                {(masters || []).map((m) => (
                  <option key={m.id} value={m.id}>{m.name}</option>
                ))}
              </select>
            </label>
          )}

          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
              Cancel
            </button>
            <button onClick={cloneAndApply} disabled={!preview || busy}
                    data-testid="dpr-clone-apply"
                    className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40">
              Create AI-drafted {kind.toUpperCase()}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
