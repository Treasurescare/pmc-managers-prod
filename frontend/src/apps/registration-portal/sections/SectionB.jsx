import { Field, Input, EmailInput, PhoneWithIsd } from "./FormPrimitives";
import { DocSlotsBlock } from "./DocSlot";
import { useI18n } from "@/context/I18nContext";

export default function SectionB({ reg, update, regId, token, onDocChange, ensureDraft, countries }) {
  const { t } = useI18n();
  const slots = [
    ["previous_works", { label: t("section_b.doc_previous_works"), required: true }],
    ["iso_certificates", { label: t("section_b.doc_iso_certificates"), required: false }],
    ["licenses_permits", { label: t("section_b.doc_licenses_permits"), required: true }],
  ];
  return (
    <>
      <div className="grid gap-5 md:grid-cols-2">
        <Field label={t("section_b.contact_name")} required><Input testId="f-contact-name" value={reg.contact_name || ""} onChange={(e) => update({ contact_name: e.target.value })} /></Field>
        <Field label={t("section_b.contact_title")}><Input testId="f-contact-title" value={reg.contact_title || ""} onChange={(e) => update({ contact_title: e.target.value })} /></Field>
        <Field label={t("section_b.office_phone")}><PhoneWithIsd testId="f-contact-phone" value={reg.contact_office_phone || ""} onChange={(e) => update({ contact_office_phone: e.target.value })} countries={countries} defaultCountry={reg.country} /></Field>
        <Field label={t("section_b.mobile")} required><PhoneWithIsd testId="f-contact-mobile" value={reg.contact_mobile || ""} onChange={(e) => update({ contact_mobile: e.target.value })} countries={countries} defaultCountry={reg.country} /></Field>
        <Field label={t("section_b.contact_email")} required><EmailInput testId="f-contact-email" value={reg.contact_email || ""} onChange={(e) => update({ contact_email: e.target.value })} /></Field>
        <div />
        <Field label={t("section_b.signatory_name")} required><Input testId="f-sig-name" value={reg.signatory_name || ""} onChange={(e) => update({ signatory_name: e.target.value })} /></Field>
        <Field label={t("section_b.signatory_title")}><Input testId="f-sig-title" value={reg.signatory_title || ""} onChange={(e) => update({ signatory_title: e.target.value })} /></Field>
        <Field label={t("section_b.signatory_contact")} required><PhoneWithIsd testId="f-sig-contact" value={reg.signatory_contact || ""} onChange={(e) => update({ signatory_contact: e.target.value })} countries={countries} defaultCountry={reg.country} /></Field>
      </div>
      <DocSlotsBlock
        title={t("section_b.docs_title")}
        regId={regId} token={token} ensureDraft={ensureDraft}
        slots={slots}
        existing={reg.document_slots || {}}
        onChange={onDocChange}
      />
    </>
  );
}
