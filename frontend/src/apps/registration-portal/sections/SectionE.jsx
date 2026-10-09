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
  const missing = DECL_KEYS.filter((k) => !reg[k]).length;
  return (
    <div className="grid gap-5" data-testid="section-e">
      <div>
        <div className="flex items-baseline justify-between flex-wrap gap-2 mb-3">
          <div className="pmc-label">{t("section_e.declarations_title")}</div>
          <div className={"text-xs font-semibold " + (missing === 0 ? "text-emerald-700" : "text-amber-700")}
               data-testid="section-e-missing">
            {DECL_KEYS.length - missing} / {DECL_KEYS.length} declarations accepted
            {missing > 0 && " · all are mandatory"}
          </div>
        </div>
        <div className="grid gap-2">
          {DECL_KEYS.map((k) => (
            <label key={k}
                   className={"flex items-start gap-3 border px-4 py-3 bg-white cursor-pointer hover:border-brand-navy-soft/60 " +
                              (!reg[k] ? "border-amber-400" : "border-brand-navy/10")}>
              <input
                type="checkbox"
                data-testid={`f-${k}`}
                checked={!!reg[k]}
                onChange={() => update({ [k]: !reg[k] })}
                className="mt-1"
              />
              <span className="text-sm text-brand-navy">
                {t(`section_e.${k}`)}
                {!reg[k] && <span className="ml-2 text-[10px] uppercase tracking-widest text-amber-700">Required</span>}
              </span>
            </label>
          ))}
        </div>
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        <Field label={t("section_e.signature_name")} required><Input testId="f-sign-name" value={reg.signature_name || ""} onChange={(e) => update({ signature_name: e.target.value })} /></Field>
        <Field label={t("section_e.signature_title")} required><Input testId="f-sign-title" value={reg.signature_title || ""} onChange={(e) => update({ signature_title: e.target.value })} /></Field>
        <Field label={t("section_e.signature_date")} required><Input testId="f-sign-date" type="date" value={reg.signature_date || ""} onChange={(e) => update({ signature_date: e.target.value })} /></Field>
      </div>
    </div>
  );
}
