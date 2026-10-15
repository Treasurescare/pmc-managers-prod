/**
 * EscrowAccountWizard — v52d. The 5-section registration wizard, now
 * driven by the escrow_account_token session cookie instead of a magic
 * token in the URL. Autosaves to the account's owned institution on
 * every "Save as draft" / "Save and continue".
 *
 * Wraps the existing EscrowCoreForm / EscrowBankingStep / document
 * upload step. Signatories step and submit flow are unchanged except
 * for the auth mechanism.
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, showApiError, uploadsApi, mastersApi } from "@/lib/api";
import EscrowCoreForm from "./EscrowCoreForm";
import EscrowBankingStep from "./EscrowBankingStep";
import PhonePrefixInput from "./PhonePrefixInput";

const DOC_SLOTS = [
  ["incorporation_certificate", "Certificate of incorporation / trust deed"],
  ["regulatory_licence", "Regulatory licence"],
  ["tax_registration", "Tax / GST / VAT registration"],
  ["audited_financials_y1", "Audited financials — year 1"],
  ["audited_financials_y2", "Audited financials — year 2"],
  ["insurance_indemnity", "Insurance & indemnity cover"],
  ["letterhead_sample", "Letterhead sample"],
  ["signatory_authority_resolution", "Signatory authority resolution"],
];

const EMPTY = {
  legal_name: "", trading_name: "", country: "", registered_address: "",
  address_line1: "", address_line2: "", city: "",
  state_code: "", state_name: "", postal_code: "",
  reg_number: "", tax_id: "", gst_or_vat: "", regulator: "",
  licence_number: "", licence_expiry: "", website: "",
  primary_contact_email: "", primary_contact_phone: "", phone_country_code: "",
  signatories: [{ name: "", designation: "", email: "", phone: "" }],
  mobile_phone: "", office_phone: "",
  banking: [{
    account_name: "", account_number: "", iban: "", swift: "",
    currency: "USD", institution_name: "", branch: "",
    bank_country: "", bank_state: "", bank_city: "",
    bank_code: "", sort_code: "", routing_number: "",
    correspondent_bank: "", correspondent_swift: "", settlement_cutoff: "",
  }],
  documents: {},
};

export default function EscrowAccountWizard({ account, onDone }) {
  const iid = account?.institution?.id;
  const [form, setForm] = useState(EMPTY);
  const [step, setStep] = useState(1);
  const [saving, setSaving] = useState(false);
  const [allCountries, setAllCountries] = useState([]);
  const [loaded, setLoaded] = useState(false);

  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  useEffect(() => {
    mastersApi.listCountriesPublic().then(setAllCountries).catch(() => setAllCountries([]));
  }, []);

  // Preload institution snapshot (so returning registrants resume at the
  // first incomplete section).
  useEffect(() => {
    if (!iid) return;
    api.get(`/api/v1/escrow-institutions/${iid}/admin-view-public`)
      .then((r) => {
        const d = r.data || {};
        setForm((prev) => ({
          ...prev,
          ...d,
          signatories: d.signatories?.length ? d.signatories : prev.signatories,
          banking: d.banking?.length ? d.banking : prev.banking,
          documents: d.documents || {},
          primary_contact_email: d.primary_contact_email || account?.email,
          legal_name: d.legal_name || account?.legal_name,
          primary_contact_phone: d.primary_contact_phone || account?.primary_contact_phone,
        }));
        setLoaded(true);
      })
      .catch(() => setLoaded(true));
  }, [iid]); // eslint-disable-line

  const cleanPayload = (f) => ({
    ...f,
    signatories: (f.signatories || []).filter((s) => (s.name || "").trim() || (s.email || "").trim()),
    banking: (f.banking || []).filter((b) =>
      (b.account_name || "").trim() || (b.account_number || "").trim() ||
      (b.institution_name || "").trim()),
  });

  const persist = async ({ advance }) => {
    if (!iid) return;
    setSaving(true);
    try {
      await api.patch(`/api/v1/escrow-institutions/${iid}`, cleanPayload(form));
      toast.success(advance ? "Saved" : "Draft saved to your account");
      if (advance) setStep((s) => Math.min(5, s + 1));
    } catch (e) { showApiError(e); }
    finally { setSaving(false); }
  };

  const saveStep = () => persist({ advance: true });
  const saveDraft = () => persist({ advance: false });
  const goBack = () => setStep((s) => Math.max(1, s - 1));

  const submit = async () => {
    try {
      await api.post(`/api/v1/escrow-institutions/${iid}/submit`);
      toast.success("Submitted for review — PMC will respond within 3 business days");
      onDone?.();
    } catch (e) { showApiError(e); }
  };

  const addSignatory = () => setForm((f) => ({
    ...f, signatories: [...f.signatories, { name: "", designation: "", email: "", phone: "" }],
  }));
  const removeSignatory = (i) => setForm((f) => ({
    ...f, signatories: f.signatories.filter((_, idx) => idx !== i),
  }));

  if (!loaded) {
    return <div className="p-10 text-brand-navy/50">Loading your registration…</div>;
  }

  return (
    <div className="max-w-4xl mx-auto p-6" data-testid="escrow-account-wizard">
      <h1 className="font-serif text-2xl text-brand-navy mb-2">
        Complete your registration
      </h1>
      <p className="text-sm text-brand-navy/70 mb-6">
        Signed in as <strong>{account.email}</strong>. Everything you save
        here lives in your account — close the tab anytime and sign back
        in to resume.
      </p>

      <div className="flex gap-2 mb-6 text-[11px] uppercase tracking-widest flex-wrap">
        {["Core", "Signatories", "Banking", "Documents", "Submitted"].map((s, i) => (
          <span key={s} className={"px-3 py-1 border " +
            (step === i + 1 ? "bg-brand-navy text-white border-brand-navy"
                            : "bg-white text-brand-navy/50 border-brand-navy/15")}>
            {i + 1}. {s}
          </span>
        ))}
      </div>

      {step === 1 && (
        <>
          <EscrowCoreForm form={form} set={set} onNext={saveStep} saving={saving} />
          <div className="flex justify-end mt-3">
            <button type="button" onClick={saveDraft} disabled={saving}
                    data-testid="escrow-wiz-draft-1"
                    className="px-5 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-50">
              {saving ? "Saving…" : "Save as draft"}
            </button>
          </div>
        </>
      )}

      {step === 2 && (
        <StepShell step={2} canBack goBack={goBack}
                   saveDraft={saveDraft} saveNext={saveStep} saving={saving}>
          <div className="text-xs text-brand-navy/70 mb-4">
            Named signatories who may sign releases on joint accounts. Each needs
            their own email — these become the signing identities inside PMC.
          </div>
          {form.signatories.map((s, i) => (
            <div key={i} className="grid md:grid-cols-2 gap-4 border-b pb-3 mb-3"
                 data-testid={`escrow-sig-row-${i}`}>
              <WField label="Name" v={s.name} on={(x) => { const a=[...form.signatories]; a[i].name=x; set("signatories",a); }} />
              <WField label="Designation" v={s.designation} on={(x) => { const a=[...form.signatories]; a[i].designation=x; set("signatories",a); }} />
              <WField label="Email" v={s.email} on={(x) => { const a=[...form.signatories]; a[i].email=x; set("signatories",a); }} />
              <div>
                <div className="text-[10px] uppercase tracking-widest text-brand-navy/70">Phone</div>
                <div className="mt-1">
                  <PhonePrefixInput testId={`escrow-sig-${i}-phone`}
                                    value={s.phone || ""}
                                    onChange={(v) => { const a=[...form.signatories]; a[i].phone=v; set("signatories",a); }}
                                    countries={allCountries}
                                    defaultCountry={form.country} />
                </div>
                {form.signatories.length > 1 && (
                  <button onClick={() => removeSignatory(i)} className="mt-1 px-2 py-1 text-xs text-red-700">× Remove</button>
                )}
              </div>
            </div>
          ))}
          <button onClick={addSignatory} className="text-xs uppercase tracking-widest text-brand-navy hover:underline"
                  data-testid="escrow-wiz-add-sig">
            + Add signatory
          </button>
        </StepShell>
      )}

      {step === 3 && (
        <StepShell step={3} canBack goBack={goBack}
                   saveDraft={saveDraft} saveNext={saveStep} saving={saving}>
          <EscrowBankingStep banking={form.banking}
                             onChange={(next) => set("banking", next)} />
        </StepShell>
      )}

      {step === 4 && (
        <StepShell step={4} canBack goBack={goBack}
                   saveDraft={saveDraft}
                   nextLabel="Submit for PMC review" saveNext={submit}
                   saving={saving}>
          <div className="text-xs text-brand-navy/70 mb-3">
            Upload KYC documents. Files are kept confidential — only PMC
            reviewers and your own signatories can retrieve them.
          </div>
          <div className="grid gap-2">
            {DOC_SLOTS.map(([slot, label]) => (
              <DocSlot key={slot} slot={slot} label={label}
                       current={form.documents?.[slot]}
                       institutionId={iid}
                       onUploaded={async (meta) => {
                         const next = { ...(form.documents || {}), [slot]: meta };
                         const nf = { ...form, documents: next };
                         setForm(nf);
                         try {
                           await api.patch(`/api/v1/escrow-institutions/${iid}`, cleanPayload(nf));
                         } catch (e) { /* toast on upload is enough */ }
                       }}
                       onRemoved={async () => {
                         const next = { ...(form.documents || {}) };
                         delete next[slot];
                         const nf = { ...form, documents: next };
                         setForm(nf);
                         try {
                           await api.patch(`/api/v1/escrow-institutions/${iid}`, cleanPayload(nf));
                         } catch (e) { /* ignore */ }
                       }}
              />
            ))}
          </div>
        </StepShell>
      )}

      {step === 5 && (
        <div className="bg-emerald-50 border border-emerald-300 p-8 text-center"
             data-testid="escrow-wiz-submitted">
          <h2 className="text-xl font-semibold text-emerald-900">Submitted ✓</h2>
          <p className="text-sm text-emerald-800 mt-2">
            PMC will email {form.primary_contact_email} and ping your bell
            icon within 3 business days.
          </p>
        </div>
      )}
    </div>
  );
}


function StepShell({ children, canBack, goBack, saveDraft, saveNext,
                     nextLabel = "Save & continue", saving }) {
  return (
    <div>
      {children}
      <div className="flex justify-between items-center mt-6">
        <button type="button" onClick={goBack} disabled={!canBack || saving}
                data-testid="escrow-wiz-back"
                className="px-5 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy/70 hover:bg-brand-pale disabled:opacity-40">
          ← Back
        </button>
        <div className="flex gap-2">
          <button type="button" onClick={saveDraft} disabled={saving}
                  data-testid="escrow-wiz-draft"
                  className="px-5 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-50">
            {saving ? "Saving…" : "Save as draft"}
          </button>
          <button type="button" onClick={saveNext} disabled={saving}
                  data-testid="escrow-wiz-next"
                  className="px-5 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
            {saving ? "Saving…" : nextLabel}
          </button>
        </div>
      </div>
    </div>
  );
}


function WField({ label, v, on }) {
  return (
    <label className="block">
      <span className="block text-[10px] uppercase tracking-widest text-brand-navy/70">{label}</span>
      <input value={v || ""} onChange={(e) => on(e.target.value)}
             className="mt-1 w-full px-3 py-2 border border-brand-navy/20 focus:outline-none focus:border-brand-gold" />
    </label>
  );
}


function DocSlot({ slot, label, current, institutionId, onUploaded, onRemoved }) {
  const [busy, setBusy] = useState(false);
  const upload = async (file) => {
    setBusy(true);
    try {
      const meta = await uploadsApi.uploadFile(file, { scope: "escrow-docs" });
      await onUploaded?.(meta);
      toast.success(`${label}: uploaded`);
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };
  return (
    <div className="flex items-center justify-between bg-white p-3 border border-brand-navy/15"
         data-testid={`escrow-doc-${slot}`}>
      <div className="min-w-0">
        <div className="text-sm text-brand-navy truncate">{label}</div>
        {current?.filename && (
          <div className="text-[11px] text-brand-navy/50 truncate">{current.filename}</div>
        )}
      </div>
      <div className="flex gap-2 shrink-0 ml-2">
        <label className="px-3 py-1 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy cursor-pointer hover:bg-brand-pale">
          {busy ? "…" : current ? "Replace" : "Upload"}
          <input type="file" className="hidden"
                 onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} />
        </label>
        {current && (
          <button type="button" onClick={() => onRemoved?.()}
                  className="px-2 py-1 text-[11px] text-red-700 hover:underline">
            Remove
          </button>
        )}
      </div>
    </div>
  );
}
