import { Field, Input } from "./FormPrimitives";
import { useI18n } from "@/context/I18nContext";

const DECL_KEYS = [
  "decl_conflict_of_interest",
  "decl_integrity",
  "decl_accuracy",
  "decl_data_consent",
  "decl_fee",
  "decl_notification",
];

export default function SectionE({ reg, update }) {
  const { t } = useI18n();
  return (
    <div className="grid gap-5">
      <div>
        <div className="pmc-label mb-3">{t("section_e.declarations_title")}</div>
        <div className="grid gap-2">
          {DECL_KEYS.map((k) => (
            <label key={k} className="flex items-start gap-3 border border-brand-navy/10 px-4 py-3 bg-white cursor-pointer hover:border-brand-navy-soft/60">
              <input
                type="checkbox"
                data-testid={`f-${k}`}
                checked={!!reg[k]}
                onChange={() => update({ [k]: !reg[k] })}
                className="mt-1"
              />
              <span className="text-sm text-brand-navy">{t(`section_e.${k}`)}</span>
            </label>
          ))}
        </div>
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        <Field label={t("section_e.signature_name")}><Input testId="f-sign-name" value={reg.signature_name || ""} onChange={(e) => update({ signature_name: e.target.value })} /></Field>
        <Field label={t("section_e.signature_title")}><Input testId="f-sign-title" value={reg.signature_title || ""} onChange={(e) => update({ signature_title: e.target.value })} /></Field>
        <Field label={t("section_e.signature_date")}><Input testId="f-sign-date" type="date" value={reg.signature_date || ""} onChange={(e) => update({ signature_date: e.target.value })} /></Field>
      </div>
    </div>
  );
}
