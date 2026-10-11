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
    // Bug #13 fix — v50m. Mandatory validation client-side so the "Create
    // joint account" button never appears unresponsive. Backend already
    // enforces these; the UI now gives a specific toast per missing field
    // instead of surfacing a generic 422.
    const miss = [];
    if (!acc.name.trim())            miss.push("Display name");
    if (!acc.institution.trim())     miss.push("Institution");
    if (!acc.account_no.trim())      miss.push("Account no.");
    if (!acc.pmc_officer.name.trim())    miss.push("PMC officer name");
    if (!acc.pmc_officer.email.trim())   miss.push("PMC officer email");
    if (!acc.escrow_officer.name.trim()) miss.push("Escrow officer name");
    if (!acc.escrow_officer.email.trim())miss.push("Escrow officer email");
    if (miss.length) {
      toast.error(`Please fill in: ${miss.join(", ")}`);
      return;
    }
    if (acc.pmc_officer.email.trim().toLowerCase() ===
        acc.escrow_officer.email.trim().toLowerCase()) {
      toast.error("PMC and Escrow officer emails must be different.");
      return;
    }
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
          <AccountRow key={a.id} acc={a} onReload={onReload} />
        ))}
      </div>
    </section>
  );
}


// v51ab — single-row Edit for an existing joint escrow account. Lets the
// admin update BOTH officer emails + names + designations in one save,
// instead of the old flow that forced flipping Side-to-amend twice. Uses
// the existing PATCH /escrow/accounts/{id} endpoint which already accepts
// pmc_officer + escrow_officer payloads.
function AccountRow({ acc, onReload }) {
  const [editing, setEditing] = useState(false);
  const [pmc, setPmc] = useState(acc.pmc_officer || { name: "", email: "", designation: "", role: "pmc" });
  const [esc, setEsc] = useState(acc.escrow_officer || { name: "", email: "", designation: "", role: "escrow_institution" });
  const [busy, setBusy] = useState(false);

  const open = () => {
    setPmc({ name: "", email: "", designation: "", role: "pmc", ...(acc.pmc_officer || {}) });
    setEsc({ name: "", email: "", designation: "", role: "escrow_institution", ...(acc.escrow_officer || {}) });
    setEditing(true);
  };
  const cancel = () => setEditing(false);

  const save = async () => {
    const emailRx = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
    if (!emailRx.test(pmc.email || "")) return toast.error("PMC officer email is not valid");
    if (!emailRx.test(esc.email || "")) return toast.error("Escrow officer email is not valid");
    if ((pmc.email || "").toLowerCase() === (esc.email || "").toLowerCase()) {
      return toast.error("PMC and Escrow officer emails must be different.");
    }
    if ((pmc.name || "").trim().length < 2) return toast.error("PMC officer name too short");
    if ((esc.name || "").trim().length < 2) return toast.error("Escrow officer name too short");
    if (!window.confirm(
      `Update signers on “${acc.name}”?\n\n` +
      `  PMC officer     → ${pmc.name} <${pmc.email}>\n` +
      `  Escrow officer  → ${esc.name} <${esc.email}>\n\n` +
      `Every change is written to the audit trail.`
    )) return;
    setBusy(true);
    try {
      await escrowApi.patchAccount(acc.id, {
        pmc_officer: {
          name: pmc.name.trim(), email: pmc.email.trim(),
          designation: (pmc.designation || "").trim() || null, role: "pmc",
        },
        escrow_officer: {
          name: esc.name.trim(), email: esc.email.trim(),
          designation: (esc.designation || "").trim() || null, role: "escrow_institution",
        },
      });
      toast.success("Both signers updated · audit-trail rows written");
      setEditing(false);
      onReload?.();
    } catch (e) { showApiError(e, { fallbackTitle: "Update failed" }); }
    finally { setBusy(false); }
  };

  if (!editing) {
    return (
      <div className="p-4 grid gap-3 md:grid-cols-5 items-start" data-testid={`escrow-acc-row-${acc.id}`}>
        <div className="md:col-span-2 min-w-0">
          <div className="font-semibold text-brand-navy">{acc.name}</div>
          <div className="text-xs text-brand-navy/60 break-all">{acc.institution} · {acc.account_no} · {acc.currency}</div>
        </div>
        <div className="text-xs min-w-0">
          <div className="pmc-label">PMC officer</div>
          <div className="break-all">{acc.pmc_officer?.name} · <span className="font-mono">{acc.pmc_officer?.email}</span></div>
        </div>
        <div className="text-xs min-w-0">
          <div className="pmc-label">Escrow officer</div>
          <div className="break-all">{acc.escrow_officer?.name} · <span className="font-mono">{acc.escrow_officer?.email}</span></div>
        </div>
        <div className="flex md:justify-end">
          <button type="button" onClick={open}
                  data-testid={`escrow-acc-edit-${acc.id}`}
                  className="px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white border border-brand-navy hover:bg-brand-navy-deep">
            Edit signers
          </button>
        </div>
      </div>
    );
  }

  const field = (label, value, onChange, testid, type = "text") => (
    <label className="block">
      <span className="pmc-label">{label}</span>
      <input type={type} value={value || ""} onChange={(e) => onChange(e.target.value)}
             data-testid={testid}
             className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white text-sm"/>
    </label>
  );

  return (
    <div className="p-4 border-l-4 border-brand-navy bg-brand-pale/30" data-testid={`escrow-acc-edit-form-${acc.id}`}>
      <div className="flex items-center justify-between flex-wrap gap-2 mb-3">
        <div>
          <div className="font-semibold text-brand-navy">{acc.name}</div>
          <div className="text-xs text-brand-navy/60">{acc.institution} · {acc.account_no} · {acc.currency}</div>
        </div>
        <div className="text-xs text-brand-navy/60">
          Edit both signers in one save. Every change is written to the audit ledger.
        </div>
      </div>
      <div className="grid gap-4 md:grid-cols-2">
        <fieldset className="border border-brand-navy/15 p-3 bg-white">
          <legend className="pmc-label px-2">PMC officer</legend>
          <div className="grid gap-2">
            {field("Name",        pmc.name,        (v) => setPmc({ ...pmc, name: v }),        `escrow-edit-pmc-name-${acc.id}`)}
            {field("Email",       pmc.email,       (v) => setPmc({ ...pmc, email: v }),       `escrow-edit-pmc-email-${acc.id}`, "email")}
            {field("Designation (optional)", pmc.designation, (v) => setPmc({ ...pmc, designation: v }), `escrow-edit-pmc-desig-${acc.id}`)}
          </div>
        </fieldset>
        <fieldset className="border border-brand-navy/15 p-3 bg-white">
          <legend className="pmc-label px-2">Escrow-institution officer</legend>
          <div className="grid gap-2">
            {field("Name",        esc.name,        (v) => setEsc({ ...esc, name: v }),        `escrow-edit-eo-name-${acc.id}`)}
            {field("Email",       esc.email,       (v) => setEsc({ ...esc, email: v }),       `escrow-edit-eo-email-${acc.id}`, "email")}
            {field("Designation (optional)", esc.designation, (v) => setEsc({ ...esc, designation: v }), `escrow-edit-eo-desig-${acc.id}`)}
          </div>
        </fieldset>
      </div>
      <div className="mt-3 flex justify-end gap-2 flex-wrap">
        <button type="button" onClick={cancel} disabled={busy}
                data-testid={`escrow-acc-edit-cancel-${acc.id}`}
                className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy/80 hover:bg-brand-navy/5 disabled:opacity-40">
          Cancel
        </button>
        <button type="button" onClick={save} disabled={busy}
                data-testid={`escrow-acc-edit-save-${acc.id}`}
                className="px-5 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
          {busy ? "Saving…" : "Save both signers"}
        </button>
      </div>
    </div>
  );
}
