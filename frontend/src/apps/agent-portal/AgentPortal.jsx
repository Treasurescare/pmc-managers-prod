import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { agentApi, showApiError } from "@/lib/api";
import EscrowCoreForm from "@/apps/escrow-portal/EscrowCoreForm";
import EscrowBankingStep from "@/apps/escrow-portal/EscrowBankingStep";
import { AgentAgreementStep, AgentDocsStep } from "./AgentSteps";

const STEPS = ["Profile", "Banking", "Documents", "Agreement"];
const BANK = { account_name: "", account_number: "", iban: "", swift: "", currency: "USD", institution_name: "", branch: "",
  bank_country: "", bank_state: "", bank_city: "", bank_code: "", sort_code: "", routing_number: "" };
const STATUS = {
  submitted: ["Under review", "PMC is reviewing your agent profile. We'll email you when it's done."],
  approved: ["Approved", "You're an approved PMC onboarding agent. Supplier onboarding tools arrive in the next release."],
  rejected: ["Not approved", "Your application was not approved."],
};

export default function AgentPortal() {
  const nav = useNavigate();
  const [form, setForm] = useState(null);
  const [step, setStep] = useState(0);
  const [saving, setSaving] = useState(false);
  const formRef = useRef(null);
  formRef.current = form;
  useEffect(() => {
    agentApi.me().then((a) => setForm({ ...a, entity_type: a.entity_type || "individual", banking: a.banking?.length ? a.banking : [{ ...BANK }] }))
      .catch(() => nav("/agent/login"));
  }, []); // eslint-disable-line react-hooks/exhaustive-deps
  if (!form) return <div className="p-10 text-brand-navy/50">Loading…</div>;
  const set = (k, v) => setForm((f) => ({ ...f, [k]: v }));
  const persist = async (advance) => {
    setSaving(true);
    try {
      const { entity_type, banking, documents, history, agreement, id, email, status, ...rest } = formRef.current; // eslint-disable-line no-unused-vars
      await agentApi.saveProfile({ ...rest, entity_type, banking: banking.filter((b) => b.account_name || b.account_number || b.iban) });
      toast.success("Saved");
      if (advance) setStep((s) => Math.min(3, s + 1));
    } catch (e) { showApiError(e); } finally { setSaving(false); }
  };
  const submit = async () => {
    try { await agentApi.submit(); setForm((f) => ({ ...f, status: "submitted" })); toast.success("Submitted for PMC review"); } catch (e) { showApiError(e); }
  };
  const logout = async () => { await agentApi.logout().catch(() => {}); nav("/agent/login"); };
  const locked = !["draft", "needs_clarification"].includes(form.status);
  const lastNote = [...(form.history || [])].reverse().find((h) => h.note);
  return (
    <div className="max-w-4xl mx-auto p-6 space-y-5" data-testid="agent-portal">
      <div className="flex justify-between items-start gap-3 flex-wrap">
        <div><div className="text-[11px] uppercase tracking-widest text-brand-navy/60">PMC onboarding agent</div>
          <h1 className="font-serif text-2xl text-brand-navy">{form.legal_name || form.name}</h1>
          <div className="text-sm text-brand-navy/70">{form.email} · status <b data-testid="agent-status">{form.status.replace("_", " ")}</b></div></div>
        <button className="pmc-btn pmc-btn--secondary" onClick={logout} data-testid="agent-logout">Sign out</button>
      </div>
      {form.status === "needs_clarification" && lastNote && <div className="bg-amber-50 border border-amber-300 p-3 text-sm" data-testid="agent-clarify-note"><b>PMC asked for changes:</b> {lastNote.note}</div>}
      {locked ? (
        <div className="bg-white border border-brand-navy/15 p-6" data-testid="agent-status-card">
          <h2 className="text-lg font-semibold">{(STATUS[form.status] || [form.status])[0]}</h2>
          <p className="text-sm text-brand-navy/70 mt-1">{(STATUS[form.status] || ["", ""])[1]}</p>
          {form.status === "rejected" && lastNote && <p className="text-sm mt-2">Reason: {lastNote.note}</p>}
        </div>
      ) : <>
        <div className="flex gap-2 text-[11px] uppercase tracking-widest flex-wrap">
          {STEPS.map((s, i) => (
            <button key={s} type="button" onClick={() => setStep(i)} data-testid={`agent-step-${i}`}
                    className={"px-3 py-1 border " + (step === i ? "bg-brand-navy text-white border-brand-navy" : "bg-white text-brand-navy/60 border-brand-navy/15")}>{i + 1}. {s}</button>))}
        </div>
        {step === 0 && <>
          <div className="flex gap-4 text-sm" data-testid="agent-entity-type">
            {["individual", "company"].map((t) => (
              <label key={t} className="flex gap-2 items-center"><input type="radio" checked={form.entity_type === t} onChange={() => set("entity_type", t)} data-testid={`agent-entity-${t}`} />{t === "individual" ? "I'm an individual" : "We're a company"}</label>))}
          </div>
          <EscrowCoreForm form={form} set={set} onNext={() => setTimeout(() => persist(true), 0)} saving={saving} individual={form.entity_type === "individual"} />
        </>}
        {step === 1 && <EscrowBankingStep banking={form.banking} onChange={(next) => set("banking", next)} />}
        {step === 2 && <AgentDocsStep form={form} setForm={setForm} />}
        {step === 3 && <AgentAgreementStep form={form} setForm={setForm} />}
        {step > 0 && <div className="flex justify-between gap-2 flex-wrap">
          <button type="button" className="pmc-btn pmc-btn--secondary" disabled={step === 0} onClick={() => setStep(step - 1)} data-testid="agent-back">Back</button>
          <div className="flex gap-2">
            {step < 2 && <button type="button" className="pmc-btn pmc-btn--secondary" disabled={saving} onClick={() => persist(false)} data-testid="agent-save-draft">Save draft</button>}
            {step < 3 ? <button type="button" className="pmc-btn pmc-btn--primary" disabled={saving} onClick={() => (step < 2 ? persist(true) : setStep(3))} data-testid="agent-next">Save & continue</button>
              : <button type="button" className="pmc-btn pmc-btn--primary" onClick={submit} data-testid="agent-submit">Submit for PMC review</button>}
          </div>
        </div>}
      </>}
    </div>
  );
}
