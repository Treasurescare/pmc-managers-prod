import { useEffect, useState } from "react";
import { extraPayApi } from "@/lib/api";

export default function PayComplete() {
  const p = new URLSearchParams(window.location.search);
  const [s, setS] = useState(null);
  useEffect(() => { const sid = p.get("session_id"); if (sid) { extraPayApi.payStatus(sid).then(setS).catch(() => setS({ payment_status: "unknown" })); } }, []); // eslint-disable-line react-hooks/exhaustive-deps
  const msg = p.get("cancel") ? "Payment cancelled — you can use the link in your email again within 24 hours."
    : !s ? "Checking your payment…"
    : s.payment_status === "paid" ? `Thank you — we received ${String(s.currency || "").toUpperCase()} ${Number(s.amount || 0).toLocaleString()}. A confirmation has been emailed.`
    : "Your payment is still processing. Refresh this page in a moment.";
  return (
    <div data-testid="pay-complete" style={{ minHeight: "60vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "24px" }}>
      <div className="pmc-panel" style={{ padding: "28px", maxWidth: "520px" }}>
        <div className="pmc-eyebrow">PMC Managers</div>
        <h1 style={{ fontSize: "24px", margin: "6px 0 10px" }}>Payment</h1>
        <p data-testid="pay-complete-msg">{msg}</p>
      </div>
    </div>
  );
}
