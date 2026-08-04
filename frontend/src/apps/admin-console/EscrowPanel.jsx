import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { escrowApi, formatApiError } from "@/lib/api";

/**
 * EscrowPanel — governance-first EMD escrow ledger.
 *
 * UX matches the two-officer model:
 *   1. Admin creates a JOINT account (one PMC officer + one escrow officer).
 *   2. When EMD lands, Accounting records an inbound transaction against it.
 *   3. On outcome, EACH officer independently signs off on the intended
 *      action (release_to_contractor / release_to_vendor / forfeit).
 *   4. Only after BOTH signatures for the same action is the release button
 *      unlocked; the operator then wires the funds and the ledger closes.
 */
export default function EscrowPanel() {
  const [accounts, setAccounts] = useState([]);
  const [txs, setTxs] = useState([]);
  const [showNewAcc, setShowNewAcc] = useState(false);
  const [showNewTx, setShowNewTx] = useState(false);

  const [acc, setAcc] = useState({
    name: "", institution: "", account_no: "", iban: "", swift: "", currency: "USD",
    pmc_officer: { name: "", email: "", designation: "", role: "pmc" },
    escrow_officer: { name: "", email: "", designation: "", role: "escrow_institution" },
    active: true, notes: "",
  });
  const [tx, setTx] = useState({
    bid_ref: "", notice_ref: "", vendor_ref: "", escrow_account_id: "",
    amount: 0, currency: "USD", reference: "", notes: "",
  });

  const load = useCallback(() => {
    escrowApi.listAccounts().then((d) => setAccounts(d.items || [])).catch(() => {});
    escrowApi.listTransactions({}).then((d) => setTxs(d.items || [])).catch(() => {});
  }, []);
  useEffect(() => { load(); }, [load]);

  const activeAccounts = useMemo(() => accounts.filter((a) => a.active), [accounts]);

  const createAccount = async () => {
    try {
      await escrowApi.createAccount({ ...acc, currency: acc.currency.toUpperCase() });
      toast.success("Joint escrow account created");
      setShowNewAcc(false);
      setAcc({ ...acc, name: "", institution: "", account_no: "" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const createTx = async () => {
    if (!tx.escrow_account_id) return toast.error("Pick an escrow account");
    if (!tx.bid_ref || !tx.amount) return toast.error("Bid ref and amount are required");
    try {
      await escrowApi.initTransaction({ ...tx, amount: Number(tx.amount),
                                          currency: tx.currency.toUpperCase() });
      toast.success("EMD receipt recorded");
      setShowNewTx(false);
      setTx({ ...tx, bid_ref: "", amount: 0, reference: "" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const signAction = async (t, action) => {
    try {
      await escrowApi.sign(t.id, { intended_action: action });
      toast.success(`Signed as officer · ${action}`);
      load();
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
    if (!confirm(`Release ${t.amount} ${t.currency} — ${pmc.action}?`)) return;
    try {
      await escrowApi.release(t.id, { action: pmc.action });
      toast.success("Release recorded — ledger closed");
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div className="space-y-8" data-testid="escrow-panel">
      <section>
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="pmc-label">Joint escrow accounts</div>
            <div className="text-xs text-brand-navy/60">
              Each account is operated by two officers — PMC + Escrow Institution — and both must sign every release.
            </div>
          </div>
          <button onClick={() => setShowNewAcc(!showNewAcc)} data-testid="escrow-new-acc-toggle"
                  className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            {showNewAcc ? "Cancel" : "New joint account"}
          </button>
        </div>

        {showNewAcc && (
          <div className="border border-brand-navy/20 bg-white p-6 grid gap-3 md:grid-cols-3 mb-4" data-testid="escrow-new-acc-form">
            <label><span className="pmc-label">Display name</span>
              <input value={acc.name} onChange={(e) => setAcc({ ...acc, name: e.target.value })}
                     data-testid="escrow-acc-name" className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label><span className="pmc-label">Institution (bank / trustee)</span>
              <input value={acc.institution} onChange={(e) => setAcc({ ...acc, institution: e.target.value })}
                     data-testid="escrow-acc-inst" className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label><span className="pmc-label">Account no.</span>
              <input value={acc.account_no} onChange={(e) => setAcc({ ...acc, account_no: e.target.value })}
                     data-testid="escrow-acc-no" className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label><span className="pmc-label">IBAN</span>
              <input value={acc.iban} onChange={(e) => setAcc({ ...acc, iban: e.target.value })}
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label><span className="pmc-label">SWIFT / BIC</span>
              <input value={acc.swift} onChange={(e) => setAcc({ ...acc, swift: e.target.value })}
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label><span className="pmc-label">Currency</span>
              <select value={acc.currency} onChange={(e) => setAcc({ ...acc, currency: e.target.value })}
                      className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                {["USD", "EUR", "GBP", "INR", "KZT", "AED"].map((c) => <option key={c}>{c}</option>)}
              </select></label>
            <fieldset className="md:col-span-3 border border-brand-navy/10 p-3">
              <legend className="pmc-label px-2">PMC officer</legend>
              <div className="grid gap-2 md:grid-cols-3">
                <input placeholder="Name" value={acc.pmc_officer.name}
                       onChange={(e) => setAcc({ ...acc, pmc_officer: { ...acc.pmc_officer, name: e.target.value } })}
                       data-testid="escrow-pmc-name" className="px-3 py-2 border border-brand-navy/20" />
                <input placeholder="Email" type="email" value={acc.pmc_officer.email}
                       onChange={(e) => setAcc({ ...acc, pmc_officer: { ...acc.pmc_officer, email: e.target.value } })}
                       data-testid="escrow-pmc-email" className="px-3 py-2 border border-brand-navy/20" />
                <input placeholder="Designation" value={acc.pmc_officer.designation}
                       onChange={(e) => setAcc({ ...acc, pmc_officer: { ...acc.pmc_officer, designation: e.target.value } })}
                       className="px-3 py-2 border border-brand-navy/20" />
              </div>
            </fieldset>
            <fieldset className="md:col-span-3 border border-brand-navy/10 p-3">
              <legend className="pmc-label px-2">Escrow-institution officer</legend>
              <div className="grid gap-2 md:grid-cols-3">
                <input placeholder="Name" value={acc.escrow_officer.name}
                       onChange={(e) => setAcc({ ...acc, escrow_officer: { ...acc.escrow_officer, name: e.target.value } })}
                       data-testid="escrow-eo-name" className="px-3 py-2 border border-brand-navy/20" />
                <input placeholder="Email" type="email" value={acc.escrow_officer.email}
                       onChange={(e) => setAcc({ ...acc, escrow_officer: { ...acc.escrow_officer, email: e.target.value } })}
                       data-testid="escrow-eo-email" className="px-3 py-2 border border-brand-navy/20" />
                <input placeholder="Designation" value={acc.escrow_officer.designation}
                       onChange={(e) => setAcc({ ...acc, escrow_officer: { ...acc.escrow_officer, designation: e.target.value } })}
                       className="px-3 py-2 border border-brand-navy/20" />
              </div>
            </fieldset>
            <div className="md:col-span-3 flex justify-end">
              <button onClick={createAccount} data-testid="escrow-acc-save"
                      className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
                Create joint account
              </button>
            </div>
          </div>
        )}

        <div className="border border-brand-navy/10 bg-white divide-y divide-brand-navy/10">
          {accounts.length === 0 && <div className="p-6 text-sm text-brand-navy/50">No accounts configured yet.</div>}
          {accounts.map((a) => (
            <div key={a.id} className="p-4 grid gap-3 md:grid-cols-4" data-testid={`escrow-acc-row-${a.id}`}>
              <div className="md:col-span-2">
                <div className="font-semibold text-brand-navy">{a.name}</div>
                <div className="text-xs text-brand-navy/60">{a.institution} · {a.account_no} · {a.currency}</div>
              </div>
              <div className="text-xs">
                <div className="pmc-label">PMC officer</div>
                <div>{a.pmc_officer?.name} · <span className="font-mono">{a.pmc_officer?.email}</span></div>
              </div>
              <div className="text-xs">
                <div className="pmc-label">Escrow officer</div>
                <div>{a.escrow_officer?.name} · <span className="font-mono">{a.escrow_officer?.email}</span></div>
              </div>
            </div>
          ))}
        </div>
      </section>

      <section>
        <div className="flex items-center justify-between mb-3">
          <div>
            <div className="pmc-label">EMD transactions ledger</div>
            <div className="text-xs text-brand-navy/60">
              Inbound EMD receipts; each release requires both officers to sign the same action.
            </div>
          </div>
          <button onClick={() => setShowNewTx(!showNewTx)} data-testid="escrow-new-tx-toggle"
                  disabled={activeAccounts.length === 0}
                  className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
            {showNewTx ? "Cancel" : "Record inbound EMD"}
          </button>
        </div>

        {showNewTx && (
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
                     data-testid="escrow-tx-bid" className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label><span className="pmc-label">Notice ref</span>
              <input value={tx.notice_ref} onChange={(e) => setTx({ ...tx, notice_ref: e.target.value })}
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label><span className="pmc-label">Vendor ref</span>
              <input value={tx.vendor_ref} onChange={(e) => setTx({ ...tx, vendor_ref: e.target.value })}
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label><span className="pmc-label">Amount</span>
              <input type="number" value={tx.amount || ""}
                     onChange={(e) => setTx({ ...tx, amount: e.target.value })}
                     data-testid="escrow-tx-amount"
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label><span className="pmc-label">Currency</span>
              <input value={tx.currency} onChange={(e) => setTx({ ...tx, currency: e.target.value })}
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label className="md:col-span-3"><span className="pmc-label">Bank reference / UTR</span>
              <input value={tx.reference} onChange={(e) => setTx({ ...tx, reference: e.target.value })}
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
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
          {txs.map((t) => {
            const sigs = t.signatures || {};
            const pmcOk = !!sigs.pmc?.signed_at;
            const escOk = !!sigs.escrow_institution?.signed_at;
            const bothMatch = pmcOk && escOk && sigs.pmc.action === sigs.escrow_institution.action;
            const closed = ["released_to_contractor", "released_to_vendor", "forfeited", "cancelled"].includes(t.status);
            return (
              <div key={t.id} className="p-4" data-testid={`escrow-tx-row-${t.id}`}>
                <div className="flex items-baseline justify-between gap-3 flex-wrap">
                  <div>
                    <span className="font-mono text-xs text-brand-navy-soft">{t.bid_ref}</span>
                    <span className="mx-2 text-brand-navy/30">→</span>
                    <span className="font-semibold text-brand-navy">{t.amount} {t.currency}</span>
                    <span className="ml-3 text-[10px] uppercase tracking-widest px-2 py-0.5 bg-brand-pale text-brand-navy">
                      {t.status}
                    </span>
                  </div>
                  <div className="text-[11px] text-brand-navy/50">
                    {t.escrow_account_snapshot?.name} · received {(t.received_at || "").slice(0, 10)}
                  </div>
                </div>
                <div className="mt-2 grid gap-3 md:grid-cols-2 text-xs">
                  <div className={`p-2 border ${pmcOk ? "bg-emerald-50 border-emerald-200" : "bg-brand-pale border-brand-navy/10"}`}>
                    <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">
                      PMC officer · {t.escrow_account_snapshot?.pmc_officer?.name}
                    </div>
                    {pmcOk
                      ? <div>Signed <b>{sigs.pmc.action}</b> at {sigs.pmc.signed_at?.slice(0, 19).replace('T', ' ')}</div>
                      : <div className="text-brand-navy/50 italic">Awaiting signature</div>}
                  </div>
                  <div className={`p-2 border ${escOk ? "bg-emerald-50 border-emerald-200" : "bg-brand-pale border-brand-navy/10"}`}>
                    <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">
                      Escrow officer · {t.escrow_account_snapshot?.escrow_officer?.name}
                    </div>
                    {escOk
                      ? <div>Signed <b>{sigs.escrow_institution.action}</b> at {sigs.escrow_institution.signed_at?.slice(0, 19).replace('T', ' ')}</div>
                      : <div className="text-brand-navy/50 italic">Awaiting signature</div>}
                  </div>
                </div>
                {!closed && (
                  <div className="mt-3 flex flex-wrap gap-2 border-t border-brand-navy/10 pt-3">
                    {["release_to_contractor", "release_to_vendor", "forfeit"].map((a) => (
                      <button key={a} onClick={() => signAction(t, a)}
                              data-testid={`escrow-sign-${a}-${t.id}`}
                              className="px-3 py-1 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy hover:text-white">
                        Sign · {a.replace(/_/g, " ")}
                      </button>
                    ))}
                    <button onClick={() => release(t)} disabled={!bothMatch}
                            data-testid={`escrow-release-${t.id}`}
                            className="ml-auto px-3 py-1 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
                      Release ({bothMatch ? "unlocked" : "needs both signatures"})
                    </button>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      </section>
    </div>
  );
}
