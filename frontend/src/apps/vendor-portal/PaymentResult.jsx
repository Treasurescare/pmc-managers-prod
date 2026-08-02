import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { paymentApi } from "@/lib/api";

export default function PaymentResult({ outcome }) {
  const loc = useLocation();
  const nav = useNavigate();
  const [state, setState] = useState({ label: "Checking…", status: "polling", details: null });

  useEffect(() => {
    if (outcome === "cancel") {
      setState({ label: "Payment cancelled", status: "cancelled", details: null });
      return;
    }
    const params = new URLSearchParams(loc.search);
    const sid = params.get("session_id");
    if (!sid) {
      setState({ label: "No session_id provided", status: "error", details: null });
      return;
    }
    let attempts = 0;
    const timer = setInterval(async () => {
      attempts += 1;
      try {
        const r = await paymentApi.status(sid);
        if (r.payment_status === "paid") {
          clearInterval(timer);
          setState({ label: "EMD received", status: "paid", details: r });
        } else if (r.payment_status === "failed" || r.payment_status === "expired") {
          clearInterval(timer);
          setState({ label: `Payment ${r.payment_status}`, status: r.payment_status, details: r });
        } else if (attempts >= 15) {
          clearInterval(timer);
          setState({ label: "Still processing — refresh in a minute", status: "pending", details: r });
        }
      } catch (e) {
        if (attempts >= 5) {
          clearInterval(timer);
          setState({ label: "Could not confirm status", status: "error", details: null });
        }
      }
    }, 2000);
    return () => clearInterval(timer);
  }, [loc, outcome]);

  const isSuccess = state.status === "paid";
  const iconColor = isSuccess ? "text-green-600" : state.status === "cancelled" ? "text-slate-500" : "text-amber-600";
  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50" data-testid="payment-result">
      <div className="bg-white border rounded-lg p-8 max-w-md w-full text-center">
        <div className={`text-5xl ${iconColor} mb-3`}>{isSuccess ? "✓" : state.status === "cancelled" ? "×" : "…"}</div>
        <h1 className="text-2xl font-serif" data-testid="payment-status">{state.label}</h1>
        {state.details && (
          <div className="mt-3 text-sm text-slate-600">
            {state.details.amount} {state.details.currency}
          </div>
        )}
        <button onClick={() => nav("/vendor")}
          className="mt-6 w-full bg-slate-900 text-white rounded-md py-2.5 text-sm hover:bg-slate-800"
          data-testid="payment-back">Return to dashboard</button>
      </div>
    </div>
  );
}
