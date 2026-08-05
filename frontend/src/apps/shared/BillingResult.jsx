/**
 * BillingResult — Stripe redirects here on success/cancel. Polls the backend
 * for the true status until it flips to "paid" (webhook / polling fallback).
 */
import { useEffect, useState, useCallback } from "react";
import { useSearchParams, Link } from "react-router-dom";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";

const API = process.env.REACT_APP_BACKEND_URL;

function StatusCard({ paid, pending, error, tx }) {
  if (paid) {
    return (
      <div className="border-2 border-emerald-500 bg-emerald-50 p-10">
        <div className="pmc-label text-emerald-800">Payment received</div>
        <h1 className="font-display text-3xl text-emerald-900 mt-3">Thank you — you're all set</h1>
        <p className="mt-3 text-sm text-emerald-900/85">
          We've received your payment{tx?.amount ? ` of ${tx.currency?.toUpperCase()} ${tx.amount.toLocaleString()}` : ""}
          {tx?.product_code ? ` for ${tx.product_code}` : ""}.
          A receipt has been queued to your inbox.
        </p>
        <Link to="/" data-testid="billing-home"
              className="mt-6 inline-block px-5 py-2 border-2 border-emerald-700 text-emerald-800 text-xs uppercase tracking-widest hover:bg-emerald-700 hover:text-white">
          Back to the tender board
        </Link>
      </div>
    );
  }
  if (error) {
    return (
      <div className="border-2 border-red-500 bg-red-50 p-10">
        <div className="pmc-label text-red-800">Payment error</div>
        <h1 className="font-display text-3xl text-red-900 mt-3">{error}</h1>
      </div>
    );
  }
  return (
    <div className="border-2 border-brand-navy/20 bg-white p-10" data-testid="billing-pending">
      <div className="pmc-label">Payment in progress</div>
      <h1 className="font-display text-3xl text-brand-navy mt-3">
        {pending ? "Confirming your payment…" : "Loading status…"}
      </h1>
      <p className="text-sm text-brand-navy/70 mt-3">
        Stripe usually confirms within a few seconds. Don't close this window.
      </p>
    </div>
  );
}

export default function BillingResult({ outcome }) {
  const [params] = useSearchParams();
  const sid = params.get("session_id");
  const [state, setState] = useState({ paid: false, pending: false, error: null, tx: null });
  const [attempts, setAttempts] = useState(0);

  const poll = useCallback(async () => {
    if (!sid) { setState((s) => ({ ...s, error: "Missing session_id" })); return; }
    try {
      const r = await fetch(`${API}/api/v1/billing/status/${sid}`);
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      if (d.payment_status === "paid") {
        setState({ paid: true, pending: false, error: null, tx: d });
      } else {
        setState({ paid: false, pending: true, error: null, tx: d });
        setAttempts((a) => a + 1);
      }
    } catch (e) {
      setState({ paid: false, pending: false, error: e.message, tx: null });
    }
  }, [sid]);

  useEffect(() => { poll(); }, [poll]);
  useEffect(() => {
    if (state.paid || state.error || attempts > 30) return;
    const t = setTimeout(poll, 2000);
    return () => clearTimeout(t);
  }, [state, attempts, poll]);

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-3xl mx-auto w-full px-6 lg:px-10 py-16">
        {outcome === "cancel" ? (
          <div className="border-2 border-brand-navy/20 bg-white p-10" data-testid="billing-cancel">
            <div className="pmc-label">Checkout cancelled</div>
            <h1 className="font-display text-3xl text-brand-navy mt-3">No charges made</h1>
            <p className="text-sm text-brand-navy/70 mt-3">
              You cancelled the payment. Come back any time — nothing was billed.
            </p>
            <Link to="/" data-testid="billing-home"
                  className="mt-6 inline-block px-5 py-2 border-2 border-brand-navy text-brand-navy text-xs uppercase tracking-widest hover:bg-brand-navy hover:text-white">
              Back to the tender board
            </Link>
          </div>
        ) : (
          <StatusCard {...state}/>
        )}
      </main>
      <Footer />
    </div>
  );
}
