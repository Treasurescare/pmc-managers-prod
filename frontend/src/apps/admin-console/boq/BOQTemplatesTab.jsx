import { useEffect, useMemo, useRef, useState } from "react";
import { toast } from "sonner";
import { boqApi, mastersApi, formatApiError, showApiError} from "@/lib/api";
import UnspscPicker from "@/components/UnspscPicker";
import { InfoDot } from "@/components/InfoDot";
const EMPTY_LINE = {
  description: "", unit: "", quantity: 0, unit_rate: 0,
  unspsc_code: "", unspsc_title: "", remarks: "",
};

/**
 * BOQTemplatesTab — list, create, Excel import AND v52bs add/edit/delete of
 * line items inline (per the user manual: description, unit, quantity, rate,
 * UNSPSC pulled from the categories master).
 */
export default function BOQTemplatesTab({
  templates, showNewTmpl, setShowNewTmpl, tmplDraft, setTmplDraft,
  selectedTmpl, setSelectedTmpl, onReload,
}) {
  // v52bw — scroll the viewer into view the instant a template is opened,
  // so admins don't scroll past a long template list wondering if View
  // did anything.
  // v52cf — add a 1.2s amber ring flash so the jump is unmistakable even
  // when the viewer was already in the viewport (list was short).
  const viewerRef = useRef(null);
  const [flashOn, setFlashOn] = useState(false);
  useEffect(() => {
    if (selectedTmpl && viewerRef.current) {
      viewerRef.current.scrollIntoView({ behavior: "smooth", block: "start" });
      setFlashOn(true);
      const timer = setTimeout(() => setFlashOn(false), 1200);
      return () => clearTimeout(timer);
    }
  }, [selectedTmpl?.id]);
  const createTemplate = async () => {
    if (!tmplDraft.name) return toast.error("Name required");
    try {
      await boqApi.createTemplate({ ...tmplDraft, items: [] });
      toast.success("Template created");
      setShowNewTmpl(false);
      setTmplDraft({ name: "", notice_ref: "", currency: "USD",
                      unspsc_code: "", unspsc_title: "" });
      onReload();
    } catch (e) { showApiError(e); }
  };

  const importExcel = async (tmpl, file) => {
    try {
      const r = await boqApi.importExcel(tmpl.id, file);
      toast.success(`Imported ${r.items} items`);
      onReload();
      if (selectedTmpl?.id === tmpl.id) setSelectedTmpl(await boqApi.getTemplate(tmpl.id));
    } catch (e) { showApiError(e); }
  };

  const viewTemplate = async (tmpl) => setSelectedTmpl(await boqApi.getTemplate(tmpl.id));

  // v52bs — inline line-item editor state
  const [draftLine, setDraftLine] = useState(EMPTY_LINE);
  const [editingIdx, setEditingIdx] = useState(null);
  const items = useMemo(() => selectedTmpl?.items || [], [selectedTmpl]);

  const persistItems = async (nextItems) => {
    try {
      await boqApi.updateTemplate(selectedTmpl.id, { items: nextItems });
      const fresh = await boqApi.getTemplate(selectedTmpl.id);
      setSelectedTmpl(fresh);
      onReload();
    } catch (e) { showApiError(e); }
  };

  const addLine = async () => {
    if (!draftLine.description.trim()) return toast.error("Description is required");
    if (Number(draftLine.quantity) < 0 || Number(draftLine.unit_rate) < 0)
      return toast.error("Quantity and unit rate must be ≥ 0");
    const next = [...items, {
      ...draftLine,
      quantity: Number(draftLine.quantity) || 0,
      unit_rate: Number(draftLine.unit_rate) || 0,
    }];
    await persistItems(next);
    setDraftLine(EMPTY_LINE);
    toast.success("Line item added");
  };
  const saveEdit = async (i) => {
    const next = items.map((it, idx) => idx === i ? {
      ...draftLine,
      quantity: Number(draftLine.quantity) || 0,
      unit_rate: Number(draftLine.unit_rate) || 0,
    } : it);
    await persistItems(next);
    setEditingIdx(null); setDraftLine(EMPTY_LINE);
    toast.success("Line updated");
  };
  const removeLine = async (i) => {
    if (!window.confirm(`Delete line ${i + 1}: ${items[i].description}?`)) return;
    await persistItems(items.filter((_, idx) => idx !== i));
  };

  return (
    <>
      <div className="flex justify-between mb-4">
        <div className="text-sm text-brand-navy/70">{templates.length} BOQ templates</div>
        <button onClick={() => setShowNewTmpl(!showNewTmpl)} data-testid="boq-new-toggle"
          className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
          {showNewTmpl ? "Cancel" : "New BOQ Template"}
        </button>
      </div>
      {showNewTmpl && (
        <div className="bg-white border p-4 mb-4 grid gap-2 md:grid-cols-3" data-testid="boq-new-form">
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Template name<InfoDot tip="Internal name for the Bill-of-Quantities template. Free text." />
            <input placeholder="Template name" value={tmplDraft.name}
              onChange={(e) => setTmplDraft({ ...tmplDraft, name: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="boq-name" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Linked notice ref<InfoDot tip="Optional. Bind this BOQ to a specific tender so line-item bidding is enabled on the notice page." />
            <input placeholder="Linked notice ref (optional)" value={tmplDraft.notice_ref}
              onChange={(e) => setTmplDraft({ ...tmplDraft, notice_ref: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="boq-notice-ref" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Currency<InfoDot tip="ISO-4217 code applied to all Unit Rate columns imported from Excel." />
            <input placeholder="Currency" value={tmplDraft.currency}
              onChange={(e) => setTmplDraft({ ...tmplDraft, currency: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
          </label>
          <div className="md:col-span-3">
            <div className="text-[10px] uppercase tracking-widest text-brand-navy/60 mb-1">
              UNSPSC commodity family (optional)
            </div>
            <UnspscPicker
              value={tmplDraft.unspsc_code}
              title={tmplDraft.unspsc_title}
              onChange={({ code, title }) => setTmplDraft({
                ...tmplDraft, unspsc_code: code, unspsc_title: title,
              })}
              testidPrefix="boq-unspsc"
            />
          </div>
          <button onClick={createTemplate} data-testid="boq-create"
            className="md:col-span-3 px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white">
            Create
          </button>
        </div>
      )}
      <div className="bg-white border">
        {templates.map((t) => (
          <div key={t.id} className="border-b p-3 flex justify-between items-center"
            data-testid={`boq-row-${t.id}`}>
            <div>
              <div className="font-semibold text-sm">{t.name}</div>
              <div className="text-xs text-slate-500">
                {t.notice_ref || "—"} · {(t.items || []).length} items · {t.currency}
                {t.unspsc_code && (
                  <span className="ml-2 font-mono">· UNSPSC {t.unspsc_code}</span>
                )}
              </div>
            </div>
            <div className="flex items-center gap-2">
              <label className="px-3 py-1.5 text-xs border cursor-pointer">
                Import Excel
                <input type="file" accept=".xlsx,.xls" hidden
                  onChange={(e) => e.target.files?.[0] && importExcel(t, e.target.files[0])}
                  data-testid={`boq-import-${t.id}`} />
              </label>
              <button onClick={() => boqApi.exportXlsx(t.id, t.name).catch(showApiError)}
                      data-testid={`boq-export-xlsx-${t.id}`}
                      className="text-xs border px-3 py-1.5">Export Excel</button>
              <button onClick={() => boqApi.exportPdf(t.id, t.name).catch(showApiError)}
                      data-testid={`boq-export-pdf-${t.id}`}
                      className="text-xs border px-3 py-1.5">Export PDF</button>
              <button onClick={() => viewTemplate(t)} data-testid={`boq-view-${t.id}`}
                className="text-xs border px-3 py-1.5">View</button>
            </div>
          </div>
        ))}
      </div>
      {selectedTmpl && (
        <div ref={viewerRef}
             className={"mt-4 bg-white border p-4 transition-shadow duration-500 " +
               (flashOn ? "ring-4 ring-amber-400 shadow-lg" : "")}
             data-testid="boq-viewer">
          {flashOn && (
            <div className="text-[11px] uppercase tracking-widest text-amber-700 font-semibold mb-2"
                 data-testid="boq-viewer-flash">
              ↓ Viewing “{selectedTmpl.name}” — details below
            </div>
          )}
          <div className="flex items-baseline justify-between">
            <div className="font-serif text-lg">{selectedTmpl.name}</div>
            <div className="flex items-center gap-3">
              {selectedTmpl.unspsc_code && (
                <div className="text-[11px] font-mono text-brand-navy/60">
                  UNSPSC {selectedTmpl.unspsc_code} · {selectedTmpl.unspsc_title}
                </div>
              )}
              <button type="button" onClick={() => setSelectedTmpl(null)}
                      data-testid="boq-viewer-close"
                      className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy/70 hover:bg-brand-navy/5">
                Close
              </button>
            </div>
          </div>

          {/* v52bs — add / edit line item form */}
          <div className="bg-brand-pale/40 border border-brand-navy/15 p-3 mt-3"
               data-testid="boq-line-form">
            <div className="text-[11px] uppercase tracking-widest text-brand-navy/70 mb-2">
              {editingIdx !== null ? `Edit line ${editingIdx + 1}` : "Add line item"}
            </div>
            <div className="grid gap-2 md:grid-cols-6">
              <input placeholder="Description *" value={draftLine.description}
                     data-testid="boq-line-desc"
                     onChange={(e) => setDraftLine({ ...draftLine, description: e.target.value })}
                     className="md:col-span-2 px-2 py-1.5 border text-xs" />
              <input placeholder="Unit (nos, kg, m²)" value={draftLine.unit}
                     data-testid="boq-line-unit"
                     onChange={(e) => setDraftLine({ ...draftLine, unit: e.target.value })}
                     className="px-2 py-1.5 border text-xs" />
              <input type="number" min="0" step="any" placeholder="Qty" value={draftLine.quantity}
                     data-testid="boq-line-qty"
                     onChange={(e) => setDraftLine({ ...draftLine, quantity: e.target.value })}
                     className="px-2 py-1.5 border text-xs" />
              <input type="number" min="0" step="any" placeholder="Rate" value={draftLine.unit_rate}
                     data-testid="boq-line-rate"
                     onChange={(e) => setDraftLine({ ...draftLine, unit_rate: e.target.value })}
                     className="px-2 py-1.5 border text-xs" />
              <div className="text-xs text-brand-navy/70 flex items-center">
                = {((Number(draftLine.quantity)||0) * (Number(draftLine.unit_rate)||0)).toLocaleString()}
              </div>
            </div>
            <div className="mt-2 grid gap-2 md:grid-cols-2">
              <div>
                <div className="text-[10px] uppercase tracking-widest text-brand-navy/60 mb-1">UNSPSC commodity</div>
                <UnspscPicker value={draftLine.unspsc_code} title={draftLine.unspsc_title}
                              onChange={({ code, title }) => setDraftLine({
                                ...draftLine, unspsc_code: code, unspsc_title: title })}
                              testidPrefix="boq-line-unspsc" />
              </div>
              <div className="flex items-end justify-end gap-2">
                {editingIdx !== null && (
                  <button onClick={() => { setEditingIdx(null); setDraftLine(EMPTY_LINE); }}
                          data-testid="boq-line-cancel"
                          className="text-[11px] uppercase tracking-widest px-3 py-1.5 border border-brand-navy/20">
                    Cancel
                  </button>
                )}
                <button onClick={editingIdx !== null ? () => saveEdit(editingIdx) : addLine}
                        data-testid="boq-line-save"
                        className="text-[11px] uppercase tracking-widest px-4 py-1.5 bg-brand-navy text-white hover:bg-brand-navy-deep">
                  {editingIdx !== null ? "Save line" : "+ Add line item"}
                </button>
              </div>
            </div>
          </div>

          <table className="w-full text-xs mt-4" data-testid="boq-items-table">
            <thead className="text-slate-500">
              <tr><th className="text-left">Sl.</th><th className="text-left">Description</th>
                <th>Unit</th><th>Qty</th><th className="text-right">Unit Rate</th>
                <th className="text-right">Line Total</th><th>UNSPSC</th><th></th></tr>
            </thead>
            <tbody>
              {items.length === 0 && (
                <tr><td colSpan={8} className="py-6 text-center text-brand-navy/50"
                        data-testid="boq-items-empty">
                  No line items yet. Add rows above or import an Excel BOQ.
                </td></tr>
              )}
              {items.map((it, i) => (
                <tr key={`boq-item-${it.sl_no ?? i}`} className="border-t"
                    data-testid={`boq-item-${i}`}>
                  <td className="py-1">{i + 1}</td>
                  <td>{it.description}</td>
                  <td className="text-center">{it.unit || "—"}</td>
                  <td className="text-center">{it.quantity}</td>
                  <td className="text-right">{Number(it.unit_rate || 0).toLocaleString()}</td>
                  <td className="text-right">{(Number(it.quantity||0) * Number(it.unit_rate||0)).toLocaleString()}</td>
                  <td className="font-mono text-[10px]">{it.unspsc_code || "—"}</td>
                  <td className="text-right whitespace-nowrap">
                    <button onClick={() => { setEditingIdx(i); setDraftLine({ ...EMPTY_LINE, ...it }); }}
                            data-testid={`boq-item-edit-${i}`}
                            className="text-[10px] uppercase tracking-widest text-brand-navy hover:underline mr-2">
                      Edit
                    </button>
                    <button onClick={() => removeLine(i)}
                            data-testid={`boq-item-del-${i}`}
                            className="text-[10px] uppercase tracking-widest text-red-700 hover:underline">
                      Delete
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
