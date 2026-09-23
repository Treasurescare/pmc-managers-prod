import { useEffect, useState } from "react";
import { toast } from "sonner";
import { tenderProApi, tenderTemplateApi, publicApi, showApiError } from "@/lib/api";

/**
 * v45 · Phase C — DPR upload modal.
 * Admin uploads a project brief / DPR; the LLM extracts a header prefill
 * and section-body drafts; we clone the closest master and land the admin
 * on a ready-to-review draft.
 */
export default function DprGenerateModal({ open, onClose, kind, masters, onCloned }) {
  const [files, setFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [previews, setPreviews] = useState([]);
  const [resolvedKeys, setResolvedKeys] = useState({});
  const [batchMasterId, setBatchMasterId] = useState("");
  // v45f · Country-first: pick country → masters filter to that country
  const [country, setCountry] = useState("");
  // v46d · Country dropdown now sources from the platform-wide country
  // master (publicApi.countries) — not from existing templates — so an
  // empty template library still lets admin scope by country.
  const [countryList, setCountryList] = useState([]);
  useEffect(() => {
    if (!open) return;
    publicApi.countries().then((rows) => setCountryList(rows || [])).catch(() => setCountryList([]));
  }, [open]);
  // v46e — if the picked country has no masters, allow the admin to either
  // (a) borrow a master from any other country (dropdown shows country
  //     code prefix), or
  // (b) proceed WITHOUT a master — the AI drafts a fresh template from the
  //     DPR itself and we save it as a new master under the picked country.
  const [crossCountry, setCrossCountry] = useState(false);
  const [noMasterMode, setNoMasterMode] = useState(false);
  const countryMasters = country
    ? (masters || []).filter((m) => (m.country || m.header?.country) === country)
    : (masters || []);
  const filteredMasters = (country && crossCountry) ? (masters || []) : countryMasters;
  const countryOf = (m) => (m.country || m.header?.country || "??").toUpperCase();

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
    if (!batchMasterId && !noMasterMode) return toast.error("Pick a master, borrow one from another country, or tick 'Build a new master from this DPR'");
    setBusy(true);
    setPreviews(files.map((f) => ({ file: f, status: "pending", masterId: batchMasterId })));
    const results = await Promise.all(files.map(async (f) => {
      try {
        const r = await tenderProApi.analyzeDpr(f, kind, batchMasterId || null);
        return { file: f, preview: r, masterId: batchMasterId || null, status: "ready",
                 name: r?.header?.work_title || f.name.replace(/\.[^.]+$/, "") || "AI Draft" };
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
    const ready = previews.filter((p) => p.status === "ready");
    if (!ready.length) return toast.error("Analyze the DPRs first");
    setBusy(true);
    const created = [];
    const errors = [];
    for (const p of ready) {
      const master = p.masterId ? masters.find((m) => m.id === p.masterId) : null;
      try {
        // v46e — when no master exists (or the admin chose "Build new
        // master from this DPR"), skeleton the template from the AI
        // extraction: every section the LLM drafted becomes a section
        // in the new master, with human-readable titles derived from
        // the code and the country tagged so it feeds the picker next
        // time.
        const secBodies = p.preview.section_bodies || {};
        const cleanSections = master
          ? (master.sections || []).map((s) => ({
              code: s.code, kind: s.kind || "section", title: s.title,
              hint: s.hint ?? null,
              body: secBodies[s.code] || s.body || "",
              order: typeof s.order === "number" ? s.order : null,
            }))
          : Object.keys(secBodies).map((code, i) => ({
              code, kind: "section",
              title: code.replace(/[_-]/g, " ").replace(/\b\w/g, (c) => c.toUpperCase()),
              hint: null,
              body: secBodies[code] || "",
              order: i * 10,
            }));

        const mergedHeader = { ...((master && master.header) || {}), ...(p.preview.header || {}) };
        // Stamp country/industry so this new template is discoverable next run
        if (!mergedHeader.country && country) mergedHeader.country = country;
        const industry = master?.industry || p.preview.header?.industry || "general";

        const tVal = Number(mergedHeader.tender_value || mergedHeader.budget_amount || 0);
        if (tVal > 0 && !(Number(mergedHeader.emd_amount) > 0)) {
          try {
            const ems = await tenderProApi.listEmdMasters(mergedHeader.country || undefined, "emd");
            const def = (ems || []).find((m) => m.is_default) || (ems || [])[0];
            if (def) {
              const c = await tenderProApi.computeEmd(def.id, tVal);
              mergedHeader.emd_amount = c.amount;
              mergedHeader.emd_type = c.type;
              if (c.percentage) mergedHeader.emd_percentage = c.percentage;
              if (!mergedHeader.budget_currency && c.currency) mergedHeader.budget_currency = c.currency;
              toast.success(`EMD auto-computed · ${c.amount.toLocaleString()} ${c.currency} (${def.name})`);
            }
          } catch { /* no master configured — leave EMD for manual entry */ }
        }
        const chosenName = (p.name || "").trim() ||
          `${p.preview.header?.work_title || p.file.name || "AI Draft"} — ${new Date().toISOString().slice(0, 10)}`;
        const doc = await tenderTemplateApi.create({
          name: chosenName,
          kind, industry,
          country: mergedHeader.country || country || undefined,
          header: { ...mergedHeader, dpr_warnings: p.preview.warnings || [] },
          sections: cleanSections,
        });
        created.push(doc);
        // v46f — "Build a new master" must ACTUALLY persist a master:
        // POST /tender-templates always creates a draft (is_master=false,
        // top-level country dropped), so promote the fresh draft through
        // the dedicated save-as-master endpoint.
        if (noMasterMode && !p.masterId) {
          const mCountry = (mergedHeader.country || country || "").toUpperCase();
          if (mCountry) {
            try {
              await tenderProApi.saveAsMaster(doc.id, {
                country: mCountry, industry,
                name: `${chosenName} · ${mCountry} master`,
              });
            } catch (e) {
              errors.push(`${p.file.name}: draft created, but saving as master failed — ${e?.response?.data?.detail || e.message}`);
            }
          }
        }
      } catch (e) {
        errors.push(`${p.file.name}: ${e?.response?.data?.detail || e.message}`);
      }
    }
    setBusy(false);
    if (created.length) {
      const suffix = noMasterMode ? " (saved as new master)" : "";
      toast.success(`Created ${created.length} AI draft${created.length === 1 ? "" : "s"}${suffix}`);
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
            <span className="pmc-label">1 · Country (drives regulations + templates)</span>
            <select value={country} onChange={(e) => { setCountry(e.target.value); setBatchMasterId(""); }}
                    data-testid="dpr-country"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
              <option value="">— All countries —</option>
              {countryList.map((c) => <option key={c.code} value={c.code}>{c.name} ({c.code})</option>)}
            </select>
          </label>

          <label className="block text-sm">
            <span className="pmc-label">2 · Master template (AI fills its exact sections)</span>
            <select value={batchMasterId}
                    onChange={(e) => { setBatchMasterId(e.target.value); if (e.target.value) setNoMasterMode(false); }}
                    disabled={noMasterMode}
                    data-testid="dpr-batch-master"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white disabled:bg-slate-100 disabled:text-slate-400">
              <option value="">— Select master —</option>
              {filteredMasters.map((m) => (
                <option key={m.id} value={m.id}>
                  {crossCountry ? `[${countryOf(m)}] ` : ""}{m.name}
                </option>
              ))}
            </select>
            {country && countryMasters.length === 0 && (
              <div className="mt-2 border border-amber-300 bg-amber-50 p-3 text-[12px] text-amber-900 space-y-2"
                   data-testid="dpr-no-master-help">
                <div><b>No master templates saved for {country} yet.</b> Choose an option:</div>
                <label className="flex items-start gap-2 cursor-pointer">
                  <input type="checkbox" checked={crossCountry}
                         onChange={(e) => { setCrossCountry(e.target.checked); if (!e.target.checked) setBatchMasterId(""); }}
                         data-testid="dpr-cross-country"
                         className="mt-0.5" />
                  <span>Borrow a master from another country ({(masters || []).length} available across the platform — country code shown in the dropdown above).</span>
                </label>
                <label className="flex items-start gap-2 cursor-pointer">
                  <input type="checkbox" checked={noMasterMode}
                         onChange={(e) => { setNoMasterMode(e.target.checked); if (e.target.checked) setBatchMasterId(""); }}
                         data-testid="dpr-no-master-mode"
                         className="mt-0.5" />
                  <span><b>Build a brand-new master from this DPR.</b> The AI drafts the structure and sections from your uploaded file and saves it as a new master under {country} for future re-use.</span>
                </label>
              </div>
            )}
          </label>

          <label className="block text-sm">
            <span className="pmc-label">3 · Upload up to 3 DPRs (PDF / DOCX / TXT · max 15 MB each)</span>
            <input type="file" accept=".pdf,.docx,.txt" multiple
                   onChange={(e) => setFiles(Array.from(e.target.files || []).slice(0, 3))}
                   data-testid="dpr-file"
                   className="mt-2 block w-full text-sm" />
            {files.length > 0 && (
              <div className="mt-2 text-[11px] text-brand-navy/60">
                {files.length} file(s): {files.map((f) => f.name).join(", ")}
              </div>
            )}
          </label>

          <button onClick={analyze} disabled={busy || !files.length || (!batchMasterId && !noMasterMode)}
                  data-testid="dpr-analyze"
                  className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
            {busy ? "Analysing…" : `4 · Analyze ${files.length || ""} DPR${files.length === 1 ? "" : "s"} with AI`}
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
                  <label className="block text-xs mb-2">
                    <span className="pmc-label">Tender name (editable — this is what you search for in the left column)</span>
                    <input value={p.name || ""}
                           onChange={(e) => patchPreview(idx, { name: e.target.value })}
                           data-testid={`dpr-name-${idx}`}
                           placeholder="Name this tender draft"
                           className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white" />
                  </label>
                  <label className="block text-xs">
                    <span className="pmc-label">Base master template</span>
                    <select value={p.masterId || ""} onChange={(e) => patchPreview(idx, { masterId: e.target.value })}
                            data-testid={`dpr-master-${idx}`}
                            className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                      <option value="">— New master from this DPR —</option>
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
