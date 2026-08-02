import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { sandboxPayApi, formatApiError } from "@/lib/api";

const GATEWAY_LABELS = {
  paypal: { name: "PayPal", tagline: "Sandbox — no real charge", color: "#003087" },
  kaspi:  { name: "Kaspi Pay", tagline: "Kazakhstan — Sandbox", color: "#F14635" },
};

export default function SandboxCheckout() {
  const loc = useLocation();
  const nav = useNavigate();
  const [session, setSession] = useState(null);
  const [busy, setBusy] = useState(false);
  const params = new URLSearchParams(loc.search);
  const sid = params.get("session_id");
  const method = params.get("method") || "paypal";
  const g = GATEWAY_LABELS[method] || GATEWAY_LABELS.paypal;

  useEffect(() => {
    if (!sid) return;
    sandboxPayApi.session(sid).then(setSession).catch(() => nav("/vendor"));
  }, [sid, nav]);

  const confirm = async () => {
    setBusy(true);
    try {
      await sandboxPayApi.confirm(sid);
      toast.success("Payment received (sandbox)");
      nav(`/vendor/payment/success?session_id=${sid}`);
    } catch (err) {
      toast.error(formatApiError(err));
      setBusy(false);
    }
  };

  if (!session) return <div className="p-10 text-slate-500">Loading sandbox session…</div>;
  const isPaid = session.payment_status === "paid";
  return (
    <div className="min-h-screen bg-slate-100 flex items-center justify-center p-6" data-testid="sandbox-checkout">
      <div className="max-w-md w-full bg-white rounded-lg overflow-hidden shadow-lg">
        <div className="text-white p-5 text-center" style={{ background: g.color }}>
          <div className="text-2xl font-bold">{g.name}</div>
          <div className="text-xs opacity-80 mt-1">{g.tagline}</div>
        </div>
        <div className="p-6 space-y-3 text-sm">
          <div className="bg-amber-50 border border-amber-200 text-amber-800 text-xs p-2 rounded">
            <strong>Sandbox mode:</strong> no real funds are moved. Confirming below advances the
            bid to <code>emd_paid</code> so the escrow, certifier, legal and accounting stages
            can be demonstrated end-to-end.
          </div>
          <div className="flex justify-between text-slate-600">
            <span>Bid</span><span className="font-mono">{session.bid_ref}</span>
          </div>
          <div className="flex justify-between text-slate-600">
            <span>Tender</span><span className="font-mono">{session.notice_ref}</span>
          </div>
          <div className="flex justify-between text-slate-600">
            <span>Amount</span>
            <strong>{session.currency} {(session.amount || 0).toLocaleString()}</strong>
          </div>
          <div className="pt-3">
            {isPaid ? (
              <div className="text-emerald-700 text-center text-sm">Already paid ✓</div>
            ) : (
              <button onClick={confirm} disabled={busy}
                className="w-full py-3 text-white font-semibold text-sm disabled:opacity-60"
                style={{ background: g.color }}
                data-testid="sandbox-confirm">
                {busy ? "Processing…" : `Confirm payment via ${g.name}`}
              </button>
            )}
            <button onClick={() => nav("/vendor")}
              className="w-full mt-2 py-2 text-xs text-slate-500 hover:underline"
              data-testid="sandbox-cancel">Cancel and return to dashboard</button>
          </div>
        </div>
      </div>
    </div>
  );
}
