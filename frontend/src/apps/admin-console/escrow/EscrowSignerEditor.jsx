/**
 * Signer editor — lets admins update the PMC or Escrow officer email on an
 * existing joint account without destroying the account or its history.
 *
 * Uses the existing `PATCH /api/v1/escrow/accounts/{id}` endpoint which
 * accepts `pmc_officer` and `escrow_officer` payloads.
 */
import { useState } from "react";
import { toast } from "sonner";
import { escrowApi, showApiError } from "@/lib/api";
import { EmailInput } from "@/apps/registration-portal/sections/FormPrimitives";

export default function EscrowSignerEditor({ accounts, onReload }) {
  const [accountId, setAccountId] = useState("");
  const [side, setSide] = useState("pmc_officer");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [designation, setDesignation] = useState("");
  const [busy, setBusy] = useState(false);

  const chosen = accounts.find((a) => a.id === accountId);

  const pick = (accId) => {
    setAccountId(accId);
    const a = accounts.find((x) => x.id === accId);
    if (a) {
      const off = side === "pmc_officer" ? a.pmc_officer : a.escrow_officer;
      setName(off?.name || "");
      setEmail(off?.email || "");
      setDesignation(off?.designation || "");
    }
  };

  const flipSide = (s) => {
    setSide(s);
    if (chosen) {
      const off = s === "pmc_officer" ? chosen.pmc_officer : chosen.escrow_officer;
      setName(off?.name || "");
      setEmail(off?.email || "");
      setDesignation(off?.designation || "");
    }
  };

  const save = async () => {
    if (!accountId) return toast.error("Pick an account first");
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email)) return toast.error("Enter a valid officer email");
    if (name.trim().length < 2) return toast.error("Officer name too short");
    if (!window.confirm(`Update ${side === "pmc_officer" ? "PMC" : "Escrow institution"} officer for “${chosen?.name}” to ${email}?`)) return;
    setBusy(true);
    try {
      const role = side === "pmc_officer" ? "pmc" : "escrow_institution";
      await escrowApi.patchAccount(accountId, {
        [side]: { name: name.trim(), email: email.trim(), designation: designation.trim() || null, role },
      });
      toast.success("Signer updated · audit-trail row written");
      onReload?.();
    } catch (e) {
      showApiError(e, { fallbackTitle: "Update failed" });
    } finally { setBusy(false); }
  };

  return (
    <section data-testid="escrow-signer-editor">
      <div className="pmc-label mb-1">Amend signer emails on a joint account</div>
      <div className="text-xs text-brand-navy/60 mb-3">
        Corrects a mistyped officer email on an <b>existing</b> pending account without
        cancelling it. Every change is written to the audit trail with the admin who made it.
      </div>
      <div className="border border-brand-navy/10 bg-white p-4 grid grid-cols-1 md:grid-cols-2 gap-3">
        <label className="block">
          <span className="pmc-label">Joint account</span>
          <select data-testid="signer-account-select" value={accountId}
                  onChange={(e) => pick(e.target.value)}
                  className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
            <option value="">— choose —</option>
            {accounts.map((a) => (
              <option key={a.id} value={a.id}>{a.name} · {a.currency}</option>
            ))}
          </select>
        </label>
        <label className="block">
          <span className="pmc-label">Side to amend</span>
          <select data-testid="signer-side-select" value={side}
                  onChange={(e) => flipSide(e.target.value)}
                  className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
            <option value="pmc_officer">PMC officer</option>
            <option value="escrow_officer">Escrow institution officer</option>
          </select>
        </label>
        <label className="block">
          <span className="pmc-label">Officer name</span>
          <input data-testid="signer-name" value={name}
                 onChange={(e) => setName(e.target.value)}
                 className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white"/>
        </label>
        <label className="block">
          <span className="pmc-label">Officer email</span>
          <EmailInput testId="signer-email" value={email}
                      onChange={(e) => setEmail(e.target.value)}/>
        </label>
        <label className="block md:col-span-2">
          <span className="pmc-label">Designation (optional)</span>
          <input data-testid="signer-designation" value={designation}
                 onChange={(e) => setDesignation(e.target.value)}
                 className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white"/>
        </label>
        <div className="md:col-span-2 flex items-center justify-end gap-2">
          <button type="button" onClick={save} disabled={busy || !accountId}
                  data-testid="save-signer"
                  className="text-[11px] uppercase tracking-widest font-semibold px-4 py-2 bg-brand-navy text-white disabled:opacity-40 disabled:cursor-not-allowed hover:bg-brand-navy/85">
            {busy ? "Saving…" : "Save signer update"}
          </button>
        </div>
      </div>
    </section>
  );
}
