import { toast } from "sonner";
import { boqApi, formatApiError } from "@/lib/api";
import UnspscPicker from "@/components/UnspscPicker";

/**
 * BOQTemplatesTab — BOQ template list, create-new form, Excel import per
 * template, and inline viewer. Templates now carry an optional UNSPSC
 * commodity tag so the whole BOQ can be reported against a standard code.
 */
export default function BOQTemplatesTab({
  templates, showNewTmpl, setShowNewTmpl, tmplDraft, setTmplDraft,
  selectedTmpl, setSelectedTmpl, onReload,
}) {
  const createTemplate = async () => {
    if (!tmplDraft.name) return toast.error("Name required");
    try {
      await boqApi.createTemplate({ ...tmplDraft, items: [] });
      toast.success("Template created");
      setShowNewTmpl(false);
      setTmplDraft({ name: "", notice_ref: "", currency: "USD",
                      unspsc_code: "", unspsc_title: "" });
      onReload();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const importExcel = async (tmpl, file) => {
    try {
      const r = await boqApi.importExcel(tmpl.id, file);
      toast.success(`Imported ${r.items} items`);
      onReload();
      if (selectedTmpl?.id === tmpl.id) setSelectedTmpl(await boqApi.getTemplate(tmpl.id));
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const viewTemplate = async (tmpl) => setSelectedTmpl(await boqApi.getTemplate(tmpl.id));

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
          <input placeholder="Template name" value={tmplDraft.name}
            onChange={(e) => setTmplDraft({ ...tmplDraft, name: e.target.value })}
            className="px-3 py-2 border" data-testid="boq-name" />
          <input placeholder="Linked notice ref (optional)" value={tmplDraft.notice_ref}
            onChange={(e) => setTmplDraft({ ...tmplDraft, notice_ref: e.target.value })}
            className="px-3 py-2 border" data-testid="boq-notice-ref" />
          <input placeholder="Currency" value={tmplDraft.currency}
            onChange={(e) => setTmplDraft({ ...tmplDraft, currency: e.target.value })}
            className="px-3 py-2 border" />
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
              <button onClick={() => viewTemplate(t)} data-testid={`boq-view-${t.id}`}
                className="text-xs border px-3 py-1.5">View</button>
            </div>
          </div>
        ))}
      </div>
      {selectedTmpl && (
        <div className="mt-4 bg-white border p-4" data-testid="boq-viewer">
          <div className="flex items-baseline justify-between">
            <div className="font-serif text-lg">{selectedTmpl.name}</div>
            {selectedTmpl.unspsc_code && (
              <div className="text-[11px] font-mono text-brand-navy/60">
                UNSPSC {selectedTmpl.unspsc_code} · {selectedTmpl.unspsc_title}
              </div>
            )}
          </div>
          <table className="w-full text-xs mt-2">
            <thead className="text-slate-500">
              <tr><th className="text-left">Sl.</th><th className="text-left">Description</th>
                <th>Unit</th><th>Qty</th><th className="text-right">Unit Rate</th></tr>
            </thead>
            <tbody>
              {(selectedTmpl.items || []).map((it, i) => (
                <tr key={`boq-item-${it.sl_no ?? i}`} className="border-t">
                  <td className="py-1">{it.sl_no}</td><td>{it.description}</td>
                  <td className="text-center">{it.unit}</td>
                  <td className="text-center">{it.quantity}</td>
                  <td className="text-right">{it.unit_rate?.toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}
