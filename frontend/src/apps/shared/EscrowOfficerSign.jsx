/**
 * EscrowOfficerSign — magic-link portal for the non-PMC escrow officer.
 * They land here from an emailed link, see the pending transactions on their
 * joint account, and can sign off on the intended release action — WITHOUT
 * needing a full staff account. See backend/routers/escrow.py `magic_*` routes.
 */
import { useCallback, useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { toast } from "sonner";
import TopBar from "@/apps/shared/TopBar";
import Footer from "@/apps/shared/Footer";

const API = process.env.REACT_APP_BACKEND_URL;

const ACTIONS = [
  { v: "release_to_contractor", l: "Release → Contractor (winning vendor)" },
  { v: "release_to_vendor",     l: "Refund → Vendor (bid did not win)" },
  { v: "forfeit",               l: "Forfeit (withdrawal / mis-declaration)" },
];

function TransactionRow({ tx, myEmail, mySide, onSign }) {
  const alreadySigned = tx.signatures && tx.signatures[mySide];
  const [action, setAction] = useState(alreadySigned?.action || "release_to_contractor");
  const [comment, setComment] = useState("");
  const [busy, setBusy] = useState(false);

  const sign = async () => {
    setBusy(true);
    try { await onSign(tx.id, action, comment); }
    finally { setBusy(false); }
  };

  const other = mySide === "pmc" ? "escrow_institution" : "pmc";
  const otherSigned = tx.signatures && tx.signatures[other];

  return (
    <div className="border-2 border-brand-navy/15 bg-white p-6 space-y-4"
         data-testid={`escrow-magic-tx-${tx.id}`}>
      <div className="flex flex-wrap items-baseline justify-between gap-3">
        <div>
          <div className="pmc-label">Escrow transaction</div>
          <h3 className="font-display text-xl text-brand-navy mt-1">
            {(tx.currency || "USD").toUpperCase()} {Number(tx.amount || 0).toLocaleString()}
          </h3>
          <div className="text-xs text-brand-navy/60 mt-1 font-mono">
            {tx.bid_ref || "—"} · {tx.notice_ref || "—"} · vendor {tx.vendor_ref || "—"}
          </div>
        </div>
        <span className="text-xs px-2 py-1 border border-brand-navy/20 uppercase tracking-widest">
          {tx.status}
        </span>
      </div>

      <div className="grid gap-2 sm:grid-cols-2 text-sm">
        <div className={`border p-3 ${alreadySigned ? "border-emerald-500 bg-emerald-50" : "border-brand-navy/15"}`}>
          <div className="pmc-label">Your sign-off ({mySide})</div>
          <div className="mt-1">
            {alreadySigned
              ? <>✓ Signed {alreadySigned.action?.replace(/_/g, " ")} at {alreadySigned.signed_at?.slice(0, 16)}</>
              : "Awaiting your signature"}
          </div>
        </div>
        <div className={`border p-3 ${otherSigned ? "border-emerald-500 bg-emerald-50" : "border-brand-navy/15"}`}>
          <div className="pmc-label">Other party ({other})</div>
          <div className="mt-1">
            {otherSigned
              ? <>✓ Signed {otherSigned.action?.replace(/_/g, " ")} at {otherSigned.signed_at?.slice(0, 16)}</>
              : "Awaiting"}
          </div>
        </div>
      </div>

      <div className="grid gap-3">
        <label>
          <div className="pmc-label">Intended action</div>
          <select value={action} onChange={(e) => setAction(e.target.value)}
                  data-testid={`escrow-magic-action-${tx.id}`}
                  className="mt-1 w-full border border-brand-navy/20 px-3 py-2 bg-white">
            {ACTIONS.map((a) => <option key={a.v} value={a.v}>{a.l}</option>)}
          </select>
        </label>
        <label>
          <div className="pmc-label">Comment (optional)</div>
          <textarea value={comment} onChange={(e) => setComment(e.target.value)}
                    data-testid={`escrow-magic-comment-${tx.id}`}
                    rows={2}
                    className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/>
        </label>
      </div>

      <div className="flex justify-end">
        <button onClick={sign} disabled={busy}
                data-testid={`escrow-magic-sign-${tx.id}`}
                className="px-5 py-2 bg-brand-navy text-white text-xs uppercase tracking-widest hover:bg-brand-navy-deep disabled:opacity-50">
          {busy ? "Signing…" : (alreadySigned ? "Update signature" : "Sign this transaction")}
        </button>
      </div>
      <p className="text-[11px] text-brand-navy/50">
        Signing with <span className="font-mono">{myEmail}</span>. Both officers must sign the SAME action
        for admin to trigger the release.
      </p>
    </div>
  );
}

export default function EscrowOfficerSign() {
  const { token } = useParams();
  const [ctx, setCtx] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/escrow/magic/${token}`);
      if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
      setCtx(await r.json());
      setError(null);
    } catch (e) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  }, [token]);

  useEffect(() => { load(); }, [load]);

  const sign = async (tid, intended_action, comment) => {
    try {
      const r = await fetch(`${API}/api/v1/escrow/magic/${token}/sign`, {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ tid, intended_action, comment }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
      toast.success("Signature recorded");
      load();
    } catch (e) {
      toast.error(`Sign failed: ${e.message}`);
    }
  };

  return (
    <div className="min-h-screen bg-brand-pale flex flex-col">
      <TopBar />
      <main className="flex-1 max-w-4xl mx-auto w-full px-6 lg:px-10 py-10" data-testid="escrow-officer-portal">
        <div className="pmc-label">Escrow officer portal</div>
        {loading && <div className="mt-6 text-brand-navy/60">Loading…</div>}
        {error && <div className="mt-6 border-2 border-red-500 bg-red-50 p-6 text-red-900">{error}</div>}
        {ctx && (
          <>
            <h1 className="font-display text-3xl lg:text-4xl mt-2 text-brand-navy">
              {ctx.account.name}
            </h1>
            <p className="text-sm text-brand-navy/60 mt-2 max-w-xl">
              Signed in as <span className="font-mono">{ctx.officer_email}</span> ({ctx.officer_side}) on
              {" "}{ctx.account.institution}. You can sign off on any pending transaction below.
              Both officers must agree on the same action for admin to release the funds.
            </p>
            <div className="mt-8 grid gap-5">
              {ctx.transactions.length === 0 && (
                <div className="text-brand-navy/60 py-12 text-center border border-dashed border-brand-navy/20 bg-white">
                  No pending transactions on this account.
                </div>
              )}
              {ctx.transactions.map((tx) => (
                <TransactionRow key={tx.id} tx={tx}
                                 myEmail={ctx.officer_email}
                                 mySide={ctx.officer_side}
                                 onSign={sign}/>
              ))}
            </div>
          </>
        )}
      </main>
      <Footer />
    </div>
  );
}
