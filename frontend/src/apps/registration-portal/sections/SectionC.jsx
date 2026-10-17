import { useEffect, useState } from "react";
import { Field, Input, NumericInput } from "./FormPrimitives";
import { DocSlotsBlock } from "./DocSlot";
import { useI18n } from "@/context/I18nContext";
import { mastersApi } from "@/lib/api";
import UnspscPicker from "@/components/UnspscPicker";

export default function SectionC({ reg, update, regId, token, onDocChange, ensureDraft }) {
  const { t } = useI18n();
  // v54e — bank master dropdown filtered by the vendor's country (same
  // masters_banks source the escrow banking step uses). Picking a bank
  // auto-fills the SWIFT from its prefix; stays editable after.
  const [banks, setBanks] = useState([]);
  useEffect(() => {
    if (!reg.country) { setBanks([]); return; }
    mastersApi.listBanks(reg.country).then(setBanks);
  }, [reg.country]);
  const slots = [
    ["articles_of_incorporation", { label: t("section_c.doc_articles_of_incorporation"), required: true }],
    ["bank_reference", { label: t("section_c.doc_bank_reference"), required: true }],
    ["power_of_attorney", { label: t("section_c.doc_power_of_attorney"), required: false }],
    ["other_supporting", { label: t("section_c.doc_other_supporting"), required: false }],
  ];
  return (
    <>
      <div className="grid gap-5 md:grid-cols-2">
        <Field label={t("section_c.bank_name")} required
               hint={banks.length
                 ? "Type to search your country's bank master — picking a bank auto-fills its SWIFT code."
                 : "No banks seeded for this country yet — type the bank name manually."}>
          <input list="f-bank-name-dl" data-testid="f-bank-name" value={reg.bank_name || ""}
                 onChange={(e) => {
                   const v = e.target.value;
                   const hit = banks.find((b) => b.name === v);
                   update(hit
                     ? { bank_name: v, bank_swift: hit.swift_prefix ? `${hit.swift_prefix}XXX` : reg.bank_swift }
                     : { bank_name: v });
                 }}
                 placeholder={banks.length ? "Type to search bank…" : "Enter bank name"}
                 className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
          <datalist id="f-bank-name-dl">
            {banks.map((b) => (
              <option key={b._id || b.name} value={b.name}>
                {b.swift_prefix ? `SWIFT ${b.swift_prefix}` : ""}
              </option>
            ))}
          </datalist>
        </Field>
        <Field label={t("section_c.branch")}><Input testId="f-bank-branch" value={reg.bank_branch || ""} onChange={(e) => update({ bank_branch: e.target.value })} /></Field>
        <Field label={t("section_c.account_number")} required><Input testId="f-bank-acct" value={reg.bank_account_number || ""} onChange={(e) => update({ bank_account_number: e.target.value })} /></Field>
        <Field label={t("section_c.swift")} required><Input testId="f-bank-swift" value={reg.bank_swift || ""} onChange={(e) => update({ bank_swift: e.target.value })} /></Field>
        <Field label={t("section_c.bank_address")}><Input testId="f-bank-address" value={reg.bank_address || ""} onChange={(e) => update({ bank_address: e.target.value })} /></Field>
        <Field label={t("section_c.turnover_currency")}>
          <select data-testid="f-turnover-currency" value={reg.turnover_currency || "USD"} onChange={(e) => update({ turnover_currency: e.target.value })}
            className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
            <option>USD</option><option>EUR</option><option>KZT</option><option>RUB</option><option>GBP</option>
          </select>
        </Field>
        <Field label={t("section_c.turnover_y1")}><NumericInput testId="f-turnover-1" value={reg.turnover_year1} onCommit={(n) => update({ turnover_year1: n })} /></Field>
        <Field label={t("section_c.turnover_y2")}><NumericInput testId="f-turnover-2" value={reg.turnover_year2} onCommit={(n) => update({ turnover_year2: n })} /></Field>
        <Field label={t("section_c.turnover_y3")}><NumericInput testId="f-turnover-3" value={reg.turnover_year3} onCommit={(n) => update({ turnover_year3: n })} /></Field>
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

