import { Field, Input } from "./FormPrimitives";

export default function SectionC({ reg, update }) {
  return (
    <div className="grid gap-5 md:grid-cols-2">
      <Field label="Bank name"><Input testId="f-bank-name" value={reg.bank_name || ""} onChange={(e) => update({ bank_name: e.target.value })} /></Field>
      <Field label="Branch"><Input testId="f-bank-branch" value={reg.bank_branch || ""} onChange={(e) => update({ bank_branch: e.target.value })} /></Field>
      <Field label="Account number"><Input testId="f-bank-acct" value={reg.bank_account_number || ""} onChange={(e) => update({ bank_account_number: e.target.value })} /></Field>
      <Field label="SWIFT"><Input testId="f-bank-swift" value={reg.bank_swift || ""} onChange={(e) => update({ bank_swift: e.target.value })} /></Field>
      <Field label="Bank address"><Input testId="f-bank-address" value={reg.bank_address || ""} onChange={(e) => update({ bank_address: e.target.value })} /></Field>
      <Field label="Turnover currency">
        <select data-testid="f-turnover-currency" value={reg.turnover_currency || "USD"} onChange={(e) => update({ turnover_currency: e.target.value })}
          className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
          <option>USD</option><option>EUR</option><option>KZT</option><option>RUB</option><option>GBP</option>
        </select>
      </Field>
      <Field label="Turnover Year 1"><Input testId="f-turnover-1" type="number" step="0.01" value={reg.turnover_year1 || ""} onChange={(e) => update({ turnover_year1: parseFloat(e.target.value || "0") || null })} /></Field>
      <Field label="Turnover Year 2"><Input testId="f-turnover-2" type="number" step="0.01" value={reg.turnover_year2 || ""} onChange={(e) => update({ turnover_year2: parseFloat(e.target.value || "0") || null })} /></Field>
      <Field label="Turnover Year 3"><Input testId="f-turnover-3" type="number" step="0.01" value={reg.turnover_year3 || ""} onChange={(e) => update({ turnover_year3: parseFloat(e.target.value || "0") || null })} /></Field>
    </div>
  );
}
