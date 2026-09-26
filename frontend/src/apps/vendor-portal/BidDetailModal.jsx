import { useEffect, useState } from "react";
import { bidApi, publicApi, showApiError } from "@/lib/api";

const LABELS = {
  emd_pending: "EMD payment pending",
  submitted: "Submitted · awaiting evaluation",
  emd_paid: "EMD paid · under review",
  admin_flagged: "Flagged by admin",
  certifier_review: "Certifier review",
  certifier_cleared: "Certifier cleared",
  legal_review: "Legal review",
  legal_cleared: "Legal cleared",
  accounting_review: "Accounting review",
  accounting_cleared: "Accounting cleared",
  committee_review: "Committee review",
  on_hold: "On hold by PMC admin",
  awarded: "Awarded",
  rejected: "Rejected",
  withdrawn: "Withdrawn",
  closed: "Closed",
};

/**
 * v46z — vendor-side Bid Detail modal + printable view.
 *
 * Vendors need a plain read-only view of any bid they've placed, plus a
 * one-click print action. This component fetches full detail (bid.get()) and
 * pulls the notice metadata for context. Print uses window.print() with a
 * scoped stylesheet that hides everything except the modal content.
 */
export default function BidDetailModal({ bidId, onClose }) {
  const [bid, setBid]       = useState(null);
  const [notice, setNotice] = useState(null);

  useEffect(() => {
    if (!bidId) return;
    let cancelled = false;
    (async () => {
      try {
        const b = await bidApi.get(bidId);
        if (cancelled) return;
        setBid(b);
        try {
          const n = await publicApi.getNotice(b.notice_ref);
          if (!cancelled) setNotice(n);
        } catch { /* notice detail is best-effort */ }
      } catch (e) { showApiError(e); onClose?.(); }
    })();
    return () => { cancelled = true; };
  }, [bidId, onClose]);

  if (!bidId) return null;

  const doPrint = () => window.print();

  return (
    <div className="fixed inset-0 bg-black/50 z-50 flex items-center justify-center p-4 print:bg-transparent print:p-0 print:items-start"
         data-testid="bid-detail-modal">
      <style>{`
        @media print {
          body * { visibility: hidden; }
          #pmc-bid-print, #pmc-bid-print * { visibility: visible; }
          #pmc-bid-print { position: absolute; left: 0; top: 0; width: 100%; }
          .pmc-no-print { display: none !important; }
        }
      `}</style>
      <div id="pmc-bid-print" className="bg-white max-w-3xl w-full max-h-[90vh] overflow-y-auto p-6 print:max-h-none print:shadow-none">
        <div className="flex justify-between items-start border-b pb-3 mb-4">
          <div>
            <div className="text-xs uppercase tracking-widest text-slate-500">Bid submission</div>
            <div className="font-display text-2xl text-brand-navy">
              {bid?.bid_ref || "Loading…"}
            </div>
          </div>
          <div className="flex gap-2 pmc-no-print">
            <button onClick={doPrint}
                    data-testid="bid-print-btn"
                    className="px-3 py-1.5 text-xs bg-slate-800 text-white hover:bg-black">
              Print / Save PDF
            </button>
            <button onClick={onClose}
                    data-testid="bid-close-btn"
                    className="px-3 py-1.5 text-xs border">
              Close
            </button>
          </div>
        </div>

        {!bid ? (
          <div className="text-sm text-slate-500 py-10 text-center">Loading bid details…</div>
        ) : (
          <div className="space-y-5 text-sm">
            <section className="grid grid-cols-2 gap-3">
              <Field label="Notice" value={bid.notice_ref} />
              <Field label="Notice title" value={notice?.title || "—"} />
              <Field label="Status" value={LABELS[bid.status] || bid.status} />
              <Field label="Submitted at" value={(bid.submitted_at || bid.created_at || "").slice(0, 19).replace("T"," ")} />
              <Field label="Vendor" value={`${bid.company_name || ""} (${bid.vendor_ref || ""})`.trim()} />
              <Field label="Vendor email" value={bid.vendor_email} />
            </section>

            <section className="border-t pt-3">
              <div className="pmc-label mb-2">Commercial</div>
              <div className="grid grid-cols-2 gap-3">
                <Field label="Quoted price" value={`${bid.price_currency} ${(bid.price_amount || 0).toLocaleString()}`} />
                <Field label="EMD due" value={`${bid.emd_currency} ${(bid.emd_due_amount || 0).toLocaleString()}`} />
                <Field label="EMD paid" value={`${bid.emd_currency} ${(bid.emd_paid_amount || 0).toLocaleString()}`} />
                <Field label="EMD source" value={bid.emd_source || "—"} />
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
                <div className="pmc-label mb-1">Attached documents</div>
                <ul className="list-disc pl-5 space-y-1">
                  {bid.documents.map((d, i) => (
                    <li key={i} className="text-slate-700">
                      <span className="font-medium">{d.name || d.filename || "Document"}</span>
                      {d.mime && <span className="text-xs text-slate-500"> · {d.mime}</span>}
                      {d.url && <a href={d.url} target="_blank" rel="noopener noreferrer"
                                    className="ml-2 text-blue-700 underline pmc-no-print">open</a>}
                    </li>
                  ))}
                </ul>
              </section>
            )}

            {Array.isArray(bid.workflow_history) && bid.workflow_history.length > 0 && (
              <section className="border-t pt-3">
                <div className="pmc-label mb-1">Workflow history</div>
                <ul className="space-y-1 text-xs">
                  {bid.workflow_history.map((w, i) => (
                    <li key={i} className="flex justify-between border-b border-slate-100 py-1">
                      <span>{w.step || w.action}</span>
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

function Field({ label, value }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className="text-slate-800">{value || "—"}</div>
    </div>
  );
}
