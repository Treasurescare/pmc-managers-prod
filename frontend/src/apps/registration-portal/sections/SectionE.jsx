import { Field, Input } from "./FormPrimitives";

const DECLARATIONS = [
  ["decl_conflict_of_interest", "No conflict of interest with PMC Managers, Emerald Corporates or Big B Corporation"],
  ["decl_integrity", "Company is not under sanctions, blacklisting or debarment"],
  ["decl_accuracy", "All information provided is accurate to the best of our knowledge"],
  ["decl_data_consent", "Consent to PMC storing and processing this data in line with applicable data-protection law"],
  ["decl_fee", "Understand that any registration fee (if applicable) is non-refundable"],
  ["decl_notification", "Accept email notifications on tender activity"],
];

export default function SectionE({ reg, update }) {
  return (
    <div className="grid gap-5">
      <div>
        <div className="pmc-label mb-3">Declarations · all six required</div>
        <div className="grid gap-2">
          {DECLARATIONS.map(([k, label]) => (
            <label key={k} className="flex items-start gap-3 border border-brand-navy/10 px-4 py-3 bg-white cursor-pointer hover:border-brand-navy-soft/60">
              <input
                type="checkbox"
                data-testid={`f-${k}`}
                checked={!!reg[k]}
                onChange={() => update({ [k]: !reg[k] })}
                className="mt-1"
              />
              <span className="text-sm text-brand-navy">{label}</span>
            </label>
          ))}
        </div>
      </div>
      <div className="grid gap-5 md:grid-cols-3">
        <Field label="Signature — full name"><Input testId="f-sign-name" value={reg.signature_name || ""} onChange={(e) => update({ signature_name: e.target.value })} /></Field>
        <Field label="Signature — title"><Input testId="f-sign-title" value={reg.signature_title || ""} onChange={(e) => update({ signature_title: e.target.value })} /></Field>
        <Field label="Signature — date"><Input testId="f-sign-date" type="date" value={reg.signature_date || ""} onChange={(e) => update({ signature_date: e.target.value })} /></Field>
      </div>
    </div>
  );
}
