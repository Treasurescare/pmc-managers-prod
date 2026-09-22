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
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [previews, setPreviews] = useState([]); // per-file [{file, preview, masterId, status, error}]
  const [resolvedKeys, setResolvedKeys] = useState({});

  if (!open) return null;

  const pickClosestMaster = (industry) => {
    if (!masters?.length) return null;
    const norm = (s) => (s || "").toLowerCase();
    // Prefer masters whose industry substring matches, else first.
    const match = masters.find((m) => industry && norm(m.industry).includes(norm(industry)));
    return match || masters[0];
  };

  const analyze = async () => {
    if (!files.length) return toast.error("Upload up to 3 DPRs (PDF/DOCX/TXT) first");
    if (files.length > 3) return toast.error("Max 3 DPRs per batch");
    setBusy(true);
    setPreviews(files.map((f) => ({ file: f, status: "pending" })));
    // Analyze in parallel, cap at 3 concurrent
    const results = await Promise.all(files.map(async (f) => {
      try {
        const r = await tenderProApi.analyzeDpr(f, kind);
        return { file: f, preview: r,
                  masterId: (pickClosestMaster(r?.header?.product_category || r?.header?.industry))?.id || masters[0]?.id || "",
                  status: "ready" };
      } catch (e) {
        return { file: f, status: "error", error: e?.response?.data?.detail || e.message || "Analyze failed" };
      }
    }));
    setPreviews(results);
    setResolvedKeys({});
    const ok = results.filter((r) => r.status === "ready").length;
    if (ok) toast.success(`Analyzed ${ok}/${files.length} DPR(s)`);
    if (ok < files.length) toast.error(`${files.length - ok} DPR(s) failed`);
    setBusy(false);
  };

  const cloneAndApply = async () => {
    const ready = previews.filter((p) => p.status === "ready" && p.masterId);
    if (!ready.length) return toast.error("Analyze the DPRs and pick a master for each first");
    setBusy(true);
    const created = [];
    const errors = [];
    // Sequential Mongo writes to avoid version-index races, but each call
    // is only ~100ms so the batch still finishes fast.
    for (const p of ready) {
      const master = masters.find((m) => m.id === p.masterId);
      if (!master) continue;
      try {
        const cleanSections = (master.sections || []).map((s) => ({
          code: s.code, kind: s.kind || "section", title: s.title,
          hint: s.hint ?? null,
          body: p.preview.section_bodies?.[s.code] || s.body || "",
          order: typeof s.order === "number" ? s.order : null,
        }));
        const doc = await tenderTemplateApi.create({
          name: `${p.preview.header?.work_title || p.file.name || "AI Draft"} — ${new Date().toISOString().slice(0, 10)}`,
          kind, industry: master.industry,
          header: { ...(master.header || {}), ...(p.preview.header || {}),
                      dpr_warnings: p.preview.warnings || [] },
          sections: cleanSections,
        });
        created.push(doc);
      } catch (e) {
        errors.push(`${p.file.name}: ${e?.response?.data?.detail || e.message}`);
      }
    }
    setBusy(false);
    if (created.length) {
      toast.success(`Created ${created.length} AI draft(s)`);
      onCloned?.(created[0]);
      onClose();
    }
    if (errors.length) toast.error(`Failed: ${errors.join(" · ")}`);
  };

  const patchPreview = (idx, patch) => {
    setPreviews((prev) => prev.map((p, i) => (i === idx ? { ...p, ...patch } : p)));
  };

  const cloneAndApply2 = null;  // legacy removed

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
            <span className="pmc-label">Upload up to 3 DPRs (PDF, DOCX or TXT · max 15 MB each)</span>
            <input type="file" accept=".pdf,.docx,.txt" multiple
                   onChange={(e) => setFiles(Array.from(e.target.files || []).slice(0, 3))}
                   data-testid="dpr-file"
                   className="mt-2 block w-full text-sm" />
            {files.length > 0 && (
              <div className="mt-2 text-[11px] text-brand-navy/60">
                {files.length} file(s) selected: {files.map((f) => f.name).join(", ")}
              </div>
            )}
          </label>

          <button onClick={analyze} disabled={busy || !files.length}
                  data-testid="dpr-analyze"
                  className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
            {busy ? "Analysing…" : `Analyze ${files.length || ""} DPR${files.length === 1 ? "" : "s"} with AI`}
          </button>

          {previews.map((p, idx) => (
            <div key={idx} className={"border p-3 text-sm " +
                                        (p.status === "error" ? "border-red-300 bg-red-50" : "border-emerald-200 bg-emerald-50")}
                 data-testid={`dpr-preview-${idx}`}>
              <div className="pmc-label mb-2 flex items-baseline justify-between">
                <span>{p.file.name}</span>
                <span className="text-[10px] tracking-normal normal-case">
                  {p.status === "error" ? `✕ ${p.error}` :
                    p.status === "pending" ? "Waiting…" :
                    `${Object.keys(p.preview?.section_bodies || {}).length} drafts · ${p.preview?.warnings?.length || 0} warnings`}
                </span>
              </div>
              {p.status === "ready" && (
                <>
                  <div className="grid gap-1 text-brand-navy text-xs mb-2">
                    {Object.entries(p.preview.header || {}).slice(0, 4).map(([k, v]) => (
                      <div key={k}><span className="font-mono text-brand-navy/60">{k}:</span> {String(v).slice(0, 70)}</div>
                    ))}
                  </div>
                  <label className="block text-xs">
                    <span className="pmc-label">Base master template</span>
                    <select value={p.masterId} onChange={(e) => patchPreview(idx, { masterId: e.target.value })}
                            data-testid={`dpr-master-${idx}`}
                            className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                      {(masters || []).map((m) => (
                        <option key={m.id} value={m.id}>{m.name}</option>
                      ))}
                    </select>
                  </label>
                  {(p.preview.warnings || []).length > 0 && (
                    <ul className="mt-2 text-[11px] text-amber-800 space-y-0.5">
                      {p.preview.warnings.slice(0, 3).map((w, i) => (
                        <li key={i}>⚠ {w}</li>
                      ))}
                      {p.preview.warnings.length > 3 && <li className="text-brand-navy/50">…+{p.preview.warnings.length - 3} more</li>}
                    </ul>
                  )}
                </>
              )}
            </div>
          ))}

          <div className="flex justify-end gap-2 pt-2">
            <button onClick={onClose} className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
              Cancel
            </button>
            <button onClick={cloneAndApply} disabled={busy || !previews.some((p) => p.status === "ready")}
                    data-testid="dpr-clone-apply"
                    className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-emerald-600 text-white hover:bg-emerald-700 disabled:opacity-40">
              {busy ? "Creating…" :
                `Create ${previews.filter((p) => p.status === "ready").length || ""} AI-drafted ${kind.toUpperCase()}${previews.filter((p) => p.status === "ready").length === 1 ? "" : "s"}`}
            </button>
          </div>
        </div>
      </div>
    </div>
  );
}
