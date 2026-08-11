import { Field, Input } from "./FormPrimitives";
import { DocSlotsBlock } from "./DocSlot";
import { useI18n } from "@/context/I18nContext";
import UnspscPicker from "@/components/UnspscPicker";

export default function SectionC({ reg, update, regId, token, onDocChange, ensureDraft }) {
  const { t } = useI18n();
  const slots = [
    ["articles_of_incorporation", { label: t("section_c.doc_articles_of_incorporation"), required: true }],
    ["bank_reference", { label: t("section_c.doc_bank_reference"), required: true }],
    ["power_of_attorney", { label: t("section_c.doc_power_of_attorney"), required: false }],
    ["other_supporting", { label: t("section_c.doc_other_supporting"), required: false }],
  ];
  return (
    <>
      <div className="grid gap-5 md:grid-cols-2">
        <Field label={t("section_c.bank_name")}><Input testId="f-bank-name" value={reg.bank_name || ""} onChange={(e) => update({ bank_name: e.target.value })} /></Field>
        <Field label={t("section_c.branch")}><Input testId="f-bank-branch" value={reg.bank_branch || ""} onChange={(e) => update({ bank_branch: e.target.value })} /></Field>
        <Field label={t("section_c.account_number")}><Input testId="f-bank-acct" value={reg.bank_account_number || ""} onChange={(e) => update({ bank_account_number: e.target.value })} /></Field>
        <Field label={t("section_c.swift")}><Input testId="f-bank-swift" value={reg.bank_swift || ""} onChange={(e) => update({ bank_swift: e.target.value })} /></Field>
        <Field label={t("section_c.bank_address")}><Input testId="f-bank-address" value={reg.bank_address || ""} onChange={(e) => update({ bank_address: e.target.value })} /></Field>
        <Field label={t("section_c.turnover_currency")}>
          <select data-testid="f-turnover-currency" value={reg.turnover_currency || "USD"} onChange={(e) => update({ turnover_currency: e.target.value })}
            className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
            <option>USD</option><option>EUR</option><option>KZT</option><option>RUB</option><option>GBP</option>
          </select>
        </Field>
        <Field label={t("section_c.turnover_y1")}><Input testId="f-turnover-1" type="number" step="0.01" value={reg.turnover_year1 || ""} onChange={(e) => update({ turnover_year1: parseFloat(e.target.value || "0") || null })} /></Field>
        <Field label={t("section_c.turnover_y2")}><Input testId="f-turnover-2" type="number" step="0.01" value={reg.turnover_year2 || ""} onChange={(e) => update({ turnover_year2: parseFloat(e.target.value || "0") || null })} /></Field>
        <Field label={t("section_c.turnover_y3")}><Input testId="f-turnover-3" type="number" step="0.01" value={reg.turnover_year3 || ""} onChange={(e) => update({ turnover_year3: parseFloat(e.target.value || "0") || null })} /></Field>
      </div>

      {/* Wave 44 — Primary UNSPSC commodity tag */}
      <div className="mt-6">
        <div className="text-[10px] uppercase tracking-widest text-brand-navy/60 mb-1">
          Primary UNSPSC commodity (optional — for cleaner reporting)
        </div>
        <UnspscPicker
          value={reg.primary_unspsc_code}
          title={reg.primary_unspsc_title}
          onChange={({ code, title }) => update({
            primary_unspsc_code: code, primary_unspsc_title: title,
          })}
          testidPrefix="vendor-unspsc"
        />
      </div>

      <DocSlotsBlock
        title={t("section_c.docs_title")}
        regId={regId} token={token} ensureDraft={ensureDraft}
        slots={slots}
        existing={reg.document_slots || {}}
        onChange={onDocChange}
      />
    </>
  );
}

