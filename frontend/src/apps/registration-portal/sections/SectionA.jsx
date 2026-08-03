import { Field, Input } from "./FormPrimitives";
import { DocSlotsBlock } from "./DocSlot";
import { useI18n } from "@/context/I18nContext";

const LEGAL_TYPES = ["", "LLC", "JSC", "Sole Proprietorship", "Partnership", "Branch", "Other"];

export default function SectionA({ reg, update, countries, regId, token, onDocChange }) {
  const { t } = useI18n();
  const slots = [
    ["incorporation_certificate", { label: t("section_a.doc_incorporation_certificate"), required: true }],
    ["address_proof", { label: t("section_a.doc_address_proof"), required: true }],
    ["tin_proof", { label: t("section_a.doc_tin_proof"), required: true }],
    ["audited_financials", { label: t("section_a.doc_audited_financials"), required: false }],
  ];
  return (
    <>
      <div className="grid gap-5 md:grid-cols-2">
        <Field label={t("section_a.company_name")}>
          <Input testId="f-company-name" value={reg.company_name || ""} onChange={(e) => update({ company_name: e.target.value })} />
        </Field>
        <Field label={t("section_a.trade_name")}>
          <Input testId="f-trade-name" value={reg.trade_name || ""} onChange={(e) => update({ trade_name: e.target.value })} />
        </Field>
        <Field label={t("section_a.registered_address")}>
          <Input testId="f-registered-address" value={reg.registered_address || ""} onChange={(e) => update({ registered_address: e.target.value })} />
        </Field>
        <Field label={t("section_a.mailing_address")}>
          <Input testId="f-mailing-address" value={reg.mailing_address || ""} onChange={(e) => update({ mailing_address: e.target.value })} />
        </Field>
        <Field label={t("section_a.country")}>
          <select data-testid="f-country" value={reg.country || "KZ"} onChange={(e) => update({ country: e.target.value })}
            className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
            {countries.map((c) => (<option key={c.code} value={c.code}>{c.name}</option>))}
          </select>
        </Field>
        <Field label={t("section_a.registration_number")}>
          <Input testId="f-reg-number" value={reg.registration_number || ""} onChange={(e) => update({ registration_number: e.target.value })} />
        </Field>
        <Field label={t("section_a.incorporation_date")}>
          <Input testId="f-incorp-date" type="date" value={reg.incorporation_date || ""} onChange={(e) => update({ incorporation_date: e.target.value })} />
        </Field>
        <Field label={t("section_a.tax_id")}>
          <Input testId="f-tax-id" value={reg.tax_id || ""} onChange={(e) => update({ tax_id: e.target.value })} />
        </Field>
        <Field label={t("section_a.legal_entity_type")}>
          <select data-testid="f-legal-type" value={reg.legal_entity_type || ""} onChange={(e) => update({ legal_entity_type: e.target.value })}
            className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
            {LEGAL_TYPES.map((opt) => (
              <option key={opt || "empty"} value={opt}>
                {t(`section_a.legal_type_options.${opt}`, opt || "—")}
              </option>
            ))}
          </select>
        </Field>
        <Field label={t("section_a.website")}>
          <Input testId="f-website" value={reg.website || ""} onChange={(e) => update({ website: e.target.value })} />
        </Field>
        <Field label={t("section_a.employees_count")}>
          <Input testId="f-employees" type="number" value={reg.employees_count || ""} onChange={(e) => update({ employees_count: parseInt(e.target.value || "0", 10) || null })} />
        </Field>
      </div>
      <DocSlotsBlock
        title={t("section_a.docs_title")}
        regId={regId} token={token}
        slots={slots}
        existing={reg.document_slots || {}}
        onChange={onDocChange}
      />
    </>
  );
}
