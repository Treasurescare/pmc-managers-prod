import { Field, Input } from "./FormPrimitives";
import { DocSlotsBlock } from "./DocSlot";

const SECTION_B_SLOTS = [
  ["previous_works", { label: "Previous Works Completed", required: true }],
  ["iso_certificates", { label: "ISO / Quality Certifications", required: false }],
  ["licenses_permits", { label: "Licenses / Permits / Regulatory Authorizations", required: true }],
];

export default function SectionB({ reg, update, regId, token, onDocChange }) {
  return (
    <>
      <div className="grid gap-5 md:grid-cols-2">
        <Field label="Contact name"><Input testId="f-contact-name" value={reg.contact_name || ""} onChange={(e) => update({ contact_name: e.target.value })} /></Field>
        <Field label="Contact title"><Input testId="f-contact-title" value={reg.contact_title || ""} onChange={(e) => update({ contact_title: e.target.value })} /></Field>
        <Field label="Office phone"><Input testId="f-contact-phone" value={reg.contact_office_phone || ""} onChange={(e) => update({ contact_office_phone: e.target.value })} /></Field>
        <Field label="Mobile"><Input testId="f-contact-mobile" value={reg.contact_mobile || ""} onChange={(e) => update({ contact_mobile: e.target.value })} /></Field>
        <Field label="Contact email"><Input testId="f-contact-email" type="email" value={reg.contact_email || ""} onChange={(e) => update({ contact_email: e.target.value })} /></Field>
        <div />
        <Field label="Authorized signatory name"><Input testId="f-sig-name" value={reg.signatory_name || ""} onChange={(e) => update({ signatory_name: e.target.value })} /></Field>
        <Field label="Signatory title"><Input testId="f-sig-title" value={reg.signatory_title || ""} onChange={(e) => update({ signatory_title: e.target.value })} /></Field>
        <Field label="Signatory contact"><Input testId="f-sig-contact" value={reg.signatory_contact || ""} onChange={(e) => update({ signatory_contact: e.target.value })} /></Field>
      </div>
      <DocSlotsBlock
        title="Business capability documents (Section B)"
        regId={regId} token={token}
        slots={SECTION_B_SLOTS}
        existing={reg.document_slots || {}}
        onChange={onDocChange}
      />
    </>
  );
}
