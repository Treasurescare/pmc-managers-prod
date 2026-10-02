import { useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, noticeDocsApi, formatApiError, showApiError } from "@/lib/api";

/**
 * NoticeViewModal — v50i.
 * Read-only full-document view of a notice. Shows every field in the
 * database record, lists primary + attachment uploads with inline View /
 * Download / Delete actions. "Delete" calls through to noticeDocsApi and
 * re-fetches so the UI stays in sync with the server.
 */
export default function NoticeViewModal({ noticeRef, onClose, onChanged }) {
  const [doc, setDoc] = useState(null);
  const [loading, setLoading] = useState(true);
  const [confirmDel, setConfirmDel] = useState(null); // {kind, file_name} | null

  const refresh = async () => {
    setLoading(true);
    try {
      const d = await adminApi.getNoticeAdmin(noticeRef);
      setDoc(d);
    } catch (e) { showApiError(e); }
    finally { setLoading(false); }
  };
  useEffect(() => { refresh(); /* eslint-disable-next-line */ }, [noticeRef]);

  if (!noticeRef) return null;

  const removeDoc = async (kind, file_name) => {
    try {
      await noticeDocsApi.deleteDocument(noticeRef, kind, file_name);
      toast.success(kind === "primary" ? "Primary document removed." : `Removed · ${file_name}`);
      setConfirmDel(null);
      await refresh();
      if (onChanged) onChanged();
    } catch (e) { showApiError(e); }
  };

  const Row = ({ label, children }) => (
    <div className="grid grid-cols-[200px_1fr] gap-3 py-2 border-b border-brand-navy/10 text-sm">
      <div className="text-brand-navy/60 text-xs uppercase tracking-widest">{label}</div>
      <div className="text-brand-navy">{children}</div>
    </div>
  );

  const DocRow = ({ meta, kind }) => (
    <div className="flex items-center gap-2 py-2 border-b border-brand-navy/10 text-sm"
         data-testid={`view-doc-${kind}-${meta.file_name}`}>
      <span className="text-xs text-brand-navy/50 font-mono">{kind === "primary" ? "PRIMARY" : "ATTACH"}</span>
      <span className="flex-1 truncate">{meta.file_name}</span>
      <span className="text-xs text-brand-navy/50">{Math.round((meta.size_bytes || 0) / 1024)} KB</span>
      <a href={meta.url} target="_blank" rel="noreferrer"
         className="text-xs underline text-brand-navy hover:text-brand-navy-deep"
         data-testid={`view-doc-open-${kind}-${meta.file_name}`}>View ↗</a>
      <a href={`${meta.url}?download=1`} download={meta.file_name}
         className="text-xs underline text-brand-navy hover:text-brand-navy-deep"
         data-testid={`view-doc-dl-${kind}-${meta.file_name}`}>Download</a>
      <button type="button"
        onClick={() => setConfirmDel({ kind, file_name: meta.file_name })}
        className="text-xs text-red-700 hover:underline"
        data-testid={`view-doc-del-${kind}-${meta.file_name}`}>Delete</button>
    </div>
  );

  return (
    <div className="fixed inset-0 z-40 bg-black/40 flex items-start justify-center p-4 overflow-y-auto"
         onClick={onClose} data-testid="notice-view-modal">
      <div className="bg-white border-2 border-brand-navy max-w-4xl w-full my-8 shadow-2xl"
           onClick={(e) => e.stopPropagation()}>
        <div className="flex items-center justify-between p-4 border-b border-brand-navy/10 bg-brand-cream">
          <div>
            <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">Notice document</div>
            <h2 className="text-lg font-semibold text-brand-navy">{doc?.title || "Loading…"}</h2>
            <div className="text-xs text-brand-navy/60 font-mono mt-1">{noticeRef}</div>
          </div>
          <button type="button" onClick={onClose} data-testid="notice-view-close"
                  className="text-sm px-3 py-1.5 border border-brand-navy/20 hover:bg-brand-navy hover:text-white">
            Close
          </button>
        </div>

        {loading && <div className="p-10 text-center text-brand-navy/50">Loading…</div>}
        {!loading && doc && (
          <div className="p-5">
            <Row label="Status">
              {doc.is_published ? (
                <span className="text-[11px] uppercase tracking-widest text-emerald-800 bg-emerald-50 border border-emerald-200 px-2 py-0.5">● Live</span>
              ) : (
                <span className="text-[11px] uppercase tracking-widest text-amber-900 bg-amber-50 border border-amber-300 px-2 py-0.5">✎ Draft</span>
              )}
              {doc.published_at && <span className="ml-2 text-xs text-brand-navy/60">published {doc.published_at.slice(0, 16).replace("T", " ")}</span>}
            </Row>
            <Row label="Reference">{doc.notice_ref}</Row>
            <Row label="Document type">{(doc.document_type || "").toUpperCase()}</Row>
            <Row label="Category">{doc.category}</Row>
            <Row label="Delivery country">{doc.delivery_country}</Row>
            <Row label="Budget">
              {doc.budget_amount
                ? `${doc.budget_currency || ""} ${Number(doc.budget_amount).toLocaleString()}`
                : <span className="text-brand-navy/40">not set</span>}
            </Row>
            <Row label="Submission deadline">{doc.submission_deadline?.replace("T", " ").slice(0, 16)}</Row>
            {doc.pre_bid_meeting_date && <Row label="Pre-bid meeting">{doc.pre_bid_meeting_date.slice(0, 16).replace("T", " ")}</Row>}
            <Row label="EMD">
              {doc.emd_config ? (
                <>
                  {doc.emd_config.fixed_amount > 0 && `Fixed ${doc.emd_config.currency || ""} ${doc.emd_config.fixed_amount}`}
                  {!doc.emd_config.fixed_amount && doc.emd_config.percentage > 0 && `${doc.emd_config.percentage}% of budget`}
                  {!doc.emd_config.fixed_amount && !doc.emd_config.percentage && <span className="text-brand-navy/40">no EMD</span>}
                </>
              ) : <span className="text-brand-navy/40">no EMD</span>}
            </Row>
            {doc.required_licenses?.length > 0 && (
              <Row label="Required licences">
                <div className="flex flex-wrap gap-1">
                  {doc.required_licenses.map((l) => (
                    <span key={l} className="text-[10px] uppercase tracking-widest bg-brand-navy/5 border border-brand-navy/15 px-2 py-0.5">{l}</span>
                  ))}
                </div>
              </Row>
            )}
            {doc.approval_matrix_id && <Row label="Approval matrix"><span className="font-mono text-xs">{doc.approval_matrix_id}</span></Row>}
            {doc.tender_template_id && <Row label="Tender template"><span className="font-mono text-xs">{doc.tender_template_id}</span></Row>}
            <Row label="Contact">
              {doc.contact_name || doc.contact_email ? (
                <>{doc.contact_name} {doc.contact_email && <a href={`mailto:${doc.contact_email}`} className="underline">({doc.contact_email})</a>}</>
              ) : <span className="text-brand-navy/40">—</span>}
            </Row>
            <Row label="Created">{doc.created_at?.replace("T", " ").slice(0, 16)}</Row>
            {doc.updated_at && <Row label="Last edited">{doc.updated_at.replace("T", " ").slice(0, 16)}</Row>}

            <div className="mt-5 border-t-2 border-brand-navy/10 pt-4">
              <div className="pmc-label mb-2">Full description</div>
              <div className="text-sm whitespace-pre-wrap text-brand-navy bg-brand-cream/40 border border-brand-navy/10 p-3">
                {doc.description || <span className="text-brand-navy/40">no description</span>}
              </div>
            </div>

            <div className="mt-5 border-t-2 border-brand-navy/10 pt-4">
              <div className="pmc-label mb-2">Uploaded documents</div>
              {doc.primary_document ? (
                <DocRow meta={doc.primary_document} kind="primary" />
              ) : (
                <div className="text-xs text-brand-navy/40 py-2 border-b border-brand-navy/10">
                  No primary document uploaded yet.
                </div>
              )}
              {(doc.attachments || []).map((a) => (
                <DocRow key={a.file_name + (a.uploaded_at || "")} meta={a} kind="attachment" />
              ))}
              {!doc.primary_document && (doc.attachments || []).length === 0 && (
                <div className="text-xs text-brand-navy/40 py-2">No attachments.</div>
              )}
            </div>

            <div className="mt-5 flex justify-between items-center">
              <a href={`/notices/${noticeRef}`} target="_blank" rel="noreferrer"
                 className="text-xs uppercase tracking-widest px-3 py-1.5 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white"
                 data-testid="view-public-preview">
                Open public page ↗
              </a>
              <div className="text-xs text-brand-navy/50">Tenant {doc.tenant_id || "default"}</div>
            </div>
          </div>
        )}
      </div>

      {confirmDel && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center"
             data-testid="confirm-doc-delete">
          <div className="bg-white border p-5 max-w-sm w-full" onClick={(e) => e.stopPropagation()}>
            <div className="text-brand-navy font-semibold mb-2">Remove this document?</div>
            <div className="text-sm text-brand-navy/70 mb-4">
              {confirmDel.kind === "primary" ? "This will detach the primary document from the notice."
                : <>Remove <strong>{confirmDel.file_name}</strong> from attachments?</>}
            </div>
            <div className="flex justify-end gap-2">
              <button type="button" onClick={() => setConfirmDel(null)}
                className="text-xs px-3 py-1.5 border border-brand-navy/20">Cancel</button>
              <button type="button" onClick={() => removeDoc(confirmDel.kind, confirmDel.file_name)}
                className="text-xs px-3 py-1.5 bg-red-600 text-white"
                data-testid="confirm-doc-delete-ok">Remove</button>
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
