import { useEffect, useState } from "react";
import { toast } from "sonner";
import { agentApi, uploadsApi, showApiError } from "@/lib/api";

const DOCS = {
  individual: [["id_proof", "Passport / national ID"], ["address_proof", "Proof of address (utility bill or bank statement)"],
    ["bank_proof", "Bank letter or cancelled cheque"], ["tax_registration", "Tax registration (optional)"], ["photo", "Photograph (optional)"]],
  company: [["incorporation_certificate", "Certificate of incorporation"], ["tax_registration", "Tax / GST / VAT registration"],
    ["authority_letter", "Board resolution / letter authorising the signatory"], ["id_proof", "Signatory's passport / national ID"],
    ["address_proof", "Company proof of address"], ["bank_proof", "Bank letter or cancelled cheque"], ["other", "Other supporting document (optional)"]],
};

export const REQUIRED_DOCS = (et) => ["id_proof", "address_proof", "bank_proof", ...(et === "company" ? ["incorporation_certificate", "tax_registration", "authority_letter"] : [])];

export const missingItems = (f) => {
  const out = [];
  [["legal_name", "Legal name"], ["country", "Country"], ["address_line1", "Address"], ["city", "City"], ["primary_contact_phone", "Mobile number"]]
    .forEach(([k, l]) => { if (!f[k]) out.push([0, l]); });
  if (f.entity_type === "company" && !f.reg_number) out.push([0, "Company registration number"]);
  if (!(f.banking || []).some((b) => b.account_name && (b.account_number || b.iban))) out.push([1, "Bank account (name and number or IBAN)"]);
  const labels = Object.fromEntries(DOCS[f.entity_type || "individual"]);
  REQUIRED_DOCS(f.entity_type).forEach((d) => { if (!f.documents?.[d]?.key) out.push([2, labels[d] || d]); });
  return out;
};

export const AgentDocsStep = ({ form, setForm, onSave }) => {
  const [busy, setBusy] = useState("");
  const slots = DOCS[form.entity_type || "individual"];
  const req = REQUIRED_DOCS(form.entity_type);
  const save = async (documents) => {
    setForm((f) => ({ ...f, documents }));
    try { await (onSave || agentApi.saveProfile)({ documents }); } catch (e) { showApiError(e); }
  };
  const upload = async (slot, file) => {
    setBusy(slot);
    try {
      const meta = await uploadsApi.uploadFile(file, { scope: "agent-docs" });
      await save({ ...(form.documents || {}), [slot]: meta });
      toast.success("Uploaded");
    } catch (e) { showApiError(e); } finally { setBusy(""); }
  };
  return (
    <div className="grid gap-2" data-testid="agent-docs-step">
      <div className="text-xs text-brand-navy/70 mb-1">Upload your {form.entity_type === "company" ? "company and signatory" : "personal"} KYC documents. Only PMC reviewers can open them.</div>
      {slots.map(([slot, label]) => {
        const cur = form.documents?.[slot];
        return (
          <div key={slot} className="flex items-center justify-between bg-white p-3 border border-brand-navy/15" data-testid={`agent-doc-${slot}`}>
            <div className="min-w-0"><div className="text-sm truncate">{label}{req.includes(slot) && <span className="text-red-700"> *</span>}{req.includes(slot) && !cur?.key && <span className="ml-2 text-[10px] uppercase tracking-widest text-red-700" data-testid={`agent-doc-required-${slot}`}>Required</span>}</div>{cur?.filename && <div className="text-[11px] text-brand-navy/50 truncate">{cur.filename}</div>}</div>
            <div className="flex gap-2 shrink-0 ml-2">
              {cur?.key && <button type="button" className="px-3 py-1 text-[11px] uppercase border border-brand-navy/40" onClick={() => uploadsApi.openFile(cur.key).catch(showApiError)}>View</button>}
              <label className="px-3 py-1 text-[11px] uppercase border border-brand-navy/40 cursor-pointer">
                {busy === slot ? "…" : cur ? "Replace" : "Upload"}
                <input type="file" className="hidden" onChange={(e) => e.target.files?.[0] && upload(slot, e.target.files[0])} data-testid={`agent-doc-input-${slot}`} />
              </label>
              {cur && <button type="button" className="text-[11px] text-red-700" onClick={() => { const d = { ...form.documents }; delete d[slot]; save(d); }}>Remove</button>}
            </div>
          </div>
        );
      })}
    </div>
  );
};

const CONSENT_LABEL = {
  supplier_consent: "I will get each supplier's written consent before entering their details or documents.",
  data_privacy: "I will protect supplier data and use it only for their PMC registration.",
  confidentiality: "I will keep all PMC, supplier and tender information confidential (NDA).",
  indemnity: "I am responsible for my own conduct and will indemnify PMC for any loss caused by my wrongdoing.",
  anti_bribery: "I will not offer or accept bribes or promise any tender outcome.",
  accuracy: "The information and documents I have given PMC about myself are true and complete.",
};

export const AgentAgreementStep = ({ form, setForm }) => {
  const [doc, setDoc] = useState(null);
  const [name, setName] = useState("");
  const [ticks, setTicks] = useState({});
  const [busy, setBusy] = useState(false);
  useEffect(() => { agentApi.agreement().then(setDoc).catch(showApiError); }, []);
  if (!doc) return null;
  const signed = form.agreement?.version === doc.version;
  const sign = async () => {
    setBusy(true);
    try { const r = await agentApi.sign(name, ticks); setForm((f) => ({ ...f, agreement: r.agreement })); toast.success("Agreement signed"); }
    catch (e) { showApiError(e); } finally { setBusy(false); }
  };
  return (
    <div className="space-y-3" data-testid="agent-agreement-step">
      <div className="bg-white border border-brand-navy/15 p-4 max-h-80 overflow-y-auto text-sm space-y-2" data-testid="agent-agreement-text">
        <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">Onboarding agent agreement · version {doc.version}</div>
        {doc.sections.map((s) => <p key={s.title}><b>{s.title}.</b> {s.text}</p>)}
      </div>
      {signed ? (
        <div className="bg-emerald-50 border border-emerald-300 p-3 text-sm" data-testid="agent-agreement-signed">
          Signed by <b>{form.agreement.signer_name}</b> on {form.agreement.signed_at.slice(0, 16).replace("T", " ")} UTC.
        </div>
      ) : (
        <div className="space-y-2">
          {doc.consent_keys.map((k) => (
            <label key={k} className="flex gap-2 text-sm items-start"><input type="checkbox" checked={!!ticks[k]} onChange={(e) => setTicks({ ...ticks, [k]: e.target.checked })} data-testid={`agent-consent-${k}`} />{CONSENT_LABEL[k]}</label>
          ))}
          <input className="w-full px-3 py-2 border border-brand-navy/20" placeholder="Type your full name as your signature" value={name} onChange={(e) => setName(e.target.value)} data-testid="agent-agreement-name" />
          <button type="button" className="pmc-btn pmc-btn--primary" disabled={busy || name.trim().length < 3 || !doc.consent_keys.every((k) => ticks[k])} onClick={sign} data-testid="agent-agreement-sign">
            {busy ? "Signing…" : "Sign agreement"}
          </button>
        </div>
      )}
    </div>
  );
};
