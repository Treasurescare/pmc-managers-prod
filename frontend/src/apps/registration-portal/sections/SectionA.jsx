import { Field, Input } from "./FormPrimitives";
import { DocSlotsBlock } from "./DocSlot";

const SECTION_A_SLOTS = [
  ["incorporation_certificate", { label: "Incorporation Certificate", required: true }],
  ["address_proof", { label: "Address Proof (utility bill / lease deed)", required: true }],
  ["tin_proof", { label: "TIN / VAT Proof", required: true }],
  ["audited_financials", { label: "Audited Financial Statements (last 3 years)", required: false }],
];

export default function SectionA({ reg, update, countries, regId, token, onDocChange }) {
  return (
    <>
      <div className="grid gap-5 md:grid-cols-2">
        <Field label="Company name">
          <Input testId="f-company-name" value={reg.company_name || ""} onChange={(e) => update({ company_name: e.target.value })} />
        </Field>
        <Field label="Trade name">
          <Input testId="f-trade-name" value={reg.trade_name || ""} onChange={(e) => update({ trade_name: e.target.value })} />
        </Field>
        <Field label="Registered address">
          <Input testId="f-registered-address" value={reg.registered_address || ""} onChange={(e) => update({ registered_address: e.target.value })} />
        </Field>
        <Field label="Mailing address">
          <Input testId="f-mailing-address" value={reg.mailing_address || ""} onChange={(e) => update({ mailing_address: e.target.value })} />
        </Field>
        <Field label="Country">
          <select data-testid="f-country" value={reg.country || "KZ"} onChange={(e) => update({ country: e.target.value })}
            className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
            {countries.map((c) => (<option key={c.code} value={c.code}>{c.name}</option>))}
          </select>
        </Field>
        <Field label="Registration number">
          <Input testId="f-reg-number" value={reg.registration_number || ""} onChange={(e) => update({ registration_number: e.target.value })} />
        </Field>
        <Field label="Incorporation date">
          <Input testId="f-incorp-date" type="date" value={reg.incorporation_date || ""} onChange={(e) => update({ incorporation_date: e.target.value })} />
        </Field>
        <Field label="Tax ID">
          <Input testId="f-tax-id" value={reg.tax_id || ""} onChange={(e) => update({ tax_id: e.target.value })} />
        </Field>
        <Field label="Legal entity type">
          <select data-testid="f-legal-type" value={reg.legal_entity_type || ""} onChange={(e) => update({ legal_entity_type: e.target.value })}
            className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
            <option value="">—</option>
            <option>LLC</option><option>JSC</option><option>Sole Proprietorship</option><option>Partnership</option><option>Branch</option><option>Other</option>
          </select>
        </Field>
        <Field label="Website">
          <Input testId="f-website" value={reg.website || ""} onChange={(e) => update({ website: e.target.value })} />
        </Field>
        <Field label="Employees count">
          <Input testId="f-employees" type="number" value={reg.employees_count || ""} onChange={(e) => update({ employees_count: parseInt(e.target.value || "0", 10) || null })} />
        </Field>
      </div>
      <DocSlotsBlock
        title="Identity & KYC documents (Section A)"
        regId={regId} token={token}
        slots={SECTION_A_SLOTS}
        existing={reg.document_slots || {}}
        onChange={onDocChange}
      />
    </>
  );
}
