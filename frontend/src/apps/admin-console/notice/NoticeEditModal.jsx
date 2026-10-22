import { useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, mastersApi, publicApi, noticeDocsApi, tenderTemplateApi, formatApiError, showApiError } from "@/lib/api";
import { InfoDot } from "@/components/InfoDot";
import EmdMasterPicker from "./EmdMasterPicker";
import { CurrencySelect } from "@/components/CurrencySelect";

/**
 * NoticeEditModal — v50i.
 * Full editable form for an existing notice. Reuses the same field set as
 * Create. Documents are uploaded via noticeDocsApi (not through PATCH)
 * so partial saves don't risk dropping existing files. Save calls
 * adminApi.updateNotice() then triggers onSaved() to refresh the parent list.
 */
export default function NoticeEditModal({ noticeRef, onClose, onSaved, isMasterAdmin }) {
  const [draft, setDraft] = useState(null);
  const [categories, setCategories] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [contractTypes, setContractTypes] = useState([]);
  const [countries, setCountries] = useState([]);
  const [matrices, setMatrices] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [primaryFile, setPrimaryFile] = useState(null);
  const [attachmentFiles, setAttachmentFiles] = useState([]);
  const [busy, setBusy] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    (async () => {
      try {
        const [n, cs, mats, tpls] = await Promise.all([
          adminApi.getNoticeAdmin(noticeRef),
          publicApi.countries().catch(() => []),
          mastersApi.listMatrices().catch(() => []),
          tenderTemplateApi.list().catch(() => []),
        ]);
        setDraft({
          title: n.title || "",
          description: n.description || "",
          document_type: n.document_type || "tender",
          category: n.category || "",
          sector_code: n.sector_code || "",
          contract_type_code: n.contract_type_code || "",
          delivery_country: n.delivery_country || "KZ",
          submission_deadline: (n.submission_deadline || "").slice(0, 16),
          budget_currency: n.budget_currency || "USD",
          budget_amount: n.budget_amount ?? null,
          is_published: !!n.is_published,
          emd_config: n.emd_config || { fixed_amount: 0, percentage: 0, currency: n.budget_currency || "USD" },
          approval_matrix_id: n.approval_matrix_id || "",
          tender_template_id: n.tender_template_id || "",
          contact_email: n.contact_email || "",
          contact_name: n.contact_name || "",
          required_licenses: n.required_licenses || [],
        });
        setCountries(cs);
        setMatrices(mats);
        setTemplates(tpls);
      } catch (e) { showApiError(e); }
      finally { setLoading(false); }
    })();
  }, [noticeRef]);

  useEffect(() => {
    if (!draft?.delivery_country) return;
    mastersApi.listCategories(draft.delivery_country)
      .then((rows) => setCategories(Array.isArray(rows) ? rows : []))
      .catch(() => setCategories([]));
  }, [draft?.delivery_country]);

  useEffect(() => {
    mastersApi.listSectors().then((r) => setSectors(Array.isArray(r) ? r : [])).catch(() => setSectors([]));
    mastersApi.listContractTypes().then((r) => setContractTypes(Array.isArray(r) ? r : [])).catch(() => setContractTypes([]));
  }, []);

  if (!noticeRef) return null;

  // v52bn — safety net: a LIVE notice must never be edited inline (fields or
  // documents). Every change goes out as a versioned corrigendum so the audit
  // trail stays defensible. The list already routes live notices away, but
  // this modal could be opened from other entry points.
  if (!loading && draft?.is_published) {
    return (
      <div className="fixed inset-0 z-40 bg-black/40 flex items-start justify-center p-4 overflow-y-auto"
           onClick={onClose} data-testid="notice-edit-modal">
        <div className="bg-white border-2 border-brand-navy max-w-lg w-full my-8 shadow-2xl"
             onClick={(e) => e.stopPropagation()}>
          <div className="flex items-center justify-between p-4 border-b border-brand-navy/10 bg-brand-cream">
            <div>
              <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">Edit notice</div>
              <h2 className="text-lg font-semibold text-brand-navy font-mono">{noticeRef}</h2>
            </div>
            <button type="button" onClick={onClose} data-testid="notice-edit-close"
                    className="text-sm px-3 py-1.5 border border-brand-navy/20 hover:bg-brand-navy hover:text-white">
              Close
            </button>
          </div>
          <div className="p-6" data-testid="notice-edit-live-locked">
            <div className="border-2 border-amber-500 bg-amber-50 p-4 text-sm text-amber-900">
              <strong>This notice is live.</strong> Field and document changes on a
              published notice must be issued as a <strong>corrigendum</strong> so every
              amendment is versioned with a date and reason.
            </div>
            <div className="mt-6 flex justify-end gap-2">
              <button type="button" onClick={onClose}
                      className="px-5 py-2.5 text-[11px] uppercase tracking-widest border border-brand-navy/20">
                Cancel
              </button>
              <a href={`/admin/e/corrigenda?notice=${noticeRef}`}
                 data-testid="notice-edit-goto-corrigenda"
                 className="px-6 py-2.5 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
                Open Corrigendum workspace ▸
              </a>
            </div>
          </div>
        </div>
      </div>
    );
  }

  const save = async () => {
    if (!draft.title || draft.title.trim().length < 3) { toast.error("Title · min 3 characters"); return; }
    if (!draft.description || draft.description.trim().length < 10) { toast.error("Description · min 10 characters"); return; }
    if (!draft.category) { toast.error("Category is required"); return; }
    if (!draft.submission_deadline) { toast.error("Submission deadline is required"); return; }
    setBusy(true);
    try {
      // v51aa — never send blank contact_email / contact_name strings to the
      // backend. The Pydantic EmailStr validator rejects "" with HTTP 422
      // ("must have an @-sign"), which blocked submit-for-approval when the
      // field was left empty.
      const payload = { ...draft };
      if (!payload.contact_email || !payload.contact_email.trim()) delete payload.contact_email;
      if (!payload.contact_name  || !payload.contact_name.trim())  delete payload.contact_name;
      await adminApi.updateNotice(noticeRef, payload);
      if (primaryFile) {
        try { await noticeDocsApi.uploadPrimary(noticeRef, primaryFile); }
        catch (e) { toast.error(`Primary doc upload failed: ${formatApiError(e)}`); }
      }
      for (const f of attachmentFiles) {
        try { await noticeDocsApi.uploadAttachment(noticeRef, f); }
        catch (e) { toast.error(`Attachment "${f.name}" failed: ${formatApiError(e)}`); }
      }
      toast.success(`Notice updated · ${noticeRef}`);
      if (onSaved) onSaved();
      onClose();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-start justify-center p-4 overflow-y-auto"
         onClick={onClose} data-testid="notice-edit-modal">
      <div className="bg-white border-2 border-brand-navy max-w-5xl w-full my-8 shadow-2xl"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-brand-navy/10 bg-brand-cream">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">Edit notice</div>
            <h2 className="text-lg font-semibold text-brand-navy font-mono">{noticeRef}</h2>
          </div>
          <button type="button" onClick={onClose} data-testid="notice-edit-close"
                  className="text-sm px-3 py-1.5 border border-brand-navy/20 hover:bg-brand-navy hover:text-white">
            Close
          </button>
        </div>

        {loading && <div className="p-10 text-center text-brand-navy/50">Loading…</div>}
        {!loading && draft && (
          <div className="p-5 grid gap-4 md:grid-cols-2">
            <label className="md:col-span-2"><span className="pmc-label">Title<InfoDot tip="Human-readable name shown on public Notice Board." /></span>
              <input value={draft.title} onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                data-testid="edit-title" className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>

            <label className="md:col-span-2"><span className="pmc-label">Description<InfoDot tip="Full scope and bidder eligibility. Rendered on the public notice page." /></span>
              <textarea rows={5} value={draft.description} onChange={(e) => setDraft({ ...draft, description: e.target.value })}
                data-testid="edit-description" className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>

            <label><span className="pmc-label">Category</span>
              <select value={draft.category} onChange={(e) => setDraft({ ...draft, category: e.target.value })}
                data-testid="edit-category" className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white">
                <option value="">— Select a category —</option>
                {categories.map((c) => (
                  <option key={c.id || c.code} value={c.name}>
                    {c.unspsc_code ? `${c.unspsc_code} · ` : ""}{c.name}
                  </option>
                ))}
              </select></label>

            <label><span className="pmc-label">Sector<InfoDot tip="Industry/domain for this tender. Optional now; becomes mandatory at go-live." /></span>
              <select value={draft.sector_code || ""} onChange={(e) => setDraft({ ...draft, sector_code: e.target.value })}
                data-testid="edit-sector" className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white">
                <option value="">— Select a sector —</option>
                {sectors.filter((s) => !s.parent_code).map((p) => (
                  <optgroup key={p.code} label={p.name}>
                    <option value={p.code}>{p.name} (all)</option>
                    {sectors.filter((c) => c.parent_code === p.code).map((c) => (
                      <option key={c.code} value={c.code}>&nbsp;&nbsp;{c.name}</option>
                    ))}
                  </optgroup>
                ))}
              </select></label>

            <label><span className="pmc-label">Contract type<InfoDot tip="Delivery model: EPC, Works, PPP, Supply, Services… Optional now; mandatory at go-live." /></span>
              <select value={draft.contract_type_code || ""} onChange={(e) => setDraft({ ...draft, contract_type_code: e.target.value })}
                data-testid="edit-contract-type" className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white">
                <option value="">— Select a contract type —</option>
                {contractTypes.filter((s) => !s.parent_code).map((p) => (
                  <optgroup key={p.code} label={p.name}>
                    <option value={p.code}>{p.name} (general)</option>
                    {contractTypes.filter((c) => c.parent_code === p.code).map((c) => (
                      <option key={c.code} value={c.code}>&nbsp;&nbsp;{c.name}</option>
                    ))}
                  </optgroup>
                ))}
              </select></label>

            <label><span className="pmc-label">Document type</span>
              <select value={draft.document_type} onChange={(e) => setDraft({ ...draft, document_type: e.target.value })}
                data-testid="edit-doc-type" className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
                <option value="tender">Tender</option><option value="rfp">RFP</option><option value="rfq">RFQ</option></select></label>

            <label><span className="pmc-label">Delivery country</span>
              <select value={draft.delivery_country}
                onChange={(e) => setDraft({ ...draft, delivery_country: e.target.value })}
                data-testid="edit-country" className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white">
                {countries.map((c) => (
                  <option key={c.code} value={c.code}>{c.code} · {c.name_en || c.name}</option>
                ))}
              </select></label>

            <label><span className="pmc-label">Submission deadline</span>
              <input type="datetime-local" value={draft.submission_deadline}
                onChange={(e) => setDraft({ ...draft, submission_deadline: e.target.value })}
                data-testid="edit-deadline" className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>

            <label><span className="pmc-label">Budget currency</span>
              <CurrencySelect country={draft.delivery_country} value={draft.budget_currency}
                onChange={(v) => setDraft({ ...draft, budget_currency: v })}
                testId="edit-currency" preserveInitial
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white" /></label>

            <label><span className="pmc-label">Budget amount</span>
              <input type="number" min="0" step="0.01" value={draft.budget_amount || ""}
                onChange={(e) => {
                  const v = parseFloat(e.target.value);
                  setDraft({ ...draft, budget_amount: (isNaN(v) || v < 0) ? null : v });
                }}
                data-testid="edit-budget" className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>

            <EmdMasterPicker
              country={draft.delivery_country}
              category={draft.category}
              tenderValue={draft.budget_amount || 0}
              emdConfig={draft.emd_config}
              onPick={(cfg) => setDraft({ ...draft, emd_config: { ...draft.emd_config, ...cfg } })} />

            <label><span className="pmc-label">EMD — Fixed amount ({draft.budget_currency})</span>
              <input type="number" min="0" value={draft.emd_config.fixed_amount || 0}
                onChange={(e) => setDraft({ ...draft, emd_config: { ...draft.emd_config, fixed_amount: parseFloat(e.target.value) || 0, currency: draft.budget_currency } })}
                data-testid="edit-emd-fixed" className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>

            <label><span className="pmc-label">EMD — % of budget</span>
              <input type="number" step="0.01" min="0" max="100" value={draft.emd_config.percentage || 0}
                onChange={(e) => setDraft({ ...draft, emd_config: { ...draft.emd_config, percentage: parseFloat(e.target.value) || 0, currency: draft.budget_currency } })}
                data-testid="edit-emd-pct" className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>

            <label className="md:col-span-2"><span className="pmc-label">Approval Matrix</span>
              <select value={draft.approval_matrix_id || ""}
                onChange={(e) => setDraft({ ...draft, approval_matrix_id: e.target.value })}
                data-testid="edit-matrix" className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
                <option value="">Default pipeline</option>
                {matrices.map((m) => <option key={m.id} value={m.id}>{m.name}</option>)}
              </select></label>

            <label className="md:col-span-2"><span className="pmc-label">Tender template</span>
              <select value={draft.tender_template_id || ""}
                onChange={(e) => setDraft({ ...draft, tender_template_id: e.target.value })}
                data-testid="edit-template" className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
                <option value="">No linked template</option>
                {templates.map((tpl) => (
                  <option key={tpl.id} value={tpl.id}>
                    {tpl.is_master ? "📚 " : "✏ "}{tpl.name} · {(tpl.sections || []).length} sections
                  </option>
                ))}
              </select></label>

            <label className="md:col-span-2 flex items-center gap-2 text-sm">
              <input type="checkbox" checked={draft.is_published}
                disabled={!isMasterAdmin && !draft.is_published}
                onChange={(e) => setDraft({ ...draft, is_published: e.target.checked })}
                data-testid="edit-publish" />
              {isMasterAdmin || draft.is_published
                ? "Published (visible on public board)"
                : "Publish immediately — reserved for Master Admin"}
            </label>

            <div className="md:col-span-2 border-t border-brand-navy/10 pt-4 mt-2">
              <div className="pmc-label mb-2">Add more documents (keeps existing)</div>
              <div className="grid gap-3 md:grid-cols-2">
                <label className="text-sm">
                  <span className="text-brand-navy/70">Replace primary document (optional)</span>
                  <input type="file" accept=".pdf,.doc,.docx"
                    onChange={(e) => setPrimaryFile(e.target.files?.[0] || null)}
                    data-testid="edit-primary-file" className="mt-1 w-full text-sm" />
                  {primaryFile && <div className="mt-1 text-xs text-brand-navy/60">Selected: {primaryFile.name}</div>}
                </label>
                <label className="text-sm">
                  <span className="text-brand-navy/70">Add attachments (appended)</span>
                  <input type="file" multiple accept=".pdf,.doc,.docx,.xls,.xlsx,.dwg,.jpg,.png"
                    onChange={(e) => setAttachmentFiles(Array.from(e.target.files || []))}
                    data-testid="edit-attachments" className="mt-1 w-full text-sm" />
                  {attachmentFiles.length > 0 && (
                    <div className="mt-1 text-xs text-brand-navy/60">
                      {attachmentFiles.length} file(s): {attachmentFiles.map(f => f.name).join(", ")}
                    </div>
                  )}
                </label>
              </div>
              <div className="text-[11px] text-brand-navy/50 mt-2">
                To remove existing documents, close this and open the "View" modal — each uploaded file has an inline Delete action.
              </div>
            </div>

            <div className="md:col-span-2 flex justify-end gap-2">
              <button type="button" onClick={onClose}
                className="px-5 py-2.5 text-[11px] uppercase tracking-widest border border-brand-navy/20">Cancel</button>
              <button type="button" onClick={save} disabled={busy}
                data-testid="edit-save"
                className="px-8 py-2.5 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90 disabled:opacity-60">
                {busy ? "Saving…" : "Save changes"}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
