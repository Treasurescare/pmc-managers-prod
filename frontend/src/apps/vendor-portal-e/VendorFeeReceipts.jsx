import { useEffect, useState } from "react";
import { vendorTenderApi } from "@/lib/api";

const PURPOSE = { tender_start: "Tender start fee", tender_fee: "Tender fee" };

export const VendorFeeReceipts = () => {
  const [rows, setRows] = useState(null);
  useEffect(() => { vendorTenderApi.receipts().then((r) => setRows(r.items || [])).catch(() => setRows([])); }, []);
  if (!rows) return null;
  return (
    <section className="pmc-panel" data-testid="vendor-fee-receipts" style={{ margin: "0 0 18px", padding: "14px 16px" }}>
      <div className="pmc-eyebrow" style={{ marginBottom: "8px" }}>Tender fee receipts</div>
      {rows.length === 0 ? <div className="pmc-muted" style={{ fontSize: "13px" }} data-testid="vendor-fee-receipts-empty">No tender fees paid yet.</div> : (
        <table style={{ width: "100%", fontSize: "13px" }}>
          <thead><tr className="pmc-muted" style={{ textAlign: "left" }}><th>Receipt</th><th>Date</th><th>For</th><th>Items</th><th style={{ textAlign: "right" }}>Total</th></tr></thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id} data-testid={`vendor-receipt-${r.receipt_no}`}>
                <td style={{ padding: "6px 8px 6px 0", fontFamily: "monospace" }}>{r.receipt_no}</td>
                <td>{String(r.paid_at || "").slice(0, 10)}</td>
                <td>{PURPOSE[r.purpose] || r.purpose}{r.tender_name ? ` · ${r.tender_name}` : ""}{r.category ? ` · ${r.category}` : ""}</td>
                <td>{(r.lines || []).map((l) => l.name).join(", ")}</td>
                <td style={{ textAlign: "right", fontWeight: 600 }}>{r.currency} {Number(r.total || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
};
