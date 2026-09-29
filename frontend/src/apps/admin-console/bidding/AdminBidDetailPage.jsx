import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, publicApi, showApiError } from "@/lib/api";

/**
 * v47h — full-page admin bid detail. Shows the ENTIRE vendor submission:
 * identity, commercial + EMD breakdown, notes, every uploaded document
 * (inline preview for images/PDF, open/download for all) and workflow history.
 */
export default function AdminBidDetailPage() {
  const { bidId } = useParams();
  const nav = useNavigate();
  const [bid, setBid] = useState(null);
  const [notice, setNotice] = useState(null);
  const [err, setErr] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const b = (await api.get(`/api/v1/bids/admin/${bidId}`)).data;
        if (cancelled) return;
        setBid(b);
        try {
          const n = await publicApi.getNotice(b.notice_ref);
          if (!cancelled) setNotice(n);
        } catch { /* notice context is best-effort */ }
      } catch (e) {
        if (e?.response?.status === 401 || e?.response?.status === 403) {
          return nav("/admin/login");
        }
        setErr(e?.response?.data?.detail || "Could not load this bid");
        showApiError(e);
      }
    })();
    return () => { cancelled = true; };
  }, [bidId, nav]);

  const docUrl = (d) =>
    d.url || (d.key ? `/api/v1/uploads/files/${d.key}` : null);

  return (
    <div className="min-h-screen bg-slate-50" data-testid="admin-bid-page">
      <style>{`@media print { .pmc-no-print { display: none !important; } body { background: white; } }`}</style>
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between flex-wrap gap-3 pmc-no-print">
        <div className="flex items-center gap-4">
          <Link to="/admin?tab=bidding" data-testid="admin-bid-back"
            className="text-xs uppercase tracking-widest border border-brand-navy/30 px-3 py-1.5 text-brand-navy hover:bg-brand-navy hover:text-white">
            ← Back to bids
          </Link>
          <div>
            <div className="text-[10px] uppercase tracking-widest text-slate-500">Bid submission · admin view</div>
            <div className="font-display text-xl text-brand-navy" data-testid="admin-bid-ref">
              {bid?.bid_ref || "Loading…"}
            </div>
          </div>
        </div>
        <button onClick={() => window.print()} data-testid="admin-bid-print"
          className="px-4 py-2 text-xs uppercase tracking-widest bg-slate-800 text-white hover:bg-black">
          Print / Save PDF
        </button>
      </header>

      <main className="max-w-5xl mx-auto px-6 py-8">
        {err && (
          <div className="border border-red-300 bg-red-50 text-red-800 p-4 text-sm" data-testid="admin-bid-error">{err}</div>
        )}
        {!bid && !err && <div className="text-slate-500 py-16 text-center">Loading bid details…</div>}

        {bid && (
          <div className="space-y-6">
            <section className="bg-white border p-6">
              <div className="pmc-label mb-3">Submission</div>
              <div className="grid gap-4 md:grid-cols-3 text-sm">
                <F label="Notice" value={bid.notice_ref} mono />
                <F label="Notice title" value={notice?.title || "—"} />
                <F label="Status" value={bid.status} />
                <F label="Submitted at" value={(bid.submitted_at || bid.created_at || "").slice(0, 19).replace("T", " ")} />
                <F label="Vendor" value={bid.company_name || "—"} />
                <F label="Vendor ref" value={bid.vendor_ref || "—"} mono />
                <F label="Vendor email" value={bid.vendor_email || "—"} mono />
              </div>
            </section>

            <section className="bg-white border p-6" data-testid="admin-bid-commercial">
              <div className="pmc-label mb-3">Commercial</div>
              <div className="grid gap-4 md:grid-cols-4 text-sm">
                <F label="Quoted price" value={`${bid.price_currency || ""} ${(bid.price_amount ?? 0).toLocaleString()}`} />
                <F label="EMD due" value={`${bid.emd_currency || ""} ${(bid.emd_due_amount ?? 0).toLocaleString()}`} />
                <F label="EMD paid" value={`${bid.emd_currency || ""} ${(bid.emd_paid_amount ?? 0).toLocaleString()}`} />
                <F label="EMD source" value={bid.emd_source || "—"} />
              </div>
            </section>

            {(bid.technical_notes || bid.commercial_notes) && (
              <section className="bg-white border p-6 space-y-4">
                {bid.technical_notes && (
                  <div>
                    <div className="pmc-label mb-1">Technical notes</div>
                    <div className="whitespace-pre-wrap text-sm text-slate-700">{bid.technical_notes}</div>
                  </div>
                )}
                {bid.commercial_notes && (
                  <div>
                    <div className="pmc-label mb-1">Commercial notes</div>
                    <div className="whitespace-pre-wrap text-sm text-slate-700">{bid.commercial_notes}</div>
                  </div>
                )}
              </section>
            )}

            <section className="bg-white border p-6" data-testid="admin-bid-documents">
              <div className="pmc-label mb-3">
                Uploaded documents · {(bid.documents || []).length}
              </div>
              {(bid.documents || []).length === 0 ? (
                <div className="text-sm text-slate-500">The vendor did not attach any documents to this bid.</div>
              ) : (
                <div className="grid gap-4">
                  {bid.documents.map((d, i) => {
                    const url = docUrl(d);
                    const mime = d.mime || "";
                    const isImg = mime.startsWith("image/") || /\.(png|jpe?g|gif|webp|bmp)$/i.test(d.filename || "");
                    const isPdf = mime === "application/pdf" || /\.pdf$/i.test(d.filename || "");
                    return (
                      <div key={i} className="border p-4" data-testid={`admin-bid-doc-${i}`}>
                        <div className="flex items-center justify-between flex-wrap gap-2">
                          <div className="text-sm">
                            <span className="text-[10px] uppercase tracking-widest bg-brand-navy/5 border border-brand-navy/20 text-brand-navy px-2 py-0.5 mr-2">
                              {d.kind || "document"}
                            </span>
                            <span className="font-medium">{d.name || d.filename || `Document ${i + 1}`}</span>
                            {mime && <span className="text-xs text-slate-500 ml-2">· {mime}</span>}
                            {d.size_bytes != null && (
                              <span className="text-xs text-slate-500 ml-2">· {(d.size_bytes / 1024).toFixed(1)} KB</span>
                            )}
                          </div>
                          {url && (
                            <div className="flex gap-2 pmc-no-print">
                              <a href={`${url}${url.includes("?") ? "&" : "?"}download=1`} download rel="noopener"
                                data-testid={`admin-bid-doc-open-${i}`}
                                className="text-[11px] uppercase tracking-widest px-3 py-1.5 bg-brand-navy text-white hover:bg-brand-navy-deep">
                                Download
                              </a>
                              <a href={url} target="_blank" rel="noopener noreferrer"
                                data-testid={`admin-bid-doc-preview-${i}`}
                                className="text-[11px] uppercase tracking-widest px-3 py-1.5 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
                                Preview
                              </a>
                            </div>
                          )}
                          {false && (
                            <div className="flex gap-2 pmc-no-print"><a href={url} download={d.filename || d.name || true}
                                data-testid={`admin-bid-doc-download-${i}`}
                                className="text-[11px] uppercase tracking-widest px-3 py-1.5 border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
                                Download
                              </a>
                            </div>
                          )}
                        </div>
                        {url && isImg && (
                          <img src={url} alt={d.filename || "attachment"}
                            className="mt-3 max-h-96 border" data-testid={`admin-bid-doc-preview-${i}`} />
                        )}
                        {url && isPdf && (
                          <iframe src={url} title={d.filename || `pdf-${i}`}
                            className="mt-3 w-full h-[480px] border pmc-no-print" data-testid={`admin-bid-doc-preview-${i}`} />
                        )}
                      </div>
                    );
                  })}
                </div>
              )}
            </section>

            {Array.isArray(bid.workflow_history) && bid.workflow_history.length > 0 && (
              <section className="bg-white border p-6" data-testid="admin-bid-workflow">
                <div className="pmc-label mb-3">Workflow history</div>
                <ul className="space-y-1 text-sm">
                  {bid.workflow_history.map((w, i) => (
                    <li key={i} className="flex justify-between border-b border-slate-100 py-1.5">
                      <span>
                        <strong>{w.action || w.step}</strong>
                        {w.by && <span className="text-slate-500"> · by {w.by}</span>}
                        {w.notes && <span className="text-slate-500"> · {w.notes}</span>}
                      </span>
                      <span className="text-slate-500 text-xs">{(w.at || "").slice(0, 16).replace("T", " ")}</span>
                    </li>
                  ))}
                </ul>
              </section>
            )}
          </div>
        )}
      </main>
    </div>
  );
}

function F({ label, value, mono }) {
  return (
    <div>
      <div className="text-[10px] uppercase tracking-widest text-slate-500">{label}</div>
      <div className={`text-slate-800 ${mono ? "font-mono text-xs" : ""}`}>{value || "—"}</div>
    </div>
  );
}
