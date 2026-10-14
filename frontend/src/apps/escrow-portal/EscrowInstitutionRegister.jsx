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
  // v52cz rev4 — structured address pieces (country→state→city→zip→addr1/2)
  address_line1: "", address_line2: "", city: "",
  state_code: "", state_name: "", postal_code: "",
  reg_number: "", tax_id: "", gst_or_vat: "", regulator: "",
  licence_number: "", licence_expiry: "", website: "",
  primary_contact_email: "", primary_contact_phone: "", phone_country_code: "",
  signatories: [{ name: "", designation: "", email: "", phone: "" }],
  // v52cz rev6 — new fields: dual phones + bank_country/state/city per row.
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

export default function EscrowInstitutionRegister() {
  const [form, setForm] = useState(EMPTY);
  const [step, setStep] = useState(1);
  const [registration, setRegistration] = useState(null); // {id, magic_token}
  const [saving, setSaving] = useState(false);
  const [viewer, setViewer] = useState(null); // {href, title}
  const [allCountries, setAllCountries] = useState([]);
  useEffect(() => { mastersApi.listCountriesPublic().then(setAllCountries).catch(() => setAllCountries([])); }, []);
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  // v52cz rev5 — drop scaffold rows that are completely empty before
  // sending. A fresh form starts with one blank signatory + one blank bank
  // row; sending them as-is 422s on EmailStr / wastes DB rows.
  const cleanPayload = (f) => ({
    ...f,
    signatories: (f.signatories || []).filter((s) => (s.name || "").trim() || (s.email || "").trim()),
    banking: (f.banking || []).filter((b) =>
      (b.account_name || "").trim() || (b.account_number || "").trim() ||
      (b.institution_name || "").trim()),
  });

  // v52cz rev6 — unified persist that works at any step.
  // `advance`: true → go to next step, false → stay (Save as draft).
  // Also lazily creates the draft on step 1 if we don't have an id yet.
  const persist = async ({ advance }) => {
    setSaving(true);
    try {
      if (!registration) {
        const r = (await api.post("/api/v1/escrow-institutions/register",
                                  cleanPayload(form))).data;
        setRegistration(r);
      } else {
        await api.patch(`/api/v1/escrow-institutions/${registration.id}`,
                        cleanPayload(form),
                        { params: { token: registration.magic_token } });
      }
      toast.success(advance ? "Saved" : "Draft saved");
      if (advance) setStep((s) => Math.min(5, s + 1));
    } catch (e) { showApiError(e); }
    finally { setSaving(false); }
  };

  const createDraft = () => persist({ advance: true });
  const saveStep = () => persist({ advance: true });
  const saveDraft = () => persist({ advance: false });
  const goBack = () => setStep((s) => Math.max(1, s - 1));

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
        <>
          <EscrowCoreForm form={form} set={set} onNext={createDraft} saving={saving} />
          {/* v52cz rev6 — Save as draft on step 1 too (no Back since first step) */}
          <div className="flex justify-end mt-3">
            <button type="button" onClick={saveDraft} disabled={saving}
                    data-testid="escrow-reg-draft-1"
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
            <div key={i} className="grid md:grid-cols-4 gap-3 border-b pb-3 mb-3"
                 data-testid={`escrow-sig-row-${i}`}>
              <Input label="Name" v={s.name} on={(x) => { const a=[...form.signatories]; a[i].name=x; set("signatories",a); }} />
              <Input label="Designation" v={s.designation} on={(x) => { const a=[...form.signatories]; a[i].designation=x; set("signatories",a); }} />
              <Input label="Email" v={s.email} on={(x) => { const a=[...form.signatories]; a[i].email=x; set("signatories",a); }} />
              <div>
                <div className="pmc-label text-[10px]">Phone</div>
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
          <button onClick={addSignatory} className="text-xs uppercase tracking-widest text-brand-navy hover:underline">
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
                       institutionId={registration?.id}
                       token={registration?.magic_token}
                       onView={(href) => setViewer({ href, title: label })}
                       onUploaded={async (meta) => {
                         const next = { ...(form.documents || {}), [slot]: meta };
                         const nf = { ...form, documents: next };
                         setForm(nf);
                         if (registration) {
                           try {
                             await api.patch(`/api/v1/escrow-institutions/${registration.id}`,
                                             nf, { params: { token: registration.magic_token } });
                           } catch (e) { /* best-effort — toast on upload is enough */ }
                         }
                       }}
                       onRemoved={async () => {
                         const next = { ...(form.documents || {}) };
                         delete next[slot];
                         const nf = { ...form, documents: next };
                         setForm(nf);
                         if (registration) {
                           try {
                             await api.patch(`/api/v1/escrow-institutions/${registration.id}`,
                                             nf, { params: { token: registration.magic_token } });
                           } catch (e) { /* ignore */ }
                         }
                       }}
              />
            ))}
          </div>
        </StepShell>
      )}

      {step === 5 && (
        <div className="bg-emerald-50 border border-emerald-300 p-8 text-center">
          <h2 className="text-xl font-semibold text-emerald-900">Submitted ✓</h2>
          <p className="text-sm text-emerald-800 mt-2">
            PMC will email {form.primary_contact_email} within 3 business days.
          </p>
        </div>
      )}

      {/* v52cz rev7 — in-page document viewer modal. View no longer opens
          a bare browser tab; it iframes the PDF beside the form so users
          stay in context. */}
      {viewer && (
        <div className="fixed inset-0 z-50 bg-black/60 flex items-center justify-center p-4"
             data-testid="escrow-doc-viewer"
             onClick={() => setViewer(null)}>
          <div className="bg-white w-full max-w-4xl h-[85vh] flex flex-col"
               onClick={(e) => e.stopPropagation()}>
            <div className="flex items-center justify-between border-b border-brand-navy/15 px-4 py-2">
              <div className="text-sm font-semibold text-brand-navy">{viewer.title}</div>
              <div className="flex gap-2">
                <a href={viewer.href + "&download=1"}
                   className="px-3 py-1 text-xs uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-pale"
                   data-testid="escrow-doc-viewer-download">
                  Download
                </a>
                <button type="button" onClick={() => setViewer(null)}
                        data-testid="escrow-doc-viewer-close"
                        className="px-3 py-1 text-xs uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
                  Close
                </button>
              </div>
            </div>
            <iframe src={viewer.href} title={viewer.title} className="flex-1 w-full" />
          </div>
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

/**
 * v52cz rev6 — StepShell wraps every registration step with the same
 * Back + Save as draft + Save & continue toolbar. Previously only step 1
 * had a next button, Back was impossible, and there was no draft-save,
 * which blocked institutions from pausing mid-registration.
 */
function StepShell({ children, canBack, goBack, saveDraft, saveNext,
                     saving, nextLabel = "Save and continue" }) {
  return (
    <div className="bg-white p-6 border border-brand-navy/15">
      {children}
      <div className="flex items-center justify-between mt-6 pt-4 border-t border-brand-navy/10 flex-wrap gap-3">
        {canBack ? (
          <button type="button" onClick={goBack} disabled={saving}
                  data-testid="escrow-reg-back"
                  className="px-5 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-pale disabled:opacity-50">
            ← Previous
          </button>
        ) : <span />}
        <div className="flex items-center gap-3 ml-auto">
          <button type="button" onClick={saveDraft} disabled={saving}
                  data-testid="escrow-reg-draft"
                  className="px-5 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy hover:text-white disabled:opacity-50">
            {saving ? "Saving…" : "Save as draft"}
          </button>
          <button type="button" onClick={saveNext} disabled={saving}
                  data-testid="escrow-reg-next"
                  className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
            {saving ? "Saving…" : nextLabel}
          </button>
        </div>
      </div>
    </div>
  );
}

function DocSlot({ slot, label, current, onUploaded, onRemoved, onView,
                   institutionId, token }) {
  const [busy, setBusy] = useState(false);
  const viewHref = () => institutionId && token
    ? `/api/v1/escrow-institutions/${institutionId}/documents/${slot}/file?token=${encodeURIComponent(token)}`
    : "#";
  const upload = async (file) => {
    if (!file) return;
    setBusy(true);
    try {
      const p = await uploadsApi.presign(file.name, file.type || "application/pdf",
                                          "escrow-inst", file.size);
      const r = await uploadsApi.direct(p.key, file);
      const key = r?.key || p?.key;
      if (!key) { toast.error(`Upload failed for ${file.name}`); return; }
      await onUploaded({
        key, filename: file.name,
        size_bytes: r?.size_bytes ?? file.size,
        uploaded_at: new Date().toISOString(),
      });
      toast.success(`Uploaded ${file.name}`);
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };
  return (
    <div className="border border-brand-navy/10 p-3 flex items-center justify-between gap-3 flex-wrap"
         data-testid={`escrow-doc-slot-${slot}`}>
      <div className="min-w-0">
        <div className="text-sm font-medium text-brand-navy">{label}</div>
        {current ? (
          <div className="text-xs text-brand-navy/60 truncate">
            {current.filename} · {(current.size_bytes / 1024).toFixed(1)} KB
          </div>
        ) : (
          <div className="text-xs text-brand-navy/40 italic">Not uploaded yet</div>
        )}
      </div>
      <div className="flex gap-2">
        {current?.key && (
          // v52cz rev7 — open the in-page modal viewer instead of navigating
          // the browser to a bare file URL. Keeps the user on the form.
          <button type="button"
             onClick={() => onView && onView(viewHref())}
             data-testid={`escrow-doc-view-${slot}`}
             className="text-[10px] uppercase tracking-widest px-3 py-1.5 border border-brand-navy/20 hover:bg-brand-navy/5">
            View
          </button>
        )}
        {current ? (
          <button onClick={onRemoved} disabled={busy}
                  data-testid={`escrow-doc-remove-${slot}`}
                  className="text-[10px] uppercase tracking-widest px-3 py-1.5 border border-red-300 text-red-700 hover:bg-red-50 disabled:opacity-50">
            Remove
          </button>
        ) : (
          <label className="text-[10px] uppercase tracking-widest px-3 py-1.5 bg-brand-navy text-white cursor-pointer disabled:opacity-50">
            {busy ? "Uploading…" : "Upload"}
            <input type="file" className="hidden" disabled={busy}
                   data-testid={`escrow-doc-upload-${slot}`}
                   onChange={(e) => upload(e.target.files?.[0])} />
          </label>
        )}
      </div>
    </div>
  );
}
