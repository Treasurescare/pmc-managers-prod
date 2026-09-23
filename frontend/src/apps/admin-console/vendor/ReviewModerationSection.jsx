import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { vendorRatingsApi, showApiError } from "@/lib/api";
import { VendorTrustBadge } from "@/components/VendorTrustBadge";

/**
 * v46 — Admin moderation queue for public + peer reviews.
 * Renders as a section inside VendorIntelPanel.
 */
export default function ReviewModerationSection() {
  const [tab, setTab]     = useState("pending");
  const [rows, setRows]   = useState([]);
  const [count, setCount] = useState(0);
  const [busy, setBusy]   = useState(null);

  const load = useCallback(async () => {
    try {
      const status = tab === "all" ? undefined : tab;
      const [list, pc] = await Promise.all([
        vendorRatingsApi.adminList({ status, limit: 200 }),
        vendorRatingsApi.adminPendingCount().catch(() => ({ pending: 0 })),
      ]);
      setRows(list || []);
      setCount(pc.pending ?? 0);
    } catch (e) { showApiError(e); }
  }, [tab]);

  useEffect(() => { load(); }, [load]);

  const moderate = async (row, action) => {
    setBusy(row.id);
    try {
      await vendorRatingsApi.adminModerate(row.id, { action });
      toast.success(action === "approve" ? "Approved" : "Hidden");
      await load();
    } catch (e) { showApiError(e); }
    finally { setBusy(null); }
  };

  const remove = async (row) => {
    // eslint-disable-next-line no-alert
    if (!window.confirm("Delete this review permanently? This cannot be undone.")) return;
    setBusy(row.id);
    try {
      await vendorRatingsApi.adminDelete(row.id);
      toast.success("Deleted");
      await load();
    } catch (e) { showApiError(e); }
    finally { setBusy(null); }
  };

  return (
    <div className="border-t bg-white" data-testid="review-moderation-section">
      <div className="px-3 py-2 border-b flex items-baseline gap-3 flex-wrap">
        <strong className="text-brand-navy">Review moderation</strong>
        <span className="text-xs bg-amber-100 text-amber-800 px-2 py-0.5 uppercase tracking-widest">
          {count} pending
        </span>
        <div className="ml-auto flex gap-1">
          {["pending", "approved", "hidden", "all"].map((t) => (
            <button key={t} onClick={() => setTab(t)}
                    data-testid={`rm-tab-${t}`}
                    className={`text-[11px] uppercase tracking-widest px-2 py-1 border ${tab === t ? "bg-brand-navy text-white border-brand-navy" : "bg-white text-brand-navy border-brand-navy/20"}`}>
              {t}
            </button>
          ))}
        </div>
      </div>
      <div className="w-full overflow-x-auto">
        <table className="w-full text-sm min-w-[860px]">
          <thead className="text-xs text-brand-navy/60 border-b">
            <tr>
              <th className="text-left px-3 py-2">Target</th>
              <th className="text-left px-3 py-2">Reviewer</th>
              <th className="px-3 py-2">Kind</th>
              <th className="px-3 py-2">Score</th>
              <th className="text-left px-3 py-2">Comment</th>
              <th className="px-3 py-2">Status</th>
              <th className="px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} className="border-t align-top"
                  data-testid={`review-row-${r.id}`}>
                <td className="px-3 py-2 font-mono text-xs">{r.vendor_ref}</td>
                <td className="px-3 py-2">
                  <div className="text-xs">{r.reviewer_name || r.reviewer_email}</div>
                  <div className="text-[10px] text-slate-500">{r.reviewer_email}</div>
                </td>
                <td className="px-3 py-2 text-center text-xs capitalize">{(r.reviewer_kind || "").replace("_", " ")}</td>
                <td className="px-3 py-2 text-center font-mono">{r.score_out_of_100}</td>
                <td className="px-3 py-2 max-w-[280px]">
                  <div className="text-xs text-brand-navy whitespace-pre-line">{r.comment || <span className="text-slate-400">—</span>}</div>
                </td>
                <td className="px-3 py-2 text-center">
                  <span className={`text-[10px] uppercase tracking-widest px-2 py-0.5 ${r.status === "approved" ? "bg-emerald-100 text-emerald-800" : r.status === "pending" ? "bg-amber-100 text-amber-800" : "bg-slate-200 text-slate-600"}`}>
                    {r.status}
                  </span>
                </td>
                <td className="px-3 py-2">
                  <div className="flex flex-wrap gap-1 justify-center">
                    {r.status !== "approved" && (
                      <button onClick={() => moderate(r, "approve")} disabled={busy === r.id}
                              data-testid={`rm-approve-${r.id}`}
                              className="text-[10px] uppercase tracking-widest px-2 py-1 bg-emerald-600 text-white disabled:opacity-40">
                        Approve
                      </button>
                    )}
                    {r.status !== "hidden" && (
                      <button onClick={() => moderate(r, "hide")} disabled={busy === r.id}
                              data-testid={`rm-hide-${r.id}`}
                              className="text-[10px] uppercase tracking-widest px-2 py-1 bg-amber-500 text-white disabled:opacity-40">
                        Hide
                      </button>
                    )}
                    <button onClick={() => remove(r)} disabled={busy === r.id}
                            data-testid={`rm-delete-${r.id}`}
                            className="text-[10px] uppercase tracking-widest px-2 py-1 border border-red-500 text-red-600 disabled:opacity-40">
                      Delete
                    </button>
                  </div>
                </td>
              </tr>
            ))}
            {rows.length === 0 && (
              <tr><td colSpan={7} className="p-6 text-center text-slate-500">No reviews in this bucket.</td></tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export function AdminBadgePreview({ vendorRef }) {
  const [agg, setAgg] = useState(null);
  useEffect(() => {
    let cancelled = false;
    vendorRatingsApi.publicAggregate(vendorRef)
      .then((a) => { if (!cancelled) setAgg(a); })
      .catch(() => { if (!cancelled) setAgg(null); });
    return () => { cancelled = true; };
  }, [vendorRef]);
  if (!agg) return null;
  return <VendorTrustBadge tier={agg.badge} score={agg.average_score ?? "—"} count={agg.count} compact testid={`admin-badge-${vendorRef}`} />;
}
