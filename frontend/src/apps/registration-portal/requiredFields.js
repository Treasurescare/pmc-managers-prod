// Mandatory (red *) fields and documents per section of the supplier form.
export const REQUIRED_BY_SECTION = {
  a: {
    fields: { company_name: "Company name", registered_address: "Registered address", country: "Country",
      registration_number: "Registration number", incorporation_date: "Incorporation date",
      tax_id: "Tax ID", legal_entity_type: "Legal entity type" },
    docs: { incorporation_certificate: "Incorporation Certificate", address_proof: "Address Proof", tin_proof: "TIN / VAT Proof" },
  },
  b: {
    fields: { contact_name: "Contact name", contact_mobile: "Mobile", contact_email: "Contact email",
      signatory_name: "Signatory name", signatory_contact: "Signatory contact" },
    docs: { previous_works: "Previous Works Completed", licenses_permits: "Licenses / Permits" },
  },
  c: {
    fields: { bank_name: "Bank name", bank_account_number: "Account number", bank_swift: "SWIFT" },
    docs: { articles_of_incorporation: "Articles of Incorporation", bank_reference: "Bank Reference" },
  },
};

const blank = (v) => v === undefined || v === null || String(v).trim() === "";

// Returns [{ section, label }] for every mandatory field/document still empty.
export const missingRequired = (reg) => Object.entries(REQUIRED_BY_SECTION).flatMap(([section, { fields, docs }]) => [
  ...Object.entries(fields).filter(([k]) => blank(reg?.[k])).map(([, label]) => ({ section, label })),
  ...Object.entries(docs).filter(([k]) => !reg?.document_slots?.[k]).map(([, label]) => ({ section, label })),
]);
