import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import { vendorApi, paymentApi, showApiError } from "@/lib/api";

/**
 * v47b — deep link target for the admin-triggered "EMD payment link" email.
 * Route: /vendor/bids/:bidId/pay
 * Flow: verify session → create Stripe checkout → hard-redirect to Stripe.
 * If the vendor isn't signed in, bounce to login with a `next` state.
 */
export default function BidPayRedirect() {
  const { bidId } = useParams();
  const nav = useNavigate();
  const [error, setError] = useState("");

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const me = await vendorApi.me();
        if (cancelled) return;
        if (me.must_change_password) {
          return nav("/vendor/change-password", { state: { next: `/vendor/bids/${bidId}/pay` } });
        }
        const chk = await paymentApi.checkout(bidId, window.location.origin);
        if (cancelled) return;
        window.location.href = chk.checkout_url;
      } catch (e) {
        if (cancelled) return;
        if (e?.response?.status === 401) {
          return nav("/vendor/login", { state: { next: `/vendor/bids/${bidId}/pay` } });
        }
        setError(e?.response?.data?.detail || "Could not start the EMD payment. Please pay from Vendor Portal → My bids instead.");
        showApiError(e);
      }
    })();
    return () => { cancelled = true; };
  }, [bidId, nav]);

  // v50v — friendlier copy for the common "already settled" case so vendors
  // who click Pay on an emd_paid bid don't hit a raw backend error.
  const friendlyError = (() => {
    if (!error) return "";
    if (/not payable|already paid|no emd due/i.test(error)) {
      return "This EMD is already settled (or not due on this bid). Nothing left to pay — you're all set.";
    }
    return error;
  })();

  return (
    <div className="min-h-screen flex items-center justify-center bg-brand-parchment p-6"
         data-testid="bid-pay-redirect">
      <div className="bg-white border p-8 max-w-md w-full text-center space-y-4">
        {!error ? (
          <>
            <div className="w-10 h-10 border-2 border-brand-navy border-t-transparent rounded-full animate-spin mx-auto" />
            <div className="text-sm text-brand-navy">
              Opening secure EMD payment for bid <span className="font-mono">{bidId}</span>…
            </div>
            <div className="text-xs text-slate-500">You'll be redirected to Stripe in a moment.</div>
          </>
        ) : (
          <>
            <div className="text-sm text-red-700" data-testid="bid-pay-error">{friendlyError}</div>
            <div className="flex gap-2 justify-center">
              <Link to="/vendor/mybids" className="inline-block px-4 py-2 text-xs bg-brand-navy text-white"
                    data-testid="bid-pay-fallback">
                Back to My bids
              </Link>
              <Link to="/vendor/emd" className="inline-block px-4 py-2 text-xs border border-brand-navy text-brand-navy"
                    data-testid="bid-pay-emd-link">
                EMD &amp; payments
              </Link>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
