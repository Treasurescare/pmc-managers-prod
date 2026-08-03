const STATUS_LABELS = {
  emd_pending: "EMD pending", emd_paid: "EMD paid — Awaits Escrow",
  escrow_accepted: "Escrow accepted — Awaits Admin flag",
  admin_flagged: "Admin flagged — Awaits Certifier",
  certifier_cleared: "Certifier cleared — Awaits Legal",
  legal_cleared: "Legal cleared — Awaits Accounting",
  accounting_cleared: "Accounting cleared — Awaits Committee",
  awarded: "AWARDED", rejected: "Rejected", withdrawn: "Withdrawn", closed: "Closed",
};

/**
 * BidTable — extracted from BiddingOpsPanel. Renders the bids pipeline table
 * and the per-row action buttons.
 */
export default function BidTable({ bids, onAdminFlag, onReject, onOpenAssign }) {
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
          {bids.map((b) => (
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
                {b.status === "escrow_accepted" && b.active_step?.role_code === "admin" && (
                  <button onClick={() => onAdminFlag(b)} data-testid={`admin-flag-${b.bid_ref}`}
                    className="text-[10px] bg-blue-600 text-white px-2 py-1 rounded hover:bg-blue-700">Flag→Certifier</button>
                )}
                {b.status === "admin_flagged" && !b.assigned_certifier_id && (
                  <button onClick={() => onOpenAssign(b)} data-testid={`assign-certifier-${b.bid_ref}`}
                    className="text-[10px] bg-amber-500 text-white px-2 py-1 rounded hover:bg-amber-600">Assign Certifier</button>
                )}
                {["emd_paid", "escrow_accepted", "admin_flagged"].includes(b.status) && (
                  <button onClick={() => onReject(b)} data-testid={`admin-reject-${b.bid_ref}`}
                    className="text-[10px] bg-red-600 text-white px-2 py-1 rounded hover:bg-red-700">Reject</button>
                )}
              </td>
            </tr>
          ))}
          {bids.length === 0 && (
            <tr><td colSpan={8} className="px-3 py-8 text-center text-brand-navy/40">No bids yet.</td></tr>
          )}
        </tbody>
      </table>
    </div>
  );
}
