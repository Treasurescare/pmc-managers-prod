import { useEffect, useState } from "react";
import { api, publicApi, showApiError } from "@/lib/api";

/**
 * v47f — Admin-side bid detail modal. Shows the full vendor submission plus
 * attachments (inline preview for images/PDF, otherwise a download link),
 * workflow history and EMD breakdown. Reused by every admin bid list.
 */
export default function AdminBidDetailModal({ bidId, onClose }) {
  const [bid, setBid]       = useState(null);
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    if (!bidId) return;
    let cancelled = false;
    (async () => {
      try {
        const b = (await api.get(`/api/v1/bids/admin/${bidId}`)).data;
        if (cancelled) return;
        setBid(b);
        try {
          const n = await publicApi.getNotice(b.notice_ref);
          if (!cancelled) setNotice(n);
        } catch { /* best-effort */ }
      } catch (e) { showApiError(e); onClose?.(); }
    })();
    return () => { cancelled = true; };
  }, [bidId, onClose]);

  if (!bidId) return null;
  const doPrint = () => window.print();

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 print:bg-transparent print:p-0 print:items-start"
         data-testid="admin-bid-detail-modal">
      <style>{`@media print { body * { visibility: hidden; } #pmc-adminbid-print, #pmc-adminbid-print * { visibility: visible; } #pmc-adminbid-print { position: absolute; left: 0; top: 0; width: 100%; } .pmc-no-print { display: none !important; } }`}</style>
      <div id="pmc-adminbid-print" className="bg-white max-w-4xl w-full max-h-[92vh] overflow-y-auto p-6 print:max-h-none">
        <div className="flex justify-between items-start border-b pb-3 mb-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-slate-500">Bid submission (admin view)</div>
            <div className="font-display text-2xl text-brand-navy">{bid?.bid_ref || "Loading…"}</div>
          </div>
          <div className="flex gap-2 pmc-no-print">
            <button onClick={doPrint} data-testid="admin-bid-print-btn"
              className="px-3 py-1.5 text-xs bg-slate-800 text-white hover:bg-black">Print / Save PDF</button>
            <button onClick={onClose} data-testid="admin-bid-close-btn"
              className="px-3 py-1.5 text-xs border">Close</button>
          </div>
        </div>

        {!bid ? (
          <div className="text-sm text-slate-500 py-10 text-center">Loading bid details…</div>
        ) : (
          <div className="space-y-5 text-sm">
            <section className="grid grid-cols-2 gap-3">
              <F label="Notice" value={bid.notice_ref} />
              <F label="Notice title" value={notice?.title || "—"} />
              <F label="Status" value={bid.status} />
              <F label="Submitted at" value={(bid.submitted_at || bid.created_at || "").slice(0, 19).replace("T", " ")} />
              <F label="Vendor" value={`${bid.company_name || ""} (${bid.vendor_ref || ""})`.trim()} />
              <F label="Vendor email" value={bid.vendor_email} />
            </section>

            <section className="border-t pt-3">
              <div className="pmc-label mb-2">Commercial</div>
              <div className="grid grid-cols-2 gap-3">
                <F label="Quoted price" value={`${bid.price_currency} ${(bid.price_amount || 0).toLocaleString()}`} />
                <F label="EMD due" value={`${bid.emd_currency} ${(bid.emd_due_amount || 0).toLocaleString()}`} />
                <F label="EMD paid" value={`${bid.emd_currency} ${(bid.emd_paid_amount || 0).toLocaleString()}`} />
                <F label="EMD source" value={bid.emd_source || "—"} />
              </div>
            </section>

            {bid.technical_notes && (
              <section className="border-t pt-3">
                <div className="pmc-label mb-1">Technical notes</div>
                <div className="whitespace-pre-wrap text-slate-700">{bid.technical_notes}</div>
              </section>
            )}
            {bid.commercial_notes && (
              <section className="border-t pt-3">
                <div className="pmc-label mb-1">Commercial notes</div>
                <div className="whitespace-pre-wrap text-slate-700">{bid.commercial_notes}</div>
              </section>
            )}

            {Array.isArray(bid.documents) && bid.documents.length > 0 && (
              <section className="border-t pt-3">
                <div className="pmc-label mb-2">Attached documents · {bid.documents.length}</div>
                <div className="grid gap-2">
                  {bid.documents.map((d, i) => {
                    const mime = d.mime || "";
                    const isImg = mime.startsWith("image/");
                    const isPdf = mime === "application/pdf";
                    return (
                      <div key={i} className="border p-3">
                        <div className="flex justify-between items-center mb-2">
                          <div className="text-sm">
                            <span className="font-medium">{d.name || d.filename || `Document ${i + 1}`}</span>
                            {mime && <span className="text-xs text-slate-500 ml-2">· {mime}</span>}
                          </div>
                          {d.url && <a href={d.url} target="_blank" rel="noopener noreferrer"
                                        className="text-xs text-blue-700 underline pmc-no-print"
                                        data-testid={`admin-bid-doc-open-${i}`}>Open in new tab</a>}
                        </div>
                        {d.url && isImg && <img src={d.url} alt={d.name || "attachment"}
                                                   className="max-h-64 border" />}
                        {d.url && isPdf && <iframe src={d.url} title={d.name || `pdf-${i}`}
                                                     className="w-full h-96 border pmc-no-print" />}
                      </div>
                    );
                  })}
                </div>
              </section>
            )}

            {Array.isArray(bid.workflow_history) && bid.workflow_history.length > 0 && (
              <section className="border-t pt-3">
                <div className="pmc-label mb-2">Workflow history</div>
                <ul className="space-y-1 text-xs">
                  {bid.workflow_history.map((w, i) => (
                    <li key={i} className="flex justify-between border-b border-slate-100 py-1">
                      <span>
                        <strong>{w.action || w.step}</strong>
                        {w.by && <span className="text-slate-500"> · by {w.by}</span>}
                        {w.notes && <span className="text-slate-500"> · {w.notes}</span>}
                      </span>
                      <span className="text-slate-500">{(w.at || "").slice(0, 16).replace("T", " ")}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

function F({ label, value }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className="text-slate-800">{value || "—"}</div>
    </div>
  );
}
