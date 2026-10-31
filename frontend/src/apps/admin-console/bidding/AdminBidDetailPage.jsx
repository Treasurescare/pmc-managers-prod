import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { api, publicApi, showApiError, BACKEND_URL } from "@/lib/api";
import { BidOpeningPanel } from "./BidOpeningPanel";

/**
 * v51ba — full-page admin bid detail. Shows the ENTIRE vendor submission
 * plus a dedicated Award Record panel with lifecycle sign-offs and
 * printable Award Letter / Procurement Contract.
 */
export default function AdminBidDetailPage() {
  const { bidId } = useParams();
  const nav = useNavigate();
  const [bid, setBid] = useState(null);
  const [notice, setNotice] = useState(null);
  const [award, setAward] = useState(null);
  const [err, setErr] = useState("");
  const [deleting, setDeleting] = useState(false);

  const isOrphan = bid && !bid.envelope_state && (
    (!bid.price_amount || Number(bid.price_amount) <= 0)
    && (!bid.documents || bid.documents.length === 0)
    && Number(bid.emd_paid_amount || 0) <= 0
    && ["draft", "submitted", "emd_pending"].includes(bid.status)
  );

  const deleteOrphan = async () => {
    if (!window.confirm(`Delete orphan bid ${bid.bid_ref}? This is permanent and only works because the bid has no price, no documents and no payment.`)) return;
    setDeleting(true);
    try {
      await api.delete(`/api/v1/bids/admin/${bidId}`);
      nav("/admin?tab=bidding");
    } catch (e) {
      showApiError(e);
    } finally {
      setDeleting(false);
    }
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const b = (await api.get(`/api/v1/bids/admin/${bidId}`)).data;
        if (cancelled) return;
        setBid(b);
        // Notice context is best-effort.
        try {
          const n = await publicApi.getNotice(b.notice_ref);
          if (!cancelled) setNotice(n);
        } catch { /* ignore */ }
        // Award summary only when the bid is awarded.
        if (b.status === "awarded" || b.awarded_at) {
          try {
            const a = (await api.get(`/api/v1/awards/bid/${bidId}/summary`)).data;
            if (!cancelled) setAward(a);
          } catch { /* non-fatal */ }
        }
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

  const openPrintView = (kind) => {
    // Open auth-protected HTML in a new tab. Backend reads the httpOnly
    // auth cookie, so a plain window.open works for admin users.
    const base = BACKEND_URL || "";
    const url = `${base}/api/v1/awards/bid/${bidId}/${kind}.html`;
    window.open(url, "_blank", "noopener,noreferrer");
  };

  const downloadPdf = async (kind) => {
    try {
      const path = kind === "award-letter"
        ? `/api/v1/awards/bid/${bidId}/award-letter.pdf`
        : `/api/v1/awards/bid/${bidId}/contract.pdf`;
      const res = await api.get(path, { responseType: "blob" });
      const blob = new Blob([res.data], { type: "application/pdf" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = `${award?.award_ref || "award"}-${kind}.pdf`;
      document.body.appendChild(a);
      a.click();
      a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 2000);
    } catch (e) {
      showApiError(e);
    }
  };

  const fmtTs = (v) => (v || "").slice(0, 19).replace("T", " ");

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
        <div className="space-y-6" data-testid="admin-bid-detail-wrap">
            {bid.envelope_state && bid.envelope_state !== "commercial_open" && (
              <section className="border border-brand-navy/30 bg-brand-navy/5 p-4 text-sm" data-testid="admin-bid-sealed-banner">
                <div className="pmc-label">{bid.envelope_state === "sealed" ? "Sealed bid" : "Commercial envelope sealed"}</div>
                <div className="text-brand-navy/80 mt-1">
                  {bid.envelope_state === "sealed"
                    ? `The technical and commercial envelopes (${bid.sealed_documents_count || 0} file(s)) and the price are encrypted. Nobody can see them until every committee member approves the opening on the bid opening date.`
                    : "The price and commercial documents stay encrypted until every committee member approves the commercial opening."}
                </div>
              </section>
            )}
            {bid.envelope_state && <BidOpeningPanel noticeRef={bid.notice_ref} />}
            {isOrphan && (
              <section className="border border-red-300 bg-red-50 p-5" data-testid="admin-bid-orphan-banner">
                <div className="flex items-start justify-between gap-4 flex-wrap">
                  <div>
                    <div className="pmc-label text-red-900">Orphan bid detected</div>
                    <div className="text-sm text-red-900 mt-1">
                      This bid has no quoted price, no documents and no EMD paid.
                      Delete to clear the queue — the vendor can re-submit cleanly.
                    </div>
                  </div>
                  <button onClick={deleteOrphan} disabled={deleting}
                          data-testid="admin-bid-delete-orphan"
                          className="px-4 py-2 text-xs uppercase tracking-widest bg-red-700 text-white hover:bg-red-800 disabled:opacity-50">
                    {deleting ? "Deleting…" : "Delete orphan bid"}
                  </button>
                </div>
              </section>
            )}

            {/* v51ba — Award Record panel (awarded bids only) */}
            {award && award.is_awarded && (
              <section className="bg-white border border-emerald-300 p-6" data-testid="admin-bid-award-record">
                <div className="flex items-center justify-between flex-wrap gap-3 mb-4">
                  <div>
                    <div className="pmc-label text-emerald-700">Award record</div>
                    <div className="font-display text-xl text-brand-navy mt-1" data-testid="admin-bid-award-ref">
                      {award.award_ref || "—"}
                      {award.po_no && <span className="text-xs text-slate-500 ml-3 font-mono">PO · {award.po_no}</span>}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2 pmc-no-print">
                    <button onClick={() => openPrintView("award-letter")}
                            data-testid="admin-bid-print-award-letter"
                            className="px-3 py-1.5 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
                      Print Award Letter
                    </button>
                    <button onClick={() => downloadPdf("award-letter")}
                            data-testid="admin-bid-pdf-award-letter"
                            className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy/5">
                      Download PDF
                    </button>
                    <button onClick={() => openPrintView("contract")}
                            data-testid="admin-bid-print-contract"
                            className="px-3 py-1.5 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
                      Print Contract
                    </button>
                    <button onClick={() => downloadPdf("contract")}
                            data-testid="admin-bid-pdf-contract"
                            className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy/5">
                      Download PDF
                    </button>
                  </div>
                </div>

                <div className="grid gap-4 md:grid-cols-3 text-sm" data-testid="admin-bid-award-tender">
                  <F label="Tender ref" value={award.tender?.notice_ref} mono />
                  <F label="Tender title" value={award.tender?.title} />
                  <F label="Delivery country" value={award.tender?.delivery_country} />
                  <F label="Tender opened" value={fmtTs(award.tender?.published_at)} />
                  <F label="Submission deadline" value={fmtTs(award.tender?.submission_deadline)} />
                  <F label="Bid submitted" value={fmtTs(award.winner?.submitted_at)} />
                  <F label="Technical cleared" value={fmtTs(award.winner?.technical_cleared_at)} />
                  <F label="Financial opened" value={fmtTs(award.winner?.financial_opened_at)} />
                  <F label="Awarded at" value={fmtTs(award.awarded_at)} />
                </div>

                <div className="mt-5 border-t pt-4 grid gap-4 md:grid-cols-3 text-sm" data-testid="admin-bid-award-winner">
                  <F label="Winning vendor" value={award.winner?.company_name} />
                  <F label="Vendor ref" value={award.winner?.vendor_ref} mono />
                  <F label="Vendor email" value={award.winner?.vendor_email} mono />
                  <F label="Awarded price"
                     value={`${award.winner?.price_currency || ""} ${(award.winner?.price_amount ?? 0).toLocaleString()}`} />
                  <F label="Awarded by" value={award.awarded_by} />
                </div>

                <div className="mt-5 border-t pt-4" data-testid="admin-bid-award-signoffs">
                  <div className="pmc-label mb-2">Lifecycle sign-offs</div>
                  <ul className="divide-y divide-slate-100">
                    {(award.signoffs || []).map((s) => (
                      <li key={s.key} className="py-2 flex items-center justify-between gap-3 text-sm"
                          data-testid={`admin-bid-signoff-${s.key}`}>
                        <div>
                          <span className="font-medium text-slate-800">{s.label}</span>
                          {s.by && <span className="text-slate-500"> · {s.by}</span>}
                          {s.notes && <span className="text-slate-500 italic"> — {s.notes}</span>}
                        </div>
                        <div className="text-xs">
                          {s.signed ? (
                            <span className="text-slate-500">{fmtTs(s.at)}</span>
                          ) : (
                            <span className="text-amber-700 uppercase tracking-widest text-[10px]">pending</span>
                          )}
                        </div>
                      </li>
                    ))}
                  </ul>

                  {(award.escrow || []).length > 0 && (
                    <div className="mt-4 bg-slate-50 border border-slate-200 p-3">
                      <div className="pmc-label mb-2">Escrow ledger &amp; dual sign-off</div>
                      <ul className="space-y-2 text-sm">
                        {award.escrow.map((tx, i) => (
                          <li key={i} className="border-b border-slate-100 pb-2"
                              data-testid={`admin-bid-escrow-tx-${i}`}>
                            <div className="flex justify-between flex-wrap gap-2">
                              <span className="font-medium text-slate-800">
                                {tx.currency} {Number(tx.amount || 0).toLocaleString()}
                                <span className="text-xs text-slate-500 ml-2">· {tx.status}</span>
                              </span>
                              {tx.released_at && (
                                <span className="text-xs text-slate-500">
                                  Released {fmtTs(tx.released_at)} → {tx.released_to}
                                </span>
                              )}
                            </div>
                            <div className="text-xs text-slate-600 mt-1 grid md:grid-cols-2 gap-1">
                              <div>PMC: {tx.pmc_officer || "—"}
                                {tx.pmc_signed_at && <span className="text-slate-500"> · {fmtTs(tx.pmc_signed_at)}</span>}
                              </div>
                              <div>Escrow: {tx.escrow_officer || "—"}
                                {tx.escrow_signed_at && <span className="text-slate-500"> · {fmtTs(tx.escrow_signed_at)}</span>}
                              </div>
                            </div>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}

                  {(award.envelopes || []).length > 0 && (
                    <div className="mt-4" data-testid="admin-bid-award-envelopes">
                      <div className="pmc-label mb-2">DocuSign envelopes</div>
                      <ul className="space-y-1 text-sm">
                        {award.envelopes.map((e) => (
                          <li key={e.envelope_id}
                              className="flex justify-between gap-2 border-b border-slate-100 py-1.5">
                            <span>
                              <span className="font-mono text-xs text-slate-500">{(e.kind || "")}·{(e.sub_kind || "")}</span>
                              <span className="ml-2">{e.signer_name || e.signer_email || "—"}</span>
                              {e.archived && <span className="ml-2 text-[10px] uppercase tracking-widest text-slate-500">archived</span>}
                            </span>
                            <span className="text-xs">
                              <span className={e.status === "completed" ? "text-emerald-700" : "text-amber-700"}>
                                {e.status || "—"}
                              </span>
                              {e.completed_at && <span className="text-slate-500 ml-2">{fmtTs(e.completed_at)}</span>}
                            </span>
                          </li>
                        ))}
                      </ul>
                    </div>
                  )}
                </div>
              </section>
            )}

            <section className="bg-white border p-6">
              <div className="pmc-label mb-3">Submission</div>
              <div className="grid gap-4 md:grid-cols-3 text-sm">
                <F label="Notice" value={bid.notice_ref} mono />
                <F label="Notice title" value={notice?.title || "—"} />
                <F label="Status" value={bid.status} />
                <F label="Submitted at" value={fmtTs(bid.submitted_at || bid.created_at)} />
                <F label="Vendor" value={bid.company_name || "—"} />
                <F label="Vendor ref" value={bid.vendor_ref || "—"} mono />
                {bid.partner_code && <F label="Partner" value={`${bid.partner_code}${bid.partner_name ? ` · ${bid.partner_name}` : ""}`} mono />}
                <F label="Vendor email" value={bid.vendor_email || "—"} mono />
              </div>
            </section>

            <section className="bg-white border p-6" data-testid="admin-bid-commercial">
              <div className="pmc-label mb-3">Commercial</div>
              <div className="grid gap-4 md:grid-cols-4 text-sm">
                <F label="Quoted price" value={bid.commercial_redacted ? "Sealed until opening" : `${bid.price_currency || ""} ${(bid.price_amount ?? 0).toLocaleString()}`} />
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
                Uploaded documents · {bid.envelope_state === "sealed" ? `${bid.sealed_documents_count || 0} sealed` : (bid.documents || []).length}
              </div>
              {(bid.documents || []).length === 0 ? (
                <div className="text-sm text-slate-500">{bid.envelope_state === "sealed" ? `${bid.sealed_documents_count || 0} file(s) sealed until the committee opens the envelopes.` : "The vendor did not attach any documents to this bid."}</div>
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
                        </div>
                        {url && isImg && (
                          <img src={url} alt={d.filename || "attachment"}
                            className="mt-3 max-h-96 border" data-testid={`admin-bid-doc-img-${i}`} />
                        )}
                        {url && isPdf && (
                          <iframe src={url} title={d.filename || `pdf-${i}`}
                            className="mt-3 w-full h-[480px] border pmc-no-print" data-testid={`admin-bid-doc-pdf-${i}`} />
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
                        <span className="text-slate-500"> · {w.role}</span>
                        {w.by && <span className="text-slate-500"> · by {w.by}</span>}
                        {w.notes && <span className="text-slate-500"> · {w.notes}</span>}
                      </span>
                      <span className="text-slate-500 text-xs">{fmtTs(w.at)}</span>
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
