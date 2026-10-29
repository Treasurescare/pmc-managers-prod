import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { vendorTenderApi, showApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";
import TenderBuilderPanel from "@/apps/admin-console/TenderBuilderPanel";
import { VendorScopeStrip } from "./VendorScopeStrip";

/**
 * R9 — the FULL PMC tender builder for vendors.
 *
 * Reuses the staff TenderBuilderPanel in `vendorMode` (final action = Submit
 * for PMC review, never Publish). Access + pricing are driven by the Fee
 * Master per country: free when no price is configured, otherwise a paid
 * subscription unlocks the builder. Server-side ownership isolation is the
 * authoritative boundary — this component only reflects it.
 */
export default function VendorTenderBuilderFull() {
  const [sub, setSub] = useState(null);
  const loadSub = useCallback(
    () => vendorTenderApi.subscription().then(setSub).catch(() => {}), []);

  useEffect(() => {
    loadSub();
    const params = new URLSearchParams(window.location.search);
    const sid = params.get("sub_session");
    if (sid) {
      vendorTenderApi.subStatus(sid).then((s) => {
        if (s.payment_status === "paid") {
          toast.success("Subscription active — the full tender builder is unlocked.");
          loadSub();
        }
        window.history.replaceState({}, "", "/vendor/tender-builder");
      }).catch(() => {});
    }
    if (params.get("sub_cancel")) {
      toast("Subscription payment cancelled");
      window.history.replaceState({}, "", "/vendor/tender-builder");
    }
    const fsid = params.get("fee_session");
    if (fsid) {
      vendorTenderApi.feeStatus(fsid).then((s) => {
        if (s.payment_status === "paid") toast.success("Payment received — the fee for this tender is paid.");
        else toast("Payment is still processing — refresh in a moment.");
        window.history.replaceState({}, "", "/vendor/tender-builder");
      }).catch(() => {});
    }
    if (params.get("fee_cancel")) {
      toast("Fee payment cancelled");
      window.history.replaceState({}, "", "/vendor/tender-builder");
    }
  }, [loadSub]);

  const subscribe = async () => {
    try {
      const r = await vendorTenderApi.subCheckout(window.location.origin);
      window.location.href = r.checkout_url;
    } catch (e) { showApiError(e); }
  };

  // Priced subscription that is not active → the builder is locked behind payment.
  const gated = sub && sub.required && !sub.active;

  return (
    <div data-testid="vendor-tender-builder" data-pmc-e-page="vendor-tender-builder">
      <VendorPortalChrome active="/vendor/tender-builder">
        <div style={{ padding: "8px 4px 16px" }}>
          {sub && (
            <div className="pmc-panel" data-testid="vendor-tb-entitlement"
                 style={{ padding: "12px 16px", marginBottom: "14px", display: "flex",
                          justifyContent: "space-between", alignItems: "center",
                          gap: "12px", flexWrap: "wrap" }}>
              <div>
                <div className="pmc-eyebrow" style={{ marginBottom: "2px" }}>Tender builder access</div>
                <div style={{ fontSize: "14px", fontWeight: 600 }} data-testid="vendor-tb-access-state">
                  {sub.free
                    ? "Included free for approved vendors"
                    : sub.active
                      ? `Subscription active${sub.expires_at ? ` — renews ${String(sub.expires_at).slice(0, 10)}` : ""}`
                      : `Subscription required — ${sub.price?.currency?.toUpperCase()} ${sub.price?.amount} / ${sub.price?.period_days} days`}
                </div>
                <div className="pmc-muted" style={{ fontSize: "12px", marginTop: "2px" }}>
                  Every tender you submit is reviewed by a PMC officer before it goes live.
                  You cannot bid on a tender you prepared.
                </div>
              </div>
              {!sub.free && !sub.active && (
                <button className="pmc-btn pmc-btn--primary" data-testid="vendor-subscribe-btn" onClick={subscribe}>
                  Subscribe &amp; pay
                </button>
              )}
            </div>
          )}

          {gated ? (
            <div className="pmc-panel" style={{ padding: "28px", textAlign: "center" }} data-testid="vendor-sub-gate">
              <div className="pmc-eyebrow" style={{ marginBottom: "6px" }}>Subscription required</div>
              <div style={{ fontSize: "20px", fontWeight: 700, marginBottom: "4px" }}>
                {sub.price?.currency?.toUpperCase()} {sub.price?.amount}
                <span className="pmc-muted" style={{ fontSize: "13px" }}> / {sub.price?.period_days} days</span>
              </div>
              <p className="pmc-muted" style={{ fontSize: "13px", marginBottom: "16px" }}>
                Subscribe to unlock the full PMC tender builder.
              </p>
              <button className="pmc-btn pmc-btn--primary" data-testid="vendor-subscribe-gate-btn" onClick={subscribe}>
                Subscribe &amp; pay
              </button>
            </div>
          ) : (
            <div data-testid="vendor-full-builder">
              <VendorScopeStrip />
              <TenderBuilderPanel vendorMode />
            </div>
          )}
        </div>
      </VendorPortalChrome>
    </div>
  );
}
