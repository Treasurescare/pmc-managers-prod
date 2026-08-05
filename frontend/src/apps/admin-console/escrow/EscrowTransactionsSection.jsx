/**
 * EscrowTransactionsSection — refactor slice of EscrowPanel.
 * Owns the inbound-EMD form + the ledger with per-officer sign buttons and
 * the final release button. Kept pure UI + calls into escrowApi.
 */
import { useMemo, useState } from "react";
import { toast } from "sonner";
import { escrowApi, formatApiError } from "@/lib/api";

const ACTIONS = ["release_to_contractor", "release_to_vendor", "forfeit"];
const CLOSED = new Set(["released_to_contractor", "released_to_vendor", "forfeited", "cancelled"]);
const EMPTY_TX = {
  bid_ref: "", notice_ref: "", vendor_ref: "", escrow_account_id: "",
  amount: 0, currency: "USD", reference: "", notes: "",
};

function SignatureBox({ label, officer, sig }) {
  const ok = !!sig?.signed_at;
  return (
    <div className={`p-2 border ${ok ? "bg-emerald-50 border-emerald-200" : "bg-brand-pale border-brand-navy/10"}`}>
      <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">
        {label} · {officer?.name}
      </div>
      {ok
        ? <div>Signed <b>{sig.action}</b> at {sig.signed_at?.slice(0, 19).replace("T", " ")}</div>
        : <div className="text-brand-navy/50 italic">Awaiting signature</div>}
    </div>
  );
}

function TransactionRow({ t, onSign, onRelease }) {
  const sigs = t.signatures || {};
  const pmc = sigs.pmc || {};
  const esc = sigs.escrow_institution || {};
  const bothMatch = pmc.action && pmc.action === esc.action;
  const closed = CLOSED.has(t.status);
  return (
    <div className="p-4" data-testid={`escrow-tx-row-${t.id}`}>
      <div className="flex items-baseline justify-between gap-3 flex-wrap">
        <div>
          <span className="font-mono text-xs text-brand-navy-soft">{t.bid_ref}</span>
          <span className="mx-2 text-brand-navy/30">→</span>
          <span className="font-semibold text-brand-navy">{t.amount} {t.currency}</span>
          <span className="ml-3 text-[10px] uppercase tracking-widest px-2 py-0.5 bg-brand-pale text-brand-navy">{t.status}</span>
        </div>
        <div className="text-[11px] text-brand-navy/50">
          {t.escrow_account_snapshot?.name} · received {(t.received_at || "").slice(0, 10)}
        </div>
      </div>
      <div className="mt-2 grid gap-3 md:grid-cols-2 text-xs">
        <SignatureBox label="PMC officer" officer={t.escrow_account_snapshot?.pmc_officer} sig={pmc}/>
        <SignatureBox label="Escrow officer" officer={t.escrow_account_snapshot?.escrow_officer} sig={esc}/>
      </div>
      {!closed && (
        <div className="mt-3 flex flex-wrap gap-2 border-t border-brand-navy/10 pt-3">
          {ACTIONS.map((a) => (
            <button key={a} onClick={() => onSign(t, a)}
                    data-testid={`escrow-sign-${a}-${t.id}`}
                    className="px-3 py-1 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy hover:text-white">
              Sign · {a.replace(/_/g, " ")}
            </button>
          ))}
          <button onClick={() => onRelease(t)} disabled={!bothMatch}
                  data-testid={`escrow-release-${t.id}`}
                  className="ml-auto px-3 py-1 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
            Release ({bothMatch ? "unlocked" : "needs both signatures"})
          </button>
        </div>
      )}
    </div>
  );
}

export default function EscrowTransactionsSection({ accounts, txs, onReload }) {
  const [showNew, setShowNew] = useState(false);
  const [tx, setTx] = useState(EMPTY_TX);
  const activeAccounts = useMemo(() => accounts.filter((a) => a.active), [accounts]);

  const createTx = async () => {
    if (!tx.escrow_account_id) return toast.error("Pick an escrow account");
    if (!tx.bid_ref || !tx.amount) return toast.error("Bid ref and amount are required");
    try {
      await escrowApi.initTransaction({ ...tx, amount: Number(tx.amount),
                                          currency: tx.currency.toUpperCase() });
      toast.success("EMD receipt recorded");
      setShowNew(false);
      setTx(EMPTY_TX);
      onReload();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const signAction = async (t, action) => {
    try {
      await escrowApi.sign(t.id, { intended_action: action });
      toast.success(`Signed as officer · ${action}`);
      onReload();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const release = async (t) => {
    const sigs = t.signatures || {};
    const pmc = sigs.pmc || {};
    const esc = sigs.escrow_institution || {};
    if (!pmc.action || pmc.action !== esc.action) {
      toast.error("Both officers must sign the SAME action before release");
      return;
    }
    if (!window.confirm(`Release ${t.amount} ${t.currency} — ${pmc.action}?`)) return;
    try {
      await escrowApi.release(t.id, { action: pmc.action });
      toast.success("Release recorded — ledger closed");
      onReload();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="pmc-label">EMD transactions ledger</div>
          <div className="text-xs text-brand-navy/60">
            Inbound EMD receipts; each release requires both officers to sign the same action.
          </div>
        </div>
        <button onClick={() => setShowNew(!showNew)} data-testid="escrow-new-tx-toggle"
                disabled={activeAccounts.length === 0}
                className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
          {showNew ? "Cancel" : "Record inbound EMD"}
        </button>
      </div>

      {showNew && (
        <div className="border border-brand-navy/20 bg-white p-6 grid gap-3 md:grid-cols-3 mb-4" data-testid="escrow-new-tx-form">
          <label className="md:col-span-1"><span className="pmc-label">Escrow account</span>
            <select value={tx.escrow_account_id}
                    onChange={(e) => setTx({ ...tx, escrow_account_id: e.target.value })}
                    data-testid="escrow-tx-acc"
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
              <option value="">Select…</option>
              {activeAccounts.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
            </select></label>
          <label><span className="pmc-label">Bid ref</span>
            <input value={tx.bid_ref} onChange={(e) => setTx({ ...tx, bid_ref: e.target.value })}
                   data-testid="escrow-tx-bid" className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">Notice ref</span>
            <input value={tx.notice_ref} onChange={(e) => setTx({ ...tx, notice_ref: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">Vendor ref</span>
            <input value={tx.vendor_ref} onChange={(e) => setTx({ ...tx, vendor_ref: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">Amount</span>
            <input type="number" value={tx.amount || ""}
                   onChange={(e) => setTx({ ...tx, amount: e.target.value })}
                   data-testid="escrow-tx-amount"
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">Currency</span>
            <input value={tx.currency} onChange={(e) => setTx({ ...tx, currency: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label className="md:col-span-3"><span className="pmc-label">Bank reference / UTR</span>
            <input value={tx.reference} onChange={(e) => setTx({ ...tx, reference: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <div className="md:col-span-3 flex justify-end">
            <button onClick={createTx} data-testid="escrow-tx-save"
                    className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
              Record receipt
            </button>
          </div>
        </div>
      )}

      <div className="border border-brand-navy/10 bg-white divide-y divide-brand-navy/10">
        {txs.length === 0 && <div className="p-6 text-sm text-brand-navy/50">No transactions yet.</div>}
        {txs.map((t) => (
          <TransactionRow key={t.id} t={t} onSign={signAction} onRelease={release}/>
        ))}
      </div>
    </section>
  );
}
