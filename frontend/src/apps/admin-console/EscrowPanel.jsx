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
import { useCallback, useEffect, useState } from "react";
import { escrowApi } from "@/lib/api";
import EscrowAccountsSection from "./escrow/EscrowAccountsSection";
import EscrowTransactionsSection from "./escrow/EscrowTransactionsSection";

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
    </div>
  );
}
