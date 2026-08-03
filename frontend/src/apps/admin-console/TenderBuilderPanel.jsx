import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { tenderTemplateApi, formatApiError } from "@/lib/api";

/**
 * TenderBuilderPanel — Section-by-section tender/RFP/RFQ composer.
 *
 * Left column: master library + user drafts. Right column: editor —
 * header meta form + one textarea per section (Sections, Annexures, Forms).
 * Uses only textareas (no external rich-text lib) — future upgrade can swap
 * to react-quill or tiptap without touching the data model.
 */
const KIND_LABEL = { section: "Section", annexure: "Annexure", form: "Form" };
const KIND_TONE = {
  section: "bg-brand-navy/5 border-brand-navy/20 text-brand-navy",
  annexure: "bg-amber-50 border-amber-200 text-amber-900",
  form: "bg-emerald-50 border-emerald-200 text-emerald-900",
};

export default function TenderBuilderPanel() {
  const [list, setList] = useState([]);
  const [selectedId, setSelectedId] = useState(null);
  const [doc, setDoc] = useState(null);
  const [kind, setKind] = useState("tender");
  const [busy, setBusy] = useState(false);
  const [dirty, setDirty] = useState(false);

  const load = useCallback(async () => {
    try { setList(await tenderTemplateApi.list()); }
    catch (e) { toast.error(formatApiError(e)); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openTemplate = async (id) => {
    setSelectedId(id);
    setDirty(false);
    try { setDoc(await tenderTemplateApi.get(id)); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const cloneMaster = async (master) => {
    setBusy(true);
    try {
      const payload = {
        name: `${master.name} — draft ${new Date().toISOString().slice(0, 10)}`,
        kind, industry: master.industry,
        header: { ...(master.header || {}) },
        sections: (master.sections || []).map((s) => ({ ...s })),
      };
      const created = await tenderTemplateApi.create(payload);
      toast.success("Draft created");
      await load();
      await openTemplate(created.id);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const patchSection = (idx, patch) => {
    setDoc((prev) => {
      const sections = [...(prev.sections || [])];
      sections[idx] = { ...sections[idx], ...patch };
      return { ...prev, sections };
    });
    setDirty(true);
  };

  const addBlank = (kindCode) => {
    setDoc((prev) => {
      const sections = [...(prev.sections || [])];
      const nextOrder = sections.length ? Math.max(...sections.map((s) => s.order || 0)) + 10 : 10;
      const code = `${kindCode}-${sections.length + 1}`;
      sections.push({ code, kind: kindCode, title: `New ${KIND_LABEL[kindCode]}`,
                       hint: "", body: "", order: nextOrder });
      return { ...prev, sections };
    });
    setDirty(true);
  };

  const removeSection = (idx) => {
    if (!confirm("Remove this section?")) return;
    setDoc((prev) => {
      const sections = [...(prev.sections || [])];
      sections.splice(idx, 1);
      return { ...prev, sections };
    });
    setDirty(true);
  };

  const move = (idx, delta) => {
    setDoc((prev) => {
      const sections = [...(prev.sections || [])];
      const target = idx + delta;
      if (target < 0 || target >= sections.length) return prev;
      [sections[idx], sections[target]] = [sections[target], sections[idx]];
      sections.forEach((s, i) => { s.order = (i + 1) * 10; });
      return { ...prev, sections };
    });
    setDirty(true);
  };

  const save = async () => {
    if (!doc) return;
    setBusy(true);
    try {
      const payload = {
        name: doc.name, kind: doc.kind || "tender",
        industry: doc.industry, header: doc.header || {},
        sections: doc.sections || [],
      };
      const updated = await tenderTemplateApi.update(doc.id, payload);
      toast.success("Saved");
      setDoc(updated);
      setDirty(false);
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const removeDraft = async () => {
    if (!doc || doc.is_master) return;
    if (!confirm("Delete this draft?")) return;
    try {
      await tenderTemplateApi.remove(doc.id);
      toast.success("Deleted");
      setDoc(null); setSelectedId(null);
      await load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const masters = list.filter((x) => x.is_master);
  const drafts = list.filter((x) => !x.is_master);

  return (
    <div data-testid="tender-builder-panel" className="grid gap-6 lg:grid-cols-[300px_1fr]">
      <aside className="space-y-4">
        <div className="border border-brand-navy/10 bg-white">
          <div className="pmc-label p-3 border-b border-brand-navy/10">Kind</div>
          <div className="p-3 flex gap-2 flex-wrap">
            {["tender", "rfp", "rfq"].map((k) => (
              <button key={k} onClick={() => setKind(k)}
                data-testid={`tb-kind-${k}`}
                className={"px-3 py-1.5 text-[11px] uppercase tracking-widest border " +
                  (kind === k ? "bg-brand-navy text-white border-brand-navy" : "border-brand-navy/20 text-brand-navy")}>
                {k.toUpperCase()}
              </button>
            ))}
          </div>
        </div>

        <div className="border border-brand-navy/10 bg-white">
          <div className="pmc-label p-3 border-b border-brand-navy/10 flex justify-between items-center">
            <span>Master library</span>
            <span className="text-brand-navy/40 normal-case tracking-normal">{masters.length}</span>
          </div>
          <div className="max-h-64 overflow-y-auto">
            {masters.map((m) => (
              <div key={m.id} className="border-b border-brand-navy/10 p-3"
                   data-testid={`tb-master-${m.id}`}>
                <div className="text-sm font-semibold text-brand-navy leading-tight">{m.name}</div>
                <div className="text-xs text-brand-navy/50 mt-1">
                  {(m.sections || []).length} sections · {m.industry || "—"}
                </div>
                <button onClick={() => cloneMaster(m)} disabled={busy}
                  data-testid={`tb-clone-${m.id}`}
                  className="mt-2 w-full px-3 py-1.5 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
                  Clone as draft
                </button>
              </div>
            ))}
            {masters.length === 0 && <div className="p-6 text-sm text-brand-navy/50">No master templates.</div>}
          </div>
        </div>

        <div className="border border-brand-navy/10 bg-white">
          <div className="pmc-label p-3 border-b border-brand-navy/10 flex justify-between items-center">
            <span>Your drafts</span>
            <span className="text-brand-navy/40 normal-case tracking-normal">{drafts.length}</span>
          </div>
          <div className="max-h-96 overflow-y-auto">
            {drafts.map((d) => (
              <button key={d.id} onClick={() => openTemplate(d.id)}
                data-testid={`tb-draft-${d.id}`}
                className={"w-full text-left border-b border-brand-navy/10 p-3 hover:bg-brand-navy/5 " +
                  (selectedId === d.id ? "bg-brand-navy/10" : "")}>
                <div className="text-sm font-semibold text-brand-navy leading-tight truncate">{d.name}</div>
                <div className="text-xs text-brand-navy/50 mt-1">
                  {(d.sections || []).length} sections · {d.kind?.toUpperCase()}
                </div>
              </button>
            ))}
            {drafts.length === 0 && <div className="p-6 text-sm text-brand-navy/50">Clone a master to start.</div>}
          </div>
        </div>
      </aside>

      <section>
        {!doc ? (
          <div className="border border-dashed border-brand-navy/20 bg-white p-16 text-center text-brand-navy/50">
            Pick a draft from the left, or clone a master template to start composing.
          </div>
        ) : (
          <div className="space-y-6">
            {/* Header */}
            <div className="border border-brand-navy/10 bg-white p-5">
              <div className="flex flex-wrap items-baseline justify-between gap-3">
                <div className="flex-1 min-w-[240px]">
                  <div className="pmc-label">Tender name</div>
                  <input value={doc.name || ""}
                    onChange={(e) => { setDoc({ ...doc, name: e.target.value }); setDirty(true); }}
                    data-testid="tb-name"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20 text-lg font-serif text-brand-navy" />
                </div>
                <div className="flex gap-2">
                  <button onClick={save} disabled={busy || !dirty}
                    data-testid="tb-save"
                    className="px-5 py-2 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
                    {busy ? "Saving…" : dirty ? "Save changes" : "Saved"}
                  </button>
                  {!doc.is_master && (
                    <button onClick={removeDraft} data-testid="tb-delete"
                      className="px-4 py-2 text-[12px] uppercase tracking-widest border border-red-500 text-red-600 hover:bg-red-50">
                      Delete
                    </button>
                  )}
                </div>
              </div>

              <div className="mt-4 grid gap-3 md:grid-cols-3 text-sm">
                <label className="text-sm">
                  <span className="pmc-label">Work title</span>
                  <input value={doc.header?.work_title || ""}
                    onChange={(e) => { setDoc({ ...doc, header: { ...doc.header, work_title: e.target.value } }); setDirty(true); }}
                    data-testid="tb-work-title"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
                </label>
                <label className="text-sm">
                  <span className="pmc-label">Budget</span>
                  <input type="number" value={doc.header?.budget_amount || ""}
                    onChange={(e) => { setDoc({ ...doc, header: { ...doc.header, budget_amount: Number(e.target.value) } }); setDirty(true); }}
                    data-testid="tb-budget"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
                </label>
                <label className="text-sm">
                  <span className="pmc-label">Currency</span>
                  <select value={doc.header?.budget_currency || "INR"}
                    onChange={(e) => { setDoc({ ...doc, header: { ...doc.header, budget_currency: e.target.value } }); setDirty(true); }}
                    data-testid="tb-currency"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                    {["INR", "USD", "EUR", "KZT", "GBP", "AED"].map((c) => <option key={c}>{c}</option>)}
                  </select>
                </label>
                <label className="text-sm">
                  <span className="pmc-label">Period (days)</span>
                  <input type="number" value={doc.header?.period_days || ""}
                    onChange={(e) => { setDoc({ ...doc, header: { ...doc.header, period_days: Number(e.target.value) } }); setDirty(true); }}
                    data-testid="tb-period"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
                </label>
                <label className="text-sm md:col-span-2">
                  <span className="pmc-label">Evaluation method</span>
                  <input value={doc.header?.evaluation_method || ""}
                    onChange={(e) => { setDoc({ ...doc, header: { ...doc.header, evaluation_method: e.target.value } }); setDirty(true); }}
                    data-testid="tb-eval-method"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
                </label>
                <label className="text-sm md:col-span-3">
                  <span className="pmc-label">Eligibility</span>
                  <textarea rows={2} value={doc.header?.eligibility || ""}
                    onChange={(e) => { setDoc({ ...doc, header: { ...doc.header, eligibility: e.target.value } }); setDirty(true); }}
                    data-testid="tb-eligibility"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
                </label>
              </div>
            </div>

            {/* Sections */}
            <div className="space-y-4">
              {(doc.sections || []).sort((a, b) => (a.order || 0) - (b.order || 0)).map((s, i) => (
                <article key={`${s.code}-${i}`} className={`border p-5 ${KIND_TONE[s.kind] || KIND_TONE.section}`}
                         data-testid={`tb-section-${s.code}`}>
                  <div className="flex items-baseline justify-between gap-3 flex-wrap">
                    <div className="flex-1 min-w-[200px]">
                      <div className="text-[10px] uppercase tracking-widest opacity-60">{KIND_LABEL[s.kind] || s.kind}</div>
                      <input value={s.title}
                        onChange={(e) => patchSection(i, { title: e.target.value })}
                        data-testid={`tb-section-title-${s.code}`}
                        className="mt-1 w-full px-3 py-2 border border-current/20 bg-white text-brand-navy font-serif text-lg" />
                    </div>
                    <div className="flex gap-1">
                      <button onClick={() => move(i, -1)} data-testid={`tb-up-${s.code}`}
                        className="px-2 py-1 text-xs border border-current/30 bg-white hover:bg-brand-pale">↑</button>
                      <button onClick={() => move(i, +1)} data-testid={`tb-down-${s.code}`}
                        className="px-2 py-1 text-xs border border-current/30 bg-white hover:bg-brand-pale">↓</button>
                      <button onClick={() => removeSection(i)} data-testid={`tb-del-${s.code}`}
                        className="px-2 py-1 text-xs border border-red-500 text-red-600 bg-white hover:bg-red-50">×</button>
                    </div>
                  </div>
                  {s.hint && (
                    <div className="mt-2 text-xs opacity-70 italic">
                      {s.hint}
                    </div>
                  )}
                  <textarea value={s.body || ""}
                    onChange={(e) => patchSection(i, { body: e.target.value })}
                    data-testid={`tb-section-body-${s.code}`}
                    placeholder={s.hint || `Write the ${KIND_LABEL[s.kind]?.toLowerCase() || "section"} content here…`}
                    rows={8}
                    className="mt-3 w-full px-3 py-2 border border-current/20 bg-white text-brand-navy leading-relaxed text-sm resize-y" />
                  <div className="mt-2 text-[11px] opacity-60">
                    Code: <code className="font-mono">{s.code}</code>
                    {(s.body || "").length > 0 && (
                      <span className="ml-3">{(s.body || "").length} chars</span>
                    )}
                  </div>
                </article>
              ))}
            </div>

            {/* Add row */}
            <div className="border border-dashed border-brand-navy/30 bg-white p-4 flex flex-wrap gap-2 justify-center">
              <span className="text-sm text-brand-navy/60 mr-2 self-center">Add a new:</span>
              {["section", "annexure", "form"].map((k) => (
                <button key={k} onClick={() => addBlank(k)}
                  data-testid={`tb-add-${k}`}
                  className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
                  + {KIND_LABEL[k]}
                </button>
              ))}
            </div>
          </div>
        )}
      </section>
    </div>
  );
}
