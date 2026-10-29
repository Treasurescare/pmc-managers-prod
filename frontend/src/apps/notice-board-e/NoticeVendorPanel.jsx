import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "sonner";
import { extraPayApi, showApiError } from "@/lib/api";

const money = (c, n) => `${(c || "").toUpperCase()} ${Number(n || 0).toLocaleString(undefined, { maximumFractionDigits: 2 })}`;

export const NoticeVendorPanel = ({ noticeRef }) => {
  const [cat, setCat] = useState(null);
  const [doc, setDoc] = useState(null);
  const load = () => {
    extraPayApi.categoryInterest(noticeRef).then(setCat).catch(() => {});
    extraPayApi.docFee(noticeRef).then(setDoc).catch(() => {});
  };
  useEffect(() => {
    const p = new URLSearchParams(window.location.search);
    const sid = p.get("session_id");
    if (sid && p.get("doc_paid")) {
      extraPayApi.docFeeStatus(sid).then((s) => {
        if (s.payment_status === "paid") toast.success("Document fee paid — you can now download the tender pack.");
        window.history.replaceState({}, "", window.location.pathname);
        load();
      }).catch(() => load());
    } else load();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [noticeRef]);
  const pay = async () => {
    try { const r = await extraPayApi.docFeeCheckout(noticeRef); window.location.href = r.checkout_url; } catch (e) { showApiError(e); }
  };
  const showCat = cat && !cat.registered;
  const showDoc = doc && doc.required;
  if (!showCat && !showDoc) return null;
  return (
    <div style={{ display: "grid", gap: "10px", margin: "12px 0" }}>
      {showCat && (
        <div className="pmc-panel" data-testid="notice-category-upsell" style={{ padding: "12px 16px", borderLeft: "4px solid var(--warning, #b7791f)", color: "#1b2430", background: "#fff8e6" }}>
          <b>This tender is in “{cat.category}”, which is not one of your registered categories.</b>
          <div style={{ fontSize: "13px", marginTop: "4px" }}>
            Registration is free for one category; every additional category needs a payment. Add it, pay the fee, and you can bid once PMC approves it.
            We've also sent this to your notifications and email.
          </div>
          {cat.pending_request
            ? <div style={{ fontSize: "13px", marginTop: "6px" }} data-testid="notice-category-pending">Your request for this category is {cat.pending_request.payment_status === "unpaid" ? "waiting for payment" : "with PMC for approval"}. <Link to="/vendor/categories">Open My categories</Link></div>
            : <Link to={`/vendor/categories?add=${encodeURIComponent(cat.category)}`} className="pmc-btn pmc-btn--primary pmc-btn--sm" style={{ marginTop: "8px" }} data-testid="notice-category-add">Add this category</Link>}
        </div>
      )}
      {showDoc && (
        <div className="pmc-panel" data-testid="notice-doc-fee" style={{ padding: "12px 16px", color: "#1b2430", background: "#ffffff" }}>
          {doc.paid
            ? <span data-testid="notice-doc-fee-paid">✓ Document fee paid — download the pack any number of times.</span>
            : <><b>Tender document download fee: {money(doc.currency, doc.amount)}</b> — pay once to download any number of times.
              <button type="button" onClick={pay} className="pmc-btn pmc-btn--primary pmc-btn--sm" style={{ marginLeft: "10px" }} data-testid="notice-doc-fee-pay">Pay & unlock</button></>}
        </div>
      )}
    </div>
  );
};
