import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, mastersApi, noticeDocsApi, formatApiError } from "@/lib/api";

export default function NoticesPanel() {
  const [items, setItems] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [matrices, setMatrices] = useState([]);
  const [primaryFile, setPrimaryFile] = useState(null);
  const [attachmentFiles, setAttachmentFiles] = useState([]);
  const [draft, setDraft] = useState({
    title: "", description: "", document_type: "tender", category: "",
    delivery_country: "KZ", submission_deadline: "", budget_currency: "USD",
    budget_amount: null, is_published: true,
    emd_config: { fixed_amount: 0, percentage: 0, currency: "USD" },
    approval_matrix_id: "",
  });

  const load = useCallback(() => {
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/v1/notices?limit=100`)
      .then((r) => r.json())
      .then((d) => setItems(d.items || []))
      .catch((err) => console.warn("Failed to load notices:", err));
  }, []);
  useEffect(() => {
    load();
    mastersApi.listMatrices().then(setMatrices).catch(() => {});
  }, [load]);

  const create = async () => {
    if (!draft.title || !draft.description || !draft.category || !draft.submission_deadline) {
      toast.error("Title, description, category and deadline are required");
      return;
    }
    try {
      const created = await adminApi.createNotice(draft);
      if (primaryFile) {
        try { await noticeDocsApi.uploadPrimary(created.notice_ref, primaryFile); }
        catch (e) { toast.error(`Primary doc upload failed: ${formatApiError(e)}`); }
      }
      for (const f of attachmentFiles) {
        try { await noticeDocsApi.uploadAttachment(created.notice_ref, f); }
        catch (e) { toast.error(`Attachment "${f.name}" failed: ${formatApiError(e)}`); }
      }
      toast.success(`Notice created · ${created.notice_ref}`);
      setShowNew(false);
      setDraft({ ...draft, title: "", description: "" });
      setPrimaryFile(null); setAttachmentFiles([]);
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  return (
    <div data-testid="admin-notices-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-brand-navy/70">Published notices — visible on the public board</div>
        <button type="button" onClick={() => setShowNew(!showNew)} data-testid="notice-new-toggle"
          className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          {showNew ? "Cancel" : "New notice"}
        </button>
      </div>

      {showNew && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-4 md:grid-cols-2" data-testid="notice-new-form">
          <label className="col-span-2"><span className="pmc-label">Title</span>
            <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })} data-testid="notice-title"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label className="col-span-2"><span className="pmc-label">Description</span>
            <textarea rows={4} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })} data-testid="notice-description"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Category</span>
            <input value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value })} data-testid="notice-category"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Document type</span>
            <select value={draft.document_type} onChange={(e) => setDraft({ ...draft, document_type: e.target.value })} data-testid="notice-doc-type"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              <option value="tender">Tender</option><option value="rfp">RFP</option><option value="rfq">RFQ</option></select></label>
          <label><span className="pmc-label">Delivery country</span>
            <input value={draft.delivery_country} onChange={(e) => setDraft({ ...draft, delivery_country: e.target.value })} data-testid="notice-country"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Submission deadline</span>
            <input type="datetime-local" value={draft.submission_deadline} onChange={(e) => setDraft({ ...draft, submission_deadline: e.target.value })} data-testid="notice-deadline"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Budget currency</span>
            <input value={draft.budget_currency} onChange={(e) => setDraft({ ...draft, budget_currency: e.target.value })} data-testid="notice-currency"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Budget amount</span>
            <input type="number" value={draft.budget_amount || ""} onChange={(e) => setDraft({ ...draft, budget_amount: parseFloat(e.target.value) || null })} data-testid="notice-budget"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">EMD — Fixed amount ({draft.budget_currency})</span>
            <input type="number" min="0" value={draft.emd_config.fixed_amount || 0}
              onChange={(e) => setDraft({ ...draft, emd_config: { ...draft.emd_config, fixed_amount: parseFloat(e.target.value) || 0, currency: draft.budget_currency } })}
              data-testid="notice-emd-fixed"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">EMD — % of budget</span>
            <input type="number" step="0.01" min="0" max="100" value={draft.emd_config.percentage || 0}
              onChange={(e) => setDraft({ ...draft, emd_config: { ...draft.emd_config, percentage: parseFloat(e.target.value) || 0, currency: draft.budget_currency } })}
              data-testid="notice-emd-percentage"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label className="md:col-span-2"><span className="pmc-label">Approval Matrix (Masters)</span>
            <select value={draft.approval_matrix_id || ""}
              onChange={(e) => setDraft({ ...draft, approval_matrix_id: e.target.value })}
              data-testid="notice-matrix"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              <option value="">Default pipeline (Escrow → Admin → Certifier → Legal → Accounting → Committee)</option>
              {matrices.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
            </select>
          </label>
          <label className="col-span-2 flex items-center gap-2 text-sm">
            <input type="checkbox" checked={draft.is_published} onChange={(e) => setDraft({ ...draft, is_published: e.target.checked })} data-testid="notice-publish" />
            Publish immediately (visible on public board)
          </label>

          <div className="col-span-2 border-t border-brand-navy/10 pt-4 mt-2">
            <div className="pmc-label mb-2">Tender / RFP / RFQ documents</div>
            <div className="grid gap-3 md:grid-cols-2">
              <label className="text-sm">
                <span className="text-brand-navy/70">Primary document (PDF/DOCX, single)</span>
                <input type="file" accept=".pdf,.doc,.docx"
                       onChange={(e) => setPrimaryFile(e.target.files?.[0] || null)}
                       data-testid="notice-primary-file"
                       className="mt-1 w-full text-sm" />
                {primaryFile && <div className="mt-1 text-xs text-brand-navy/60">Selected: {primaryFile.name}</div>}
              </label>
              <label className="text-sm">
                <span className="text-brand-navy/70">Additional attachments (BOQ, drawings, addenda…)</span>
                <input type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.dwg,.jpg,.png"
                       onChange={(e) => setAttachmentFiles(Array.from(e.target.files || []))}
                       data-testid="notice-attachments"
                       className="mt-1 w-full text-sm" />
                {attachmentFiles.length > 0 && (
                  <div className="mt-1 text-xs text-brand-navy/60">
                    {attachmentFiles.length} file(s): {attachmentFiles.map(f => f.name).join(", ")}
                  </div>
                )}
              </label>
            </div>
          </div>

          <div className="col-span-2 flex justify-end">
            <button type="button" onClick={create} data-testid="notice-create"
              className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">Create notice</button>
          </div>
        </div>
      )}

      <div className="border border-brand-navy/10 bg-white">
        {items.length === 0 && <div className="p-6 text-brand-navy/50 text-sm">No published notices yet.</div>}
        {items.map((n) => (
          <div key={n.id} className="p-4 border-b border-brand-navy/10 flex items-baseline gap-4 flex-wrap" data-testid={`notice-row-${n.notice_ref}`}>
            <span className="font-mono text-xs text-brand-navy-soft">{n.notice_ref}</span>
            <span className="pmc-pill uppercase text-[10px]">{n.document_type}</span>
            <span className="text-sm font-semibold text-brand-navy flex-1">{n.title}</span>
            {n.primary_document && (
              <a href={`${process.env.REACT_APP_BACKEND_URL}${n.primary_document.url}`} target="_blank" rel="noreferrer"
                 data-testid={`notice-primary-${n.notice_ref}`}
                 className="text-xs underline text-brand-navy/70">
                📎 {n.primary_document.file_name}
              </a>
            )}
            {(n.attachments || []).length > 0 && (
              <span className="text-xs text-brand-navy/50" data-testid={`notice-attach-count-${n.notice_ref}`}>
                +{n.attachments.length} attachment(s)
              </span>
            )}
            <span className="text-xs text-brand-navy/50 font-mono">{n.submission_deadline?.slice(0, 10)}</span>
          </div>
        ))}
      </div>
    </div>
  );
}
