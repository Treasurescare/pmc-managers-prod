import { useNavigate } from "react-router-dom";
import { bidApi, showApiError } from "@/lib/api";
import { useListPager } from "@/components/ListPager";
import { toast } from "sonner";

const STATUS_LABELS = {
  emd_pending: "EMD pending", emd_paid: "EMD paid — Awaits Escrow",
  escrow_accepted: "Escrow accepted — Awaits Admin approval",
  admin_flagged: "Approved — Awaits Certifier",
  certifier_cleared: "Certifier cleared — Awaits Legal",
  legal_cleared: "Legal cleared — Awaits Accounting",
  accounting_cleared: "Accounting cleared — Awaits Committee",
  on_hold: "ON HOLD",
  awarded: "AWARDED", rejected: "Rejected", withdrawn: "Withdrawn", closed: "Closed",
};

const HOLDABLE = ["submitted", "emd_pending", "emd_paid", "escrow_accepted",
                  "admin_flagged", "certifier_review", "certifier_cleared",
                  "legal_review", "legal_cleared", "accounting_review", "accounting_cleared",
                  "committee_review"];

/**
 * BidTable — extracted from BiddingOpsPanel. Renders the bids pipeline table
 * and the per-row action buttons.
 */
export default function BidTable({ bids, onAdminFlag, onReject, onOpenAssign, onOpenSpecialists, onHold, onResume, onSendEmdLink }) {
  const nav = useNavigate();
  const { paged, controls } = useListPager(bids || [], { defaultSize: 20 });
  void bidApi; void showApiError; void toast;
  const rows = paged;
  return (
    <div className="border border-brand-navy/10 bg-white overflow-x-auto" data-testid="bid-table">
      <table className="w-full text-sm">
        <thead className="text-left text-brand-navy/60 text-xs uppercase tracking-wider">
          <tr>
            <th className="px-3 py-2">Bid ref</th><th className="px-3 py-2">Notice</th>
            <th className="px-3 py-2">Vendor</th><th className="px-3 py-2">Price</th>
            <th className="px-3 py-2">EMD</th><th className="px-3 py-2">Status</th>
            <th className="px-3 py-2">Next step (matrix)</th>
            <th className="px-3 py-2">Actions</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((b) => (
            <tr key={b.id} className="border-t border-brand-navy/10" data-testid={`bid-row-${b.bid_ref}`}>
              <td className="px-3 py-2 font-mono text-xs">{b.bid_ref}</td>
              <td className="px-3 py-2 font-mono text-xs">{b.notice_ref}</td>
              <td className="px-3 py-2">{b.company_name || b.vendor_email}</td>
              <td className="px-3 py-2">{b.price_currency} {(b.price_amount || 0).toLocaleString()}</td>
              <td className="px-3 py-2 text-xs">
                {b.emd_currency} {(b.emd_due_amount || 0).toLocaleString()}
                {b.emd_paid_at && <div className="text-emerald-600">✓ paid</div>}
              </td>
              <td className="px-3 py-2 text-xs">{STATUS_LABELS[b.status] || b.status}</td>
              <td className="px-3 py-2 text-xs" data-testid={`bid-active-step-${b.bid_ref}`}>
                {b.active_step?.role_code ? (
                  <>
                    <div className="font-semibold text-brand-navy">{b.active_step.label}</div>
                    <div className="text-brand-navy/50">
                      Role: <span className="font-mono">{b.active_step.role_code}</span>
                      {b.active_step.step_number && b.active_step.total_steps && (
                        <> · step {b.active_step.step_number}/{b.active_step.total_steps}</>
                      )}
                    </div>
                  </>
                ) : (
                  <span className="text-brand-navy/40">{b.active_step?.label || "—"}</span>
                )}
              </td>
              <td className="px-3 py-2 flex gap-1 flex-wrap">
                <button onClick={() => nav(`/admin/bids/${b.id}`)} data-testid={`admin-view-bid-${b.bid_ref}`}
                  className="text-[10px] bg-slate-700 text-white px-2 py-1 rounded hover:bg-slate-900">View</button>
                {!["withdrawn", "rejected", "closed"].includes(b.status) && (
                  <button onClick={() => onOpenSpecialists(b)} data-testid={`assign-specialists-${b.bid_ref}`}
                    className="text-[10px] bg-violet-600 text-white px-2 py-1 rounded hover:bg-violet-700">Assign</button>
                )}
                {b.status === "escrow_accepted" && b.active_step?.role_code === "admin" && (
                  <button onClick={() => onAdminFlag(b)} data-testid={`admin-approve-${b.bid_ref}`}
                    className="text-[10px] bg-emerald-600 text-white px-2 py-1 rounded hover:bg-emerald-700">Approve → Certifier</button>
                )}
                {b.status === "admin_flagged" && !b.assigned_certifier_id && (
                  <button onClick={() => onOpenAssign(b)} data-testid={`assign-certifier-${b.bid_ref}`}
                    className="text-[10px] bg-amber-500 text-white px-2 py-1 rounded hover:bg-amber-600">Assign Certifier</button>
                )}
                {b.status === "emd_pending" && (b.emd_due_amount || 0) > 0 && (
                  <button onClick={() => onSendEmdLink(b)} data-testid={`send-emd-link-${b.bid_ref}`}
                    className="text-[10px] bg-indigo-600 text-white px-2 py-1 rounded hover:bg-indigo-700">Send EMD link</button>
                )}
                {HOLDABLE.includes(b.status) && (
                  <button onClick={() => onHold(b)} data-testid={`admin-hold-${b.bid_ref}`}
                    className="text-[10px] bg-slate-500 text-white px-2 py-1 rounded hover:bg-slate-600">Hold</button>
                )}
                {b.status === "on_hold" && (
                  <button onClick={() => onResume(b)} data-testid={`admin-resume-${b.bid_ref}`}
                    className="text-[10px] bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700">Resume</button>
                )}
                {["emd_paid", "escrow_accepted", "admin_flagged", "on_hold"].includes(b.status) && (
                  <button onClick={() => onReject(b)} data-testid={`admin-reject-${b.bid_ref}`}
                    className="text-[10px] bg-red-600 text-white px-2 py-1 rounded hover:bg-red-700">Reject</button>
                )}
              </td>
            </tr>
          ))}
          {rows.length === 0 && (
            <tr><td colSpan={8} className="px-3 py-8 text-center text-brand-navy/40">No bids yet.</td></tr>
          )}
        </tbody>
      </table>
      {controls}
    </div>
  );
}
