import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, mastersApi, noticeDocsApi, tenderTemplateApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

export default function NoticesPanel() {
  const { t } = useI18n();
  const [items, setItems] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [matrices, setMatrices] = useState([]);
  const [templates, setTemplates] = useState([]);
  const [primaryFile, setPrimaryFile] = useState(null);
  const [attachmentFiles, setAttachmentFiles] = useState([]);
  const [me, setMe] = useState(null);
  const [draft, setDraft] = useState({
    title: "", description: "", document_type: "tender", category: "",
    delivery_country: "KZ", submission_deadline: "", budget_currency: "USD",
    budget_amount: null, is_published: false,
    emd_config: { fixed_amount: 0, percentage: 0, currency: "USD" },
    approval_matrix_id: "",
    tender_template_id: "",
  });

  const [filterStatus, setFilterStatus] = useState("");
  const [filterQuery, setFilterQuery] = useState("");
  const [showTemplateOnly, setShowTemplateOnly] = useState(false);

  const load = useCallback(() => {
    // Bucket A fix — use the admin-only endpoint that returns BOTH drafts
    // and published notices. The public /api/v1/notices endpoint filters
    // out drafts (is_published=true only), which made new drafts look
    // invisible after creation. Cache-buster prevents CloudFront from
    // serving a stale response after create/publish.
    adminApi.listAllNotices({ limit: 200, _: Date.now() })
      .then((d) => setItems(d.items || []))
      .catch((err) => console.warn("Failed to load notices:", err));
  }, []);
  useEffect(() => {
    load();
    mastersApi.listMatrices().then(setMatrices).catch(() => {});
    tenderTemplateApi.list().then(setTemplates).catch(() => {});
    adminApi.me().then(setMe).catch(() => {});
  }, [load]);

  // Bug #32 — accept any admin role variant, not just literal "admin".
  // Backend can return "admin" | "master_admin" | "superadmin" depending on
  // seeding path; testers on newer accounts were seeing the checkbox disabled
  // because their token said "master_admin".
  const isMasterAdmin = ["admin", "master_admin", "superadmin", "staff_admin"].includes(me?.role);

  const create = async () => {
    // Bug #31 — spell out which field failed AND the exact minimum, so testers
    // don't have to guess whether "3" or "10" applies to Title or Description.
    if (!draft.title || draft.title.trim().length < 3) {
      toast.error("Title is required · minimum 3 characters");
      return;
    }
    if (!draft.description || draft.description.trim().length < 10) {
      toast.error("Description is required · minimum 10 characters");
      return;
    }
    if (!draft.category) {
      toast.error("Category is required");
      return;
    }
    if (!draft.submission_deadline) {
      toast.error("Submission deadline is required");
      return;
    }
    try {
      const created = await adminApi.createNotice(draft);
      // Bug #5 defensive fallback — if backend returned no notice_ref
      // (rare edge case: response body stripped by a proxy), still show a
      // meaningful confirmation instead of "created undefined".
      const ref = created?.notice_ref;
      if (!ref) {
        toast.warning("Notice saved but reference number was not returned. Refreshing list.");
        setShowNew(false); load();
        return;
      }
      if (primaryFile) {
        try { await noticeDocsApi.uploadPrimary(ref, primaryFile); }
        catch (e) { toast.error(`Primary doc upload failed: ${formatApiError(e)}`); }
      }
      for (const f of attachmentFiles) {
        try { await noticeDocsApi.uploadAttachment(ref, f); }
        catch (e) { toast.error(`Attachment "${f.name}" failed: ${formatApiError(e)}`); }
      }
      // Bug #57/#58/#66 — explicit toast so testers know a draft was saved
      // (previously a plain "Notice created" made them think it was live).
      if (draft.is_published) {
        toast.success(`Notice published · ${ref}`);
      } else {
        toast.success(`Draft saved · ${ref}`, {
          description: "It appears in the list below with a DRAFT badge. Filter → 'Draft only' to isolate.",
        });
      }
      setShowNew(false);
      // Bug #22 — full form reset instead of only clearing title/description
      setDraft({
        title: "", description: "", document_type: "tender", category: "",
        delivery_country: "KZ", submission_deadline: "", budget_currency: "USD",
        budget_amount: null, is_published: false,
        emd_config: { fixed_amount: 0, percentage: 0, currency: "USD" },
        approval_matrix_id: "",
        tender_template_id: "",
      });
      setPrimaryFile(null); setAttachmentFiles([]);
      load();
    } catch (err) { toast.error(formatApiError(err)); }
  };

  return (
    <div data-testid="admin-notices-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-brand-navy/70">{t("admin.notices_published_hint")}</div>
        <button type="button" onClick={() => setShowNew(!showNew)} data-testid="notice-new-toggle"
          className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          {showNew ? t("admin.notices_cancel") : t("admin.notices_new")}
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
            <input type="number" min="0" step="0.01" value={draft.budget_amount || ""}
              onChange={(e) => {
                const v = parseFloat(e.target.value);
                // Bug #16 fix — block negative or NaN budgets
                setDraft({ ...draft, budget_amount: (isNaN(v) || v < 0) ? null : v });
              }}
              data-testid="notice-budget"
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
          <label className="md:col-span-2"><span className="pmc-label">Tender template (Tender Builder)</span>
            <select value={draft.tender_template_id || ""}
              onChange={(e) => setDraft({ ...draft, tender_template_id: e.target.value })}
              data-testid="notice-tender-template"
              className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              <option value="">No linked template — public page shows only the primary PDF</option>
              {templates.map((tpl) => (
                <option key={tpl.id} value={tpl.id}>
                  {tpl.is_master ? "📚 " : "✏ "}{tpl.name} · {(tpl.sections || []).length} sections
                </option>
              ))}
            </select>
            <span className="text-xs text-brand-navy/50 mt-1 block">
              Linking a template exposes the "Download PDF (watermarked)" and "Download all documents (.zip)" buttons on the public Notice page.
            </span>
          </label>
          <label className="col-span-2 flex items-center gap-2 text-sm">
            <input type="checkbox"
                   checked={draft.is_published}
                   disabled={!isMasterAdmin}
                   onChange={(e) => setDraft({ ...draft, is_published: e.target.checked })}
                   data-testid="notice-publish" />
            {isMasterAdmin
              ? "Publish immediately (visible on public board)"
              : "Publish immediately — reserved for Master Admin (this saves as draft)"}
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

      <div className="border border-brand-navy/10 bg-white mb-3 p-3 flex flex-wrap gap-2 items-center"
           data-testid="notices-filter-bar">
        <input value={filterQuery} onChange={(e) => setFilterQuery(e.target.value)}
               placeholder="Search title / ref…"
               data-testid="notices-filter-query"
               className="px-3 py-1.5 border border-brand-navy/20 text-sm flex-1 min-w-[180px]"/>
        <select value={filterStatus} onChange={(e) => setFilterStatus(e.target.value)}
                data-testid="notices-filter-status"
                className="px-3 py-1.5 border border-brand-navy/20 text-sm bg-white">
          <option value="">Any status</option>
          <option value="published">Published</option>
          <option value="draft">Draft</option>
          <option value="expired">Deadline past</option>
        </select>
        <label className="text-xs text-brand-navy/70 flex items-center gap-1">
          <input type="checkbox" checked={showTemplateOnly}
                 onChange={(e) => setShowTemplateOnly(e.target.checked)}
                 data-testid="notices-filter-template-only" />
          Template-linked only
        </label>
        <button type="button" onClick={() => { setFilterQuery(""); setFilterStatus(""); setShowTemplateOnly(false); }}
                data-testid="notices-filter-clear"
                className="px-3 py-1.5 text-xs uppercase tracking-widest border border-brand-navy/20 text-brand-navy/70 hover:bg-brand-navy/5">
          Clear
        </button>
      </div>

      <div className="border border-brand-navy/10 bg-white">
        {(() => {
          const now = new Date().toISOString();
          const filtered = items.filter((n) => {
            if (showTemplateOnly && !n.tender_template_id) return false;
            if (filterStatus === "published" && !n.is_published) return false;
            if (filterStatus === "draft" && n.is_published) return false;
            if (filterStatus === "expired" && (n.submission_deadline || "9999") > now) return false;
            if (filterQuery) {
              const q = filterQuery.toLowerCase();
              if (!(n.title || "").toLowerCase().includes(q) &&
                  !(n.notice_ref || "").toLowerCase().includes(q)) return false;
            }
            return true;
          });
          if (filtered.length === 0) return <div className="p-6 text-brand-navy/50 text-sm">{t("admin.notices_empty")}</div>;
          return filtered.map((n) => (
          <div key={n.id} className="p-4 border-b border-brand-navy/10 flex items-baseline gap-4 flex-wrap" data-testid={`notice-row-${n.notice_ref}`}>
            <span className="font-mono text-xs text-brand-navy-soft">{n.notice_ref}</span>
            <span className="pmc-pill uppercase text-[10px]">{n.document_type}</span>
            {/* Bug #57/#58/#66 fix — visible DRAFT / LIVE status badge */}
            {n.is_published ? (
              <span data-testid={`notice-status-${n.notice_ref}`}
                    className="text-[10px] uppercase tracking-widest text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5">
                ● Live
              </span>
            ) : (
              <span data-testid={`notice-status-${n.notice_ref}`}
                    className="text-[10px] uppercase tracking-widest text-amber-900 bg-amber-50 border border-amber-300 px-2 py-0.5 font-semibold">
                ✎ Draft
              </span>
            )}
            <span className="text-sm font-semibold text-brand-navy flex-1">{n.title}</span>
            {n.tender_template_id && (
              /* N-02 fix — template badge jumps to Tender Builder for that template */
              <a href={`/admin?tab=tender-builder&template=${n.tender_template_id}`}
                 data-testid={`notice-template-badge-${n.notice_ref}`}
                 title="Open this template in Tender Builder"
                 className="text-[10px] uppercase tracking-widest text-purple-700 bg-purple-50 border border-purple-200 px-2 py-0.5 hover:bg-purple-100 hover:underline">
                📐 template linked ↗
              </a>
            )}
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
            <a href={`/notices/${n.notice_ref}`} target="_blank" rel="noreferrer"
               data-testid={`notice-preview-${n.notice_ref}`}
               title="Open the public notice page in a new tab — exactly what bidders see"
               className="text-xs uppercase tracking-widest px-2 py-1 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
              {t("admin.notices_preview_bidder")} ↗
            </a>
            <span className="text-xs text-brand-navy/50 font-mono">{n.submission_deadline?.slice(0, 10)}</span>
          </div>
          ));
        })()}
      </div>
    </div>
  );
}
