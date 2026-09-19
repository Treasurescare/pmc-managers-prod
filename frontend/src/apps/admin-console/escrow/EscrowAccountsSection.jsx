/**
 * EscrowAccountsSection — refactor slice of EscrowPanel.
 * Renders the joint-account list + inline "New joint account" form.
 * Owns its OWN "new account" form state so EscrowPanel stays small.
 */
import { useState } from "react";
import { toast } from "sonner";
import { escrowApi, formatApiError, showApiError} from "@/lib/api";
import { InfoDot } from "@/components/InfoDot";

const CURRENCIES = ["USD", "EUR", "GBP", "INR", "KZT", "AED"];
const EMPTY = {
  name: "", institution: "", account_no: "", iban: "", swift: "", currency: "USD",
  pmc_officer:    { name: "", email: "", designation: "", role: "pmc" },
  escrow_officer: { name: "", email: "", designation: "", role: "escrow_institution" },
  active: true, notes: "",
};

function OfficerFieldset({ label, value, testidPrefix, onChange }) {
  return (
    <fieldset className="md:col-span-3 border border-brand-navy/10 p-3">
      <legend className="pmc-label px-2">{label}</legend>
      <div className="grid gap-2 md:grid-cols-3">
        <input placeholder="Name" value={value.name}
               onChange={(e) => onChange({ ...value, name: e.target.value })}
               data-testid={`${testidPrefix}-name`}
               className="px-3 py-2 border border-brand-navy/20"/>
        <input placeholder="Email" type="email" value={value.email}
               onChange={(e) => onChange({ ...value, email: e.target.value })}
               data-testid={`${testidPrefix}-email`}
               className="px-3 py-2 border border-brand-navy/20"/>
        <input placeholder="Designation" value={value.designation}
               onChange={(e) => onChange({ ...value, designation: e.target.value })}
               className="px-3 py-2 border border-brand-navy/20"/>
      </div>
    </fieldset>
  );
}

export default function EscrowAccountsSection({ accounts, onReload }) {
  const [showNew, setShowNew] = useState(false);
  const [acc, setAcc] = useState(EMPTY);

  const create = async () => {
    try {
      await escrowApi.createAccount({ ...acc, currency: acc.currency.toUpperCase() });
      toast.success("Joint escrow account created");
      setShowNew(false);
      setAcc(EMPTY);
      onReload();
    } catch (e) { showApiError(e); }
  };

  return (
    <section>
      <div className="flex items-center justify-between mb-3">
        <div>
          <div className="pmc-label">Joint escrow accounts</div>
          <div className="text-xs text-brand-navy/60">
            Each account is operated by two officers — PMC + Escrow Institution — and both must sign every release.
          </div>
        </div>
        <button onClick={() => setShowNew(!showNew)} data-testid="escrow-new-acc-toggle"
                className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          {showNew ? "Cancel" : "New joint account"}
        </button>
      </div>

      {showNew && (
        <div className="border border-brand-navy/20 bg-white p-6 grid gap-3 md:grid-cols-3 mb-4" data-testid="escrow-new-acc-form">
          <label><span className="pmc-label">Display name<InfoDot tip="Internal label for the joint account. Free text (e.g. 'HSBC · Contract 2026-01 escrow')." /></span>
            <input value={acc.name} onChange={(e) => setAcc({ ...acc, name: e.target.value })}
                   data-testid="escrow-acc-name" className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">Institution (bank / trustee)<InfoDot tip="Bank or trustee that holds the funds. Used on printed transaction receipts and audit exports." /></span>
            <input value={acc.institution} onChange={(e) => setAcc({ ...acc, institution: e.target.value })}
                   data-testid="escrow-acc-inst" className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">Account no.<InfoDot tip="Bank account number for the escrow. Store-of-record only — no wire is triggered from this app." /></span>
            <input value={acc.account_no} onChange={(e) => setAcc({ ...acc, account_no: e.target.value })}
                   data-testid="escrow-acc-no" className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">IBAN<InfoDot tip="Optional. International Bank Account Number for cross-border wires." /></span>
            <input value={acc.iban} onChange={(e) => setAcc({ ...acc, iban: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">SWIFT / BIC<InfoDot tip="Optional. Bank identifier code required for foreign-currency releases." /></span>
            <input value={acc.swift} onChange={(e) => setAcc({ ...acc, swift: e.target.value })}
                   className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
          <label><span className="pmc-label">Currency<InfoDot tip="Ledger currency for this account. Transactions in other currencies must be converted before posting." /></span>
            <select value={acc.currency} onChange={(e) => setAcc({ ...acc, currency: e.target.value })}
                    className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
              {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
            </select></label>
          <OfficerFieldset label="PMC officer" value={acc.pmc_officer}
                            testidPrefix="escrow-pmc"
                            onChange={(v) => setAcc({ ...acc, pmc_officer: v })}/>
          <OfficerFieldset label="Escrow-institution officer" value={acc.escrow_officer}
                            testidPrefix="escrow-eo"
                            onChange={(v) => setAcc({ ...acc, escrow_officer: v })}/>
          <div className="md:col-span-3 flex justify-end">
            <button onClick={create} data-testid="escrow-acc-save"
                    className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
              Create joint account
              <InfoDot tip="Both officers must have DIFFERENT emails. The system will reject the create if names/emails collide." />
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
  );
}
