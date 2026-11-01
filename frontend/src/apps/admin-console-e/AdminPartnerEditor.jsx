import { useRef, useState } from "react";
import { toast } from "sonner";
import { agentApi, showApiError } from "@/lib/api";
import EscrowCoreForm from "@/apps/escrow-portal/EscrowCoreForm";
import EscrowBankingStep from "@/apps/escrow-portal/EscrowBankingStep";
import { AgentDocsStep, missingItems } from "@/apps/agent-portal/AgentSteps";

const STEPS = ["Type", "Profile", "Banking", "Documents", "Agreement"];
const BANK = { account_name: "", account_number: "", iban: "", swift: "", currency: "USD", institution_name: "", branch: "",
  bank_country: "", bank_state: "", bank_city: "", bank_code: "", sort_code: "", routing_number: "" };

const AgreementStatus = ({ a }) => (
  <div className="bg-white border border-brand-navy/15 p-4 text-sm space-y-1" data-testid="admin-partner-agreement">
    {a.agreement?.version ? <>Signed by <b>{a.agreement.signer_name}</b> on {a.agreement.signed_at?.slice(0, 16).replace("T", " ")} UTC (version {a.agreement.version}).</>
      : <>The partner agreement is <b>not signed</b>. Only the partner can sign it, from their own sign-in — send them a reminder.</>}
  </div>);

export default function AdminPartnerEditor({ a, onSaved, onClose }) {
  const [form, setForm] = useState(() => ({ ...a, entity_type: a.entity_type || "individual", banking: a.banking?.length ? a.banking : [{ ...BANK }] }));
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const ref = useRef(form);
  ref.current = form;
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const save = (body) => agentApi.adminEdit(a.id, body);
  const persist = async (advance) => {
    setSaving(true);
    try {
      const { id, email, status, history, agreement, documents, partner_code, payment, created_at, updated_at, joined_at, ...rest } = ref.current; // eslint-disable-line no-unused-vars
      await save({ ...rest, banking: (rest.banking || []).filter((b) => b.account_name || b.account_number || b.iban) });
      toast.success("Partner details saved");
      onSaved();
      if (advance) setStep((s) => Math.min(STEPS.length - 1, s + 1));
    } catch (e) { showApiError(e); } finally { setSaving(false); }
  };
  const missing = missingItems(form);
  return (
    <div className="border border-brand-navy/15 p-4 space-y-4 bg-brand-pale/30" data-testid="admin-agent-edit">
      <div className="flex justify-between items-center flex-wrap gap-2">
        <div className="flex gap-2 text-[11px] uppercase tracking-widest flex-wrap">
          {STEPS.map((s, i) => (
            <button key={s} type="button" onClick={() => setStep(i)} data-testid={`admin-agent-step-${i}`}
                    className={"px-3 py-1 border " + (step === i ? "bg-brand-navy text-white border-brand-navy" : "bg-white text-brand-navy/60 border-brand-navy/15")}>{i + 1}. {s}</button>))}
        </div>
        <button type="button" className="text-xs underline" onClick={onClose} data-testid="admin-agent-edit-close">Close</button>
      </div>
      {step === 0 && (
        <div className="flex gap-4 text-sm" data-testid="admin-agent-entity-type">
          {["individual", "company"].map((t) => (
            <label key={t} className="flex gap-2 items-center"><input type="radio" checked={form.entity_type === t} onChange={() => set("entity_type", t)} data-testid={`admin-agent-entity-${t}`} />{t === "individual" ? "Individual" : "Company"}</label>))}
        </div>)}
      {step === 1 && <EscrowCoreForm form={form} set={set} onNext={() => setTimeout(() => persist(true), 0)} saving={saving} individual={form.entity_type === "individual"} />}
      {step === 2 && <EscrowBankingStep banking={form.banking} onChange={(next) => set("banking", next)} />}
      {step === 3 && <AgentDocsStep form={form} setForm={setForm} onSave={(b) => save(b).then(onSaved)} />}
      {step === 4 && <AgreementStatus a={a} />}
      {missing.length > 0 && step === 4 && (
        <div className="bg-amber-50 border border-amber-300 p-3 text-sm space-y-1" data-testid="admin-agent-missing">
          <b>Still missing before the partner can submit:</b>
          {missing.map(([s, l]) => <div key={l}>• {l} <button type="button" className="underline text-xs" onClick={() => setStep(s + 1)}>Go to {STEPS[s + 1]}</button></div>)}
        </div>)}
      {step !== 1 && step !== 3 && step !== 4 && (
        <div className="flex justify-end gap-2">
          <button type="button" className="pmc-btn pmc-btn--secondary" disabled={saving} onClick={() => persist(false)} data-testid="admin-agent-edit-save">Save</button>
          <button type="button" className="pmc-btn pmc-btn--primary" disabled={saving} onClick={() => persist(true)} data-testid="admin-agent-edit-next">Save & continue</button>
        </div>)}
      {step === 3 && <div className="flex justify-end"><button type="button" className="pmc-btn pmc-btn--primary" onClick={() => setStep(4)} data-testid="admin-agent-docs-next">Continue</button></div>}
    </div>);
}
