/**
 * EscrowPanel — governance-first EMD escrow ledger.
 *
 * Post-Wave-38 refactor: split into two focused subcomponents so this file
 * stays under 50 lines and each section owns its own form state.
 *
 * Two-officer governance model:
 *   1. Admin creates a JOINT account (one PMC officer + one escrow officer).
 *   2. When EMD lands, Accounting records an inbound transaction against it.
 *   3. On outcome, EACH officer independently signs off on the intended
 *      action (release_to_contractor / release_to_vendor / forfeit).
 *   4. Only after BOTH signatures for the same action is the release button
 *      unlocked; the operator then wires the funds and the ledger closes.
 */
import { useCallback, useEffect, useMemo, useState } from "react";
import { escrowApi } from "@/lib/api";
import EscrowAccountsSection from "./escrow/EscrowAccountsSection";
import EscrowTransactionsSection from "./escrow/EscrowTransactionsSection";

// E-03 fix — reconciliation-vs-bank sub-panel.
// Renders one row per joint account with Ledger balance vs Bank balance and
// a delta pill. Bank balances are pulled from the account's last-reported
// figure (echoed by the escrow institution API adapter); when unknown the
// column shows "n/a" so operators know to reconcile manually.
function ReconciliationSection({ accounts, txs }) {
  const rows = useMemo(() => accounts.map((a) => {
    const acctTxs = txs.filter((t) => t.account_id === a.id);
    const ledger = acctTxs.reduce((sum, t) => sum + (t.direction === "in" ? (t.amount || 0) : -(t.amount || 0)), 0);
    const bank = a.bank_balance ?? null;
    const delta = bank == null ? null : ledger - bank;
    return { a, ledger, bank, delta };
  }), [accounts, txs]);

  return (
    <section data-testid="escrow-reconciliation">
      <div className="pmc-label mb-1">Reconciliation · Ledger vs Bank</div>
      <div className="text-xs text-brand-navy/60 mb-3">
        Compares the internal PMC ledger balance against the last-reported bank statement per account.
        A non-zero delta means someone (usually the escrow institution) hasn't confirmed a leg yet.
      </div>
      <div className="border border-brand-navy/10 bg-white overflow-x-auto">
        <table className="w-full text-sm">
          <thead className="text-xs text-brand-navy/60 border-b">
            <tr>
              <th className="text-left px-3 py-2">Account</th>
              <th className="text-right px-3 py-2">Ledger</th>
              <th className="text-right px-3 py-2">Bank</th>
              <th className="text-right px-3 py-2">Delta</th>
              <th className="text-center px-3 py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {rows.length === 0 && (
              <tr><td colSpan={5} className="p-6 text-brand-navy/50 text-center">
                No joint accounts to reconcile yet.
              </td></tr>
            )}
            {rows.map(({ a, ledger, bank, delta }) => (
              <tr key={a.id} className="border-t" data-testid={`escrow-recon-row-${a.id}`}>
                <td className="px-3 py-2">
                  <div className="font-semibold text-brand-navy">{a.name}</div>
                  <div className="text-xs text-brand-navy/60 font-mono">{a.account_no} · {a.currency}</div>
                </td>
                <td className="px-3 py-2 text-right font-mono">{a.currency} {ledger.toLocaleString()}</td>
                <td className="px-3 py-2 text-right font-mono">
                  {bank == null ? <span className="text-brand-navy/40">n/a</span> : <>{a.currency} {bank.toLocaleString()}</>}
                </td>
                <td className="px-3 py-2 text-right font-mono">
                  {delta == null ? "—" : (
                    <span className={delta === 0 ? "text-emerald-700" : "text-amber-800"}>
                      {delta > 0 ? "+" : ""}{delta.toLocaleString()}
                    </span>
                  )}
                </td>
                <td className="px-3 py-2 text-center">
                  <span className={"px-2 py-0.5 text-[10px] uppercase tracking-widest border " + (
                    delta === 0 ? "border-emerald-500 text-emerald-800" :
                    delta == null ? "border-brand-navy/20 text-brand-navy/50" :
                    "border-amber-500 text-amber-800"
                  )}>
                    {delta === 0 ? "Reconciled" : delta == null ? "Pending bank feed" : "Delta"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default function EscrowPanel() {
  const [accounts, setAccounts] = useState([]);
  const [txs, setTxs] = useState([]);

  const load = useCallback(() => {
    escrowApi.listAccounts().then((d) => setAccounts(d.items || [])).catch(() => {});
    escrowApi.listTransactions({}).then((d) => setTxs(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="space-y-8" data-testid="escrow-panel">
      <EscrowAccountsSection accounts={accounts} onReload={load}/>
      <EscrowTransactionsSection accounts={accounts} txs={txs} onReload={load}/>
      <ReconciliationSection accounts={accounts} txs={txs}/>
    </div>
  );
}
