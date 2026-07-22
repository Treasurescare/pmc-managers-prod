import { useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import DashboardLayout from "@/components/app/DashboardLayout";
import api, { formatApiError } from "@/lib/api";
import { toast } from "sonner";
import { Check, CreditCard, ArrowRight, ShieldCheck } from "lucide-react";

export default function VendorPayment() {
  const navigate = useNavigate();
  const [busy, setBusy] = useState(false);
  const [profile, setProfile] = useState(null);
  const [sp] = useSearchParams();
  const successSessionId = sp.get("session_id");
  const path = window.location.pathname;

  useEffect(() => {
    api.get("/vendor/profile").then(({ data }) => setProfile(data)).catch((e) => console.warn("Failed to load profile", e));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  // Polling for success
  useEffect(() => {
    if (!path.endsWith("/success") || !successSessionId) return;
    let tries = 0;
    const iv = setInterval(async () => {
      tries += 1;
      try {
        const { data } = await api.get(`/payments/status/${successSessionId}`);
        if (data.payment_status === "paid") {
          clearInterval(iv);
          toast.success("Registration fee received. Thank you.");
          setTimeout(() => navigate("/vendor/profile"), 800);
        }
      } catch (e) { console.warn("Failed to check payment status", e); }
      if (tries > 15) clearInterval(iv);
    }, 2000);
    return () => clearInterval(iv);
  }, [successSessionId, path, navigate]);

  const pay = async () => {
    setBusy(true);
    try {
      const { data } = await api.post("/payments/checkout", { origin_url: window.location.origin });
      window.location.href = data.checkout_url;
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  if (path.endsWith("/success")) {
    return (
      <DashboardLayout title="Payment received" subtitle="Verifying your Stripe payment...">
        <div className="max-w-2xl border p-10">
          <div className="pmc-progress" />
          <div className="pmc-label">Working</div>
          <h2 className="font-serif text-2xl mt-2">We're confirming your payment</h2>
          <p className="text-sm text-muted-foreground mt-4">This usually takes just a moment. You'll be redirected automatically.</p>
        </div>
      </DashboardLayout>
    );
  }

  if (path.endsWith("/cancel")) {
    return (
      <DashboardLayout title="Payment cancelled" subtitle="No charge was made to your card.">
        <div className="max-w-2xl border p-10">
          <p className="text-sm">You can retry at any time.</p>
          <button data-testid="retry-payment" onClick={() => navigate("/vendor/payment")} className="mt-6 bg-primary text-white px-5 py-3 text-sm">
            Retry payment
          </button>
        </div>
      </DashboardLayout>
    );
  }

  if (profile?.registration_fee_paid) {
    return (
      <DashboardLayout title="Registration fee paid" subtitle="You're set. Complete your KYC and submit your profile.">
        <div className="max-w-2xl border p-10 border-l-4 border-success">
          <div className="inline-flex items-center gap-2 text-success"><Check className="h-4 w-4" /><span className="pmc-label text-success">Paid</span></div>
          <h2 className="font-serif text-2xl mt-2">You're good to go</h2>
          <p className="text-sm text-muted-foreground mt-4">Your one-time registration fee has been received. Please continue completing your Pre-Tender Registration Form.</p>
          <button onClick={() => navigate("/vendor/profile")} data-testid="go-to-profile" className="mt-6 inline-flex items-center gap-2 bg-foreground text-white px-5 py-3 text-sm">
            Continue to registration form <ArrowRight className="h-4 w-4" />
          </button>
        </div>
      </DashboardLayout>
    );
  }

  return (
    <DashboardLayout
      title="Registration fee"
      subtitle="A one-time non-refundable fee, as per Section D of the Pre-Tender Registration Form."
    >
      <div className="grid lg:grid-cols-[1fr_360px] gap-8 max-w-5xl">
        <div className="border p-8">
          <div className="pmc-label">Payment</div>
          <h2 className="font-serif text-3xl mt-2 tracking-tight">One-time vendor registration</h2>
          <p className="text-sm text-muted-foreground mt-4">
            PMC charges a small non-refundable fee to serious bidders. It funds compliance review of your KYC file and access to the tender board.
          </p>
          <ul className="mt-6 space-y-3 text-sm">
            <li className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-success" /> Reviewed by PMC compliance within one business day</li>
            <li className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-success" /> Unlimited bids across all open tenders after approval</li>
            <li className="inline-flex items-center gap-2"><ShieldCheck className="h-4 w-4 text-success" /> Encrypted document storage tied to your entity</li>
          </ul>
          <button data-testid="pay-registration-fee" onClick={pay} disabled={busy}
            className="mt-8 bg-primary text-white px-6 py-3 text-sm inline-flex items-center gap-2 hover:-translate-y-0.5 transition-transform disabled:opacity-60">
            <CreditCard className="h-4 w-4" /> {busy ? "Opening Stripe..." : "Pay with Stripe"}
          </button>
          <p className="text-xs text-muted-foreground mt-3 font-mono">Test card: 4242 4242 4242 4242 · any future expiry · any CVC</p>
        </div>

        <aside className="border p-6 border-l-4 border-primary bg-muted/20 h-fit">
          <div className="pmc-label mb-1">Amount</div>
          <div className="font-mono text-3xl">USD 100.00</div>
          <div className="pmc-label mt-4">Type</div>
          <div className="font-mono text-sm">One-time · Non-refundable</div>
          <div className="pmc-label mt-4">Powered by</div>
          <div className="font-mono text-sm">Stripe Checkout</div>
        </aside>
      </div>
    </DashboardLayout>
  );
}
