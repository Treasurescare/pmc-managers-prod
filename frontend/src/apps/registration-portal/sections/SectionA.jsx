import { useEffect, useState } from "react";
import { Field, Input, NumericInput } from "./FormPrimitives";
import { DocSlotsBlock } from "./DocSlot";
import { useI18n } from "@/context/I18nContext";
import { mastersApi } from "@/lib/api";

// v50y — fallback used when the Legal Entity Types master is unreachable
// (first boot, offline cache). Keeps the dropdown usable either way.
const FALLBACK_TYPES = ["LLC", "JSC", "Sole Proprietorship", "Partnership", "Branch", "Other"];

const countryName = (c, lang) => c[`name_${lang}`] || c.name_en || c.name;

export default function SectionA({ reg, update, countries, regId, token, onDocChange, ensureDraft, onFormatIssue }) {
  const { t, lang } = useI18n();
  const [legalTypes, setLegalTypes] = useState([]);
  // v54e — per-country identifier formats (reg number / tax id regex +
  // example) from masters_country_formats; null-safe when unseeded.
  const [formats, setFormats] = useState(null);

  useEffect(() => {
    setFormats(null);
    if (!reg.country) return;
    mastersApi.getCountryFormats(reg.country)
      .then((d) => setFormats(d))
      .catch(() => setFormats(null));
  }, [reg.country]);

  useEffect(() => {
    // Load the admin-managed master; silently fall back to the hard-coded
    // list below if the API is unreachable (first install / offline cache).
    mastersApi.listLegalEntityTypesPublic(reg.country || undefined)
      .then((rows) => setLegalTypes(Array.isArray(rows) ? rows : []))
      .catch(() => setLegalTypes([]));
  }, [reg.country]);

  const options = legalTypes.length
    ? legalTypes.map((r) => ({
        value: r.name,
        label: lang === "ru" && r.name_ru ? r.name_ru
             : lang === "kz" && r.name_kz ? r.name_kz
             : r.name,
      }))
    : FALLBACK_TYPES.map((v) => ({ value: v, label: v }));

  // v54e — live validation wiring. today as YYYY-MM-DD for the date cap.
  const today = new Date().toISOString().slice(0, 10);
  const regFmt = formats?.reg_number;
  const taxFmt = formats?.tax_id;
  const regBad = !!(regFmt?.regex && reg.registration_number &&
    !(new RegExp(regFmt.regex).test(String(reg.registration_number).trim())));
  const taxBad = !!(taxFmt?.regex && reg.tax_id &&
    !(new RegExp(taxFmt.regex).test(String(reg.tax_id).trim())));
  const dateFuture = !!(reg.incorporation_date && reg.incorporation_date > today);
  useEffect(() => {
    onFormatIssue?.(regBad || taxBad || dateFuture);
  }, [regBad, taxBad, dateFuture, onFormatIssue]);

  const slots = [
    ["incorporation_certificate", { label: t("section_a.doc_incorporation_certificate"), required: true }],
    ["address_proof", { label: t("section_a.doc_address_proof"), required: true }],
    ["tin_proof", { label: t("section_a.doc_tin_proof"), required: true }],
    ["audited_financials", { label: t("section_a.doc_audited_financials"), required: false }],
  ];
  return (
    <>
      <div className="grid gap-5 md:grid-cols-2">
        <Field label={t("section_a.company_name")} required>
          <Input testId="f-company-name" value={reg.company_name || ""} onChange={(e) => update({ company_name: e.target.value })} />
        </Field>
        <Field label={t("section_a.trade_name")}>
          <Input testId="f-trade-name" value={reg.trade_name || ""} onChange={(e) => update({ trade_name: e.target.value })} />
        </Field>
        <Field label={t("section_a.registered_address")} required>
          <Input testId="f-registered-address" value={reg.registered_address || ""} onChange={(e) => update({ registered_address: e.target.value })} />
        </Field>
        <Field label={t("section_a.mailing_address")}>
          <Input testId="f-mailing-address" value={reg.mailing_address || ""} onChange={(e) => update({ mailing_address: e.target.value })} />
        </Field>
        <Field label={t("section_a.country")} required>
          <select data-testid="f-country" value={reg.country || "KZ"} onChange={(e) => update({ country: e.target.value })}
            className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
            {countries.map((c) => (<option key={c.code} value={c.code}>{countryName(c, lang)}</option>))}
          </select>
        </Field>
        <Field label={t("section_a.registration_number") + (formats?.reg_number?.label ? ` (${formats.reg_number.label})` : "")} required
               hint={formats?.reg_number?.example ? `Expected format: ${formats.reg_number.example}` : undefined}
               error={regBad ? `Doesn't match the ${reg.country} ${formats?.reg_number?.label || "registration number"} format (e.g. ${formats?.reg_number?.example}).` : undefined}>
          <Input testId="f-reg-number" value={reg.registration_number || ""} onChange={(e) => update({ registration_number: e.target.value })} />
        </Field>
        <Field label={t("section_a.incorporation_date")} required
               error={dateFuture ? "Incorporation date cannot be in the future." : undefined}>
          <Input testId="f-incorp-date" type="date" max={today} value={reg.incorporation_date || ""} onChange={(e) => update({ incorporation_date: e.target.value })} />
        </Field>
        <Field label={t("section_a.tax_id") + (formats?.tax_id?.label ? ` (${formats.tax_id.label})` : "")} required
               hint={formats?.tax_id?.example ? `Expected format: ${formats.tax_id.example}` : undefined}
               error={taxBad ? `Doesn't match the ${reg.country} ${formats?.tax_id?.label || "tax ID"} format (e.g. ${formats?.tax_id?.example}).` : undefined}>
          <Input testId="f-tax-id" value={reg.tax_id || ""} onChange={(e) => update({ tax_id: e.target.value })} />
        </Field>
        <Field label={t("section_a.legal_entity_type")} required>
          <select data-testid="f-legal-type" value={reg.legal_entity_type || ""} onChange={(e) => update({ legal_entity_type: e.target.value })}
            className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
            <option value="">—</option>
            {options.map((opt) => (
              <option key={opt.value} value={opt.value}>{opt.label}</option>
            ))}
          </select>
        </Field>
        <Field label={t("section_a.website")}>
          <Input testId="f-website" value={reg.website || ""} onChange={(e) => update({ website: e.target.value })} />
        </Field>
        <Field label={t("section_a.employees_count")}>
          <NumericInput testId="f-employees" integer value={reg.employees_count} onCommit={(n) => update({ employees_count: n })} />
        </Field>
      </div>
      <DocSlotsBlock
        title={t("section_a.docs_title")}
        regId={regId} token={token} ensureDraft={ensureDraft}
        slots={slots}
        existing={reg.document_slots || {}}
        onChange={onDocChange}
      />
    </>
  );
}
