import { useState } from "react";
import { toast } from "sonner";
import { api, showApiError } from "@/lib/api";

/**
 * EscrowInstitutionRegister — public self-service registration for banks /
 * trustees who want to act as escrow providers. Scaffold v51al; NOT yet
 * wired into App.js routes. Mount at `/escrow/register` when activating.
 *
 * Flow: fill core → create draft (receives magic token) → fill signatories,
 * banking, documents on subsequent pages → submit → admin review.
 */
const EMPTY = {
  legal_name: "", trading_name: "", country: "", registered_address: "",
  reg_number: "", tax_id: "", gst_or_vat: "", regulator: "",
  licence_number: "", licence_expiry: "", website: "",
  primary_contact_email: "", primary_contact_phone: "",
  signatories: [{ name: "", designation: "", email: "", phone: "" }],
  banking: [{
    account_name: "", account_number: "", iban: "", swift: "",
    currency: "USD", institution_name: "", branch: "",
    correspondent_bank: "", settlement_cutoff: "",
  }],
  documents: {},
};

export default function EscrowInstitutionRegister() {
  const [form, setForm] = useState(EMPTY);
  const [step, setStep] = useState(1);
  const [registration, setRegistration] = useState(null); // {id, magic_token}
  const [saving, setSaving] = useState(false);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const createDraft = async () => {
    if (!form.legal_name || !form.country || !form.registered_address ||
        !form.reg_number || !form.primary_contact_email) {
      toast.error("Fill legal name, country, address, registration number and primary email");
      return;
    }
    setSaving(true);
    try {
      const r = (await api.post("/api/v1/escrow-institutions/register", form)).data;
      setRegistration(r);
      toast.success("Draft saved — complete signatories, banking and documents next");
      setStep(2);
    } catch (e) { showApiError(e); }
    finally { setSaving(false); }
  };

  const saveStep = async () => {
    if (!registration) return;
    setSaving(true);
    try {
      await api.patch(`/api/v1/escrow-institutions/${registration.id}`,
                      form, { params: { token: registration.magic_token } });
      toast.success("Saved");
      setStep((s) => s + 1);
    } catch (e) { showApiError(e); }
    finally { setSaving(false); }
  };

  const submit = async () => {
    if (!registration) return;
    try {
      await api.post(`/api/v1/escrow-institutions/${registration.id}/submit`,
                     null, { params: { token: registration.magic_token } });
      toast.success("Submitted for review — PMC will respond within 3 business days");
      setStep(5);
    } catch (e) { showApiError(e); }
  };

  const addSignatory = () => setForm((f) => ({
    ...f, signatories: [...f.signatories, { name: "", designation: "", email: "", phone: "" }],
  }));
  const removeSignatory = (i) => setForm((f) => ({
    ...f, signatories: f.signatories.filter((_, idx) => idx !== i),
  }));
  const addBank = () => setForm((f) => ({
    ...f, banking: [...f.banking, { ...EMPTY.banking[0] }],
  }));

  return (
    <div className="max-w-4xl mx-auto p-6" data-testid="escrow-register-page">
      <h1 className="text-2xl font-semibold text-brand-navy mb-2">
        Register as an Escrow Institution
      </h1>
      <p className="text-sm text-brand-navy/70 mb-6">
        PMC Managers partners with licensed banks and trustee companies to hold
        tender EMD and milestone funds under dual-signature control. Approval
        typically takes 3 business days.
      </p>

      <div className="flex gap-2 mb-6 text-[11px] uppercase tracking-widest">
        {["Core", "Signatories", "Banking", "Documents", "Submitted"].map((s, i) => (
          <span key={s} className={"px-3 py-1 border " +
            (step === i + 1 ? "bg-brand-navy text-white border-brand-navy"
                            : "bg-white text-brand-navy/50 border-brand-navy/15")}>
            {i + 1}. {s}
          </span>
        ))}
      </div>

      {step === 1 && (
        <div className="grid md:grid-cols-2 gap-3 bg-white p-6 border border-brand-navy/15">
          <Input label="Legal name *" v={form.legal_name} on={(x) => set("legal_name", x)} />
          <Input label="Trading name" v={form.trading_name} on={(x) => set("trading_name", x)} />
          <Input label="Country *" v={form.country} on={(x) => set("country", x)} />
          <Input label="Registration number *" v={form.reg_number} on={(x) => set("reg_number", x)} />
          <Input label="Registered address *" v={form.registered_address} on={(x) => set("registered_address", x)} wide />
          <Input label="Tax ID" v={form.tax_id} on={(x) => set("tax_id", x)} />
          <Input label="GST / VAT" v={form.gst_or_vat} on={(x) => set("gst_or_vat", x)} />
          <Input label="Regulator / licence authority" v={form.regulator} on={(x) => set("regulator", x)} />
          <Input label="Licence number" v={form.licence_number} on={(x) => set("licence_number", x)} />
          <Input label="Licence expiry (YYYY-MM-DD)" v={form.licence_expiry} on={(x) => set("licence_expiry", x)} />
          <Input label="Website" v={form.website} on={(x) => set("website", x)} />
          <Input label="Primary contact email *" v={form.primary_contact_email} on={(x) => set("primary_contact_email", x)} />
          <Input label="Primary contact phone" v={form.primary_contact_phone} on={(x) => set("primary_contact_phone", x)} />
          <div className="md:col-span-2 flex justify-end">
            <button onClick={createDraft} disabled={saving}
                    data-testid="escrow-reg-next-1"
                    className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white disabled:opacity-50">
              {saving ? "Saving…" : "Save and continue"}
            </button>
          </div>
        </div>
      )}

      {step === 2 && (
        <div className="bg-white p-6 border border-brand-navy/15 space-y-4">
          <div className="text-xs text-brand-navy/70">
            Named signatories who may sign releases on joint accounts. Each needs
            their own email — these become the signing identities inside PMC.
          </div>
          {form.signatories.map((s, i) => (
            <div key={i} className="grid md:grid-cols-4 gap-3 border-b pb-3">
              <Input label="Name" v={s.name} on={(x) => { const a=[...form.signatories]; a[i].name=x; set("signatories",a); }} />
              <Input label="Designation" v={s.designation} on={(x) => { const a=[...form.signatories]; a[i].designation=x; set("signatories",a); }} />
              <Input label="Email" v={s.email} on={(x) => { const a=[...form.signatories]; a[i].email=x; set("signatories",a); }} />
              <div className="flex items-end gap-2">
                <Input label="Phone" v={s.phone} on={(x) => { const a=[...form.signatories]; a[i].phone=x; set("signatories",a); }} />
                {form.signatories.length > 1 && (
                  <button onClick={() => removeSignatory(i)} className="px-2 py-1 text-xs text-red-700">×</button>
                )}
              </div>
            </div>
          ))}
          <div className="flex justify-between">
            <button onClick={addSignatory} className="text-xs uppercase tracking-widest text-brand-navy">+ Add signatory</button>
            <button onClick={saveStep} disabled={saving}
                    data-testid="escrow-reg-next-2"
                    className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white disabled:opacity-50">
              {saving ? "Saving…" : "Save and continue"}
            </button>
          </div>
        </div>
      )}

      {step === 3 && (
        <div className="bg-white p-6 border border-brand-navy/15 space-y-4">
          <div className="text-xs text-brand-navy/70">
            Banking coordinates for each account you can hold funds in. Settlement
            cutoff is free text (e.g. "16:00 London").
          </div>
          {form.banking.map((b, i) => (
            <div key={i} className="grid md:grid-cols-3 gap-3 border-b pb-3">
              <Input label="Account name" v={b.account_name} on={(x) => { const a=[...form.banking]; a[i].account_name=x; set("banking",a); }} />
              <Input label="Account number" v={b.account_number} on={(x) => { const a=[...form.banking]; a[i].account_number=x; set("banking",a); }} />
              <Input label="Currency" v={b.currency} on={(x) => { const a=[...form.banking]; a[i].currency=x; set("banking",a); }} />
              <Input label="IBAN" v={b.iban} on={(x) => { const a=[...form.banking]; a[i].iban=x; set("banking",a); }} />
              <Input label="SWIFT" v={b.swift} on={(x) => { const a=[...form.banking]; a[i].swift=x; set("banking",a); }} />
              <Input label="Institution" v={b.institution_name} on={(x) => { const a=[...form.banking]; a[i].institution_name=x; set("banking",a); }} />
              <Input label="Branch" v={b.branch} on={(x) => { const a=[...form.banking]; a[i].branch=x; set("banking",a); }} />
              <Input label="Correspondent bank" v={b.correspondent_bank} on={(x) => { const a=[...form.banking]; a[i].correspondent_bank=x; set("correspondent_bank",a); }} />
              <Input label="Settlement cutoff" v={b.settlement_cutoff} on={(x) => { const a=[...form.banking]; a[i].settlement_cutoff=x; set("banking",a); }} />
            </div>
          ))}
          <div className="flex justify-between">
            <button onClick={addBank} className="text-xs uppercase tracking-widest text-brand-navy">+ Add bank</button>
            <button onClick={saveStep} disabled={saving}
                    data-testid="escrow-reg-next-3"
                    className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white disabled:opacity-50">
              {saving ? "Saving…" : "Save and continue"}
            </button>
          </div>
        </div>
      )}

      {step === 4 && (
        <div className="bg-white p-6 border border-brand-navy/15 space-y-3">
          <div className="text-xs text-brand-navy/70">
            Upload KYC documents. All files are stored encrypted; only PMC reviewers
            and your own signatories can read them.
          </div>
          <p className="text-xs text-brand-navy/50 italic">
            Upload wiring reuses the existing /api/v1/uploads/presign + direct endpoints —
            UI hook-up is a 20-line change once the module is activated.
          </p>
          <ul className="text-sm text-brand-navy/80 list-disc list-inside">
            <li>Certificate of incorporation / trust deed</li>
            <li>Regulatory licence</li>
            <li>Tax / GST / VAT registration</li>
            <li>Audited financials (last 2 years)</li>
            <li>Insurance & indemnity cover</li>
            <li>KYC & specimen signature of each signatory</li>
            <li>Letterhead sample, authority resolution</li>
          </ul>
          <div className="flex justify-end">
            <button onClick={submit}
                    data-testid="escrow-reg-submit"
                    className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
              Submit for PMC review
            </button>
          </div>
        </div>
      )}

      {step === 5 && (
        <div className="bg-emerald-50 border border-emerald-300 p-8 text-center">
          <h2 className="text-xl font-semibold text-emerald-900">Submitted ✓</h2>
          <p className="text-sm text-emerald-800 mt-2">
            PMC will email {form.primary_contact_email} within 3 business days.
          </p>
        </div>
      )}
    </div>
  );
}

function Input({ label, v, on, wide }) {
  return (
    <label className={wide ? "md:col-span-2" : ""}>
      <span className="pmc-label text-[10px]">{label}</span>
      <input value={v || ""} onChange={(e) => on(e.target.value)}
             className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/>
    </label>
  );
}
