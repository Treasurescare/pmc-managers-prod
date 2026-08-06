import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { awardsApi, bidApi, formatApiError, BACKEND_URL } from "@/lib/api";

/** Wave 39 — Post-Award document dashboard.
 *
 * Admin picks any awarded bid, sees the auto-generated PO / SLA / Contract
 * (all PDFs), can download each, and hit "Regenerate" if any failed. */
export default function AwardsPanel() {
  const [awardedBids, setAwardedBids] = useState([]);
  const [pickedBidId, setPickedBidId] = useState("");
  const [docs, setDocs] = useState([]);
  const [busy, setBusy] = useState(false);

  const loadBids = useCallback(() => {
    bidApi.listAll({ status: "awarded" }).then((rows) => {
      setAwardedBids(rows || []);
      if (!pickedBidId && rows?.length) setPickedBidId(rows[0].id);
    }).catch((e) => toast.error(formatApiError(e)));
  }, [pickedBidId]);

  const loadDocs = useCallback((bidId) => {
    if (!bidId) return;
    awardsApi.list(bidId).then((d) => setDocs(d.items || []))
      .catch((e) => toast.error(formatApiError(e)));
  }, []);

  useEffect(() => { loadBids(); }, [loadBids]);
  useEffect(() => { loadDocs(pickedBidId); }, [pickedBidId, loadDocs]);

  const regenerate = async () => {
    if (!pickedBidId) return;
    setBusy(true);
    try {
      const r = await awardsApi.regenerate(pickedBidId);
      toast.success(`Regenerated — award ref ${r.award_ref}`);
      loadDocs(pickedBidId);
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const kindLabel = (k) => ({ po: "Purchase Order", sla: "Service Level Agreement", contract: "Contract / LOA" }[k] || k);

  return (
    <div data-testid="admin-awards-panel">
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="text-sm text-brand-navy/70">
          Auto-generated Purchase Order, SLA, and Contract for every awarded bid.
          Documents are drafted the moment the committee awards the bid — download or regenerate below.
        </div>
        <button type="button" onClick={regenerate} disabled={!pickedBidId || busy}
                data-testid="awards-regenerate"
                className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-40">
          {busy ? "Regenerating…" : "Regenerate documents"}
        </button>
      </div>

      <label className="block mb-4">
        <span className="pmc-label">Awarded bid</span>
        <select value={pickedBidId} onChange={(e) => setPickedBidId(e.target.value)}
                data-testid="awards-bid-picker"
                className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
          {awardedBids.length === 0 && <option value="">No awarded bids yet</option>}
          {awardedBids.map((b) => (
            <option key={b.id} value={b.id}>
              {b.bid_ref} · {b.company_name || b.vendor_email} · {b.notice_ref}
            </option>
          ))}
        </select>
      </label>

      <div className="grid gap-4 md:grid-cols-3">
        {["po", "sla", "contract"].map((k) => {
          const d = docs.find((x) => x.kind === k);
          return (
            <div key={k} className="border border-brand-navy/10 bg-white p-5"
                 data-testid={`award-card-${k}`}>
              <div className="pmc-label">{kindLabel(k)}</div>
              {d ? (
                <>
                  <div className="mt-2 text-xs text-brand-navy/60 font-mono">{d.award_ref}</div>
                  {d.po_no && <div className="text-xs text-brand-navy/60 font-mono">PO: {d.po_no}</div>}
                  <div className="text-xs text-brand-navy/60 mt-1">Issued {d.awarded_at?.slice(0, 10)}</div>
                  <div className="text-xs text-brand-navy/50 mt-1">{(d.size_bytes / 1024).toFixed(1)} KB</div>
                  <a href={`${BACKEND_URL}/api/v1/awards/bid/${pickedBidId}/pdf/${k}`}
                     target="_blank" rel="noreferrer"
                     data-testid={`award-download-${k}`}
                     className="inline-block mt-3 text-[11px] font-semibold uppercase tracking-widest px-4 py-2 bg-brand-navy text-white hover:bg-brand-navy-deep">
                    Download PDF
                  </a>
                </>
              ) : (
                <div className="mt-2 text-xs text-brand-navy/40 italic">
                  Not yet generated — click "Regenerate documents" above.
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
