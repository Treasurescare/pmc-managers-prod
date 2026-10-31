/**
 * EscrowCoreForm — Step-1 ("Core") of the Escrow Institution registration.
 *
 * v52cz rev5 — country + state are now TYPEABLE / SEARCHABLE comboboxes
 * (the plain <select> forced users to scroll 250 countries / 36+ states).
 * Everything else from rev4 stands:
 *   a) country dropdown backed by masters_countries (ISO-2 + dial code + emoji)
 *   b) bold red REQUIRED pills on mandatory fields (vendor-registration parity)
 *   c) structured address: country → state → city → zip → address 1/2
 *   d) reg-no / tax-id / VAT live-validated against /masters/country-formats
 */
import { useEffect, useMemo, useState } from "react";
import { Field, Input, EmailInput } from "@/apps/registration-portal/sections/FormPrimitives";
import { mastersApi } from "@/lib/api";
import PhonePrefixInput from "./PhonePrefixInput";

const JOIN_ADDR = (f) => [
  f.address_line1, f.address_line2,
  f.city, f.state_name, f.postal_code,
  f._country_label || f.country,
].filter(Boolean).join(", ");

export function useCountryFormats(cc) {
  const [fmt, setFmt] = useState(null);
  useEffect(() => {
    if (!cc) { setFmt(null); return; }
    mastersApi.getCountryFormats(cc).then(setFmt).catch(() => setFmt(null));
  }, [cc]);
  return fmt;
}

function Hint({ fmt, field }) {
  const f = fmt?.[field];
  if (!f) return null;
  return (
    <span className="block text-[11px] text-brand-navy/50 mt-1" data-testid={`fmt-hint-${field}`}>
      Expected: <b>{f.label}</b>{f.example ? ` — e.g. ${f.example}` : ""}
    </span>
  );
}

function regexValid(value, regex) {
  if (!value) return true;
  if (!regex) return true;
  try { return new RegExp(regex).test(String(value).trim()); }
  catch { return true; }
}

const BASE_INPUT = "mt-1 w-full px-4 py-3 border focus:outline-none text-brand-navy bg-white";
const inputCls = (ok) => BASE_INPUT + " " +
  (ok === false ? "border-red-500 focus:border-red-500"
                : "border-brand-navy/20 focus:border-brand-navy-soft");

/**
 * v52cz rev5 — typeable/searchable dropdown. Renders an input that filters
 * the option list as you type (matches label, sub-label and code). onPick
 * receives the full option object so callers can fan out dependent fields.
 */
function ComboSelect({ testId, value, options, onPick, placeholder, disabled, invalid }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const sel = options.find((o) => o.value === value);
  const query = q.trim().toLowerCase();
  const filtered = (query
    ? options.filter((o) =>
        (o.label + " " + (o.sub || "") + " " + o.value).toLowerCase().includes(query))
    : options).slice(0, 80);
  return (
    <div className="relative" data-testid={testId}>
      <input
        className={inputCls(invalid ? false : null) + (disabled ? " bg-brand-pale/50" : "")}
        placeholder={placeholder}
        disabled={disabled}
        autoComplete="off"
        data-testid={`${testId}-input`}
        value={open ? q : (sel ? sel.label : "")}
        onFocus={() => { if (!disabled) { setOpen(true); setQ(""); } }}
        onChange={(e) => { setQ(e.target.value); setOpen(true); }}
        onBlur={() => setTimeout(() => setOpen(false), 150)}
      />
      {open && !disabled && (
        <div className="absolute z-30 left-0 right-0 mt-1 max-h-60 overflow-auto bg-white border border-brand-navy/20 shadow-lg">
          {filtered.length === 0 && (
            <div className="px-3 py-2 text-xs text-brand-navy/50" data-testid={`${testId}-empty`}>
              No matches
            </div>
          )}
          {filtered.map((o) => (
            <button key={o.value} type="button"
                    onMouseDown={(e) => { e.preventDefault(); onPick(o); setOpen(false); setQ(""); }}
                    className="block w-full text-left px-3 py-2 text-sm text-brand-navy hover:bg-brand-pale"
                    data-testid={`${testId}-opt-${o.value}`}>
              {o.label}
              {o.sub ? <span className="text-brand-navy/50 text-xs ml-2">{o.sub}</span> : null}
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

export default function EscrowCoreForm({ form, set, onNext, saving, individual = false }) {
  const [countries, setCountries] = useState([]);
  const [states, setStates] = useState([]);
  const [cities, setCities] = useState([]);
  const [cityQ, setCityQ] = useState("");
  const [touched, setTouched] = useState(false);

  useEffect(() => { mastersApi.listCountriesPublic().then(setCountries).catch(() => setCountries([])); }, []);
  const byCode = useMemo(() => {
    const m = new Map(); for (const c of countries) m.set(c.code, c); return m;
  }, [countries]);

  const fmt = useCountryFormats(form.country);
  const country = form.country ? byCode.get(form.country) : null;

  useEffect(() => {
    if (!form.country) { setStates([]); return; }
    mastersApi.listStates(form.country).then(setStates).catch(() => setStates([]));
  }, [form.country]);
  useEffect(() => {
    if (!form.country || !form.state_code) { setCities([]); return; }
    mastersApi.listCities(form.country, form.state_code, cityQ).then(setCities).catch(() => setCities([]));
  }, [form.country, form.state_code, cityQ]);

  const zipRegex = country?.postal_code_regex;
  const zipFormat = country?.postal_code_format;
  const zipOk = regexValid(form.postal_code, zipRegex);
  const regOk = individual || regexValid(form.reg_number, fmt?.reg_number?.regex);
  const taxOk = regexValid(form.tax_id, fmt?.tax_id?.regex);
  const vatOk = regexValid(form.gst_or_vat, fmt?.vat?.regex);

  const requiredMissing = (() => {
    const miss = [];
    if (!form.legal_name) miss.push("Legal name");
    if (!form.country) miss.push("Country");
    if (!form.address_line1) miss.push("Address line 1");
    if (!form.city) miss.push("City");
    if (!form.state_code) miss.push("State / Province");
    if (!form.postal_code) miss.push("Postal / ZIP code");
    if (!form.reg_number) miss.push(individual ? "Passport / national ID number" : "Registration number");
    if (!form.primary_contact_email) miss.push("Primary contact email");
    return miss;
  })();
  const allOk = requiredMissing.length === 0 && zipOk && regOk && taxOk && vatOk;

  const submit = () => {
    setTouched(true);
    if (!allOk) return;
    set("registered_address", JOIN_ADDR({ ...form, _country_label: country?.name }));
    onNext && onNext();
  };

  const countryOptions = countries.map((c) => ({
    value: c.code,
    label: `${c.emoji ? c.emoji + " " : ""}${c.name} (${c.code})`,
    sub: c.phone_code ? `+${c.phone_code}` : "",
    data: c,
  }));
  const stateOptions = states.map((s) => ({
    value: s.state_code, label: s.name, sub: s.state_code, data: s,
  }));

  return (
    <div className="grid md:grid-cols-2 gap-5 bg-white p-6 border border-brand-navy/15"
         data-testid="escrow-core-form">
      <Field label="Legal name" required>
        <Input testId="escrow-f-legal-name" value={form.legal_name || ""}
               onChange={(e) => set("legal_name", e.target.value)}
               className={inputCls(touched ? !!form.legal_name : null)} />
      </Field>
      <Field label="Trading name">
        <Input testId="escrow-f-trading-name" value={form.trading_name || ""}
               onChange={(e) => set("trading_name", e.target.value)} />
      </Field>

      <Field label="Country" required
             hint={country?.phone_code ? `Dial code +${country.phone_code}` : "Type to search…"}>
        <ComboSelect testId="escrow-f-country"
                     value={form.country || ""}
                     options={countryOptions}
                     placeholder="Type to search country…"
                     invalid={touched && !form.country}
                     onPick={(o) => {
                       set("country", o.value);
                       set("phone_country_code", o.data?.phone_code || "");
                       set("state_code", ""); set("state_name", "");
                       set("city", ""); set("postal_code", "");
                     }} />
      </Field>

      <Field label={individual ? "Passport / national ID number" : (fmt?.reg_number?.label || "Registration number")} required
             error={touched && form.reg_number && !regOk ? "Doesn't match the country format." : null}>
        <Input testId="escrow-f-reg-number" value={form.reg_number || ""}
               onChange={(e) => set("reg_number", e.target.value)}
               className={inputCls(touched ? !!form.reg_number && regOk : null)} />
        {!individual && <Hint fmt={fmt} field="reg_number" />}
      </Field>

      <div className="md:col-span-2 border-t border-brand-navy/10 pt-4 mt-1">
        <div className="pmc-label text-brand-navy/70 mb-2">REGISTERED ADDRESS</div>
        <div className="grid md:grid-cols-2 gap-5">
          <Field label="State / Province" required>
            <ComboSelect testId="escrow-f-state"
                         value={form.state_code || ""}
                         options={stateOptions}
                         disabled={!form.country}
                         placeholder={form.country
                           ? (states.length ? "Type to search state…" : "No states for this country")
                           : "Pick a country first"}
                         invalid={touched && !form.state_code}
                         onPick={(o) => {
                           set("state_code", o.value);
                           set("state_name", o.data?.name || o.label);
                           set("city", "");
                         }} />
          </Field>
          <Field label="City" required>
            <input list="escrow-city-dl" data-testid="escrow-f-city"
                   value={form.city || ""}
                   disabled={!form.state_code}
                   placeholder={form.state_code ? "Type to search city…" : "Pick a state first"}
                   onChange={(e) => { setCityQ(e.target.value); set("city", e.target.value); }}
                   className={inputCls(touched ? !!form.city : null)} />
            <datalist id="escrow-city-dl">
              {cities.map((c, i) => <option key={i} value={c.name} />)}
            </datalist>
          </Field>
          <Field label={`Postal / ZIP code${zipFormat ? ` (format: ${zipFormat})` : ""}`} required
                 error={touched && form.postal_code && !zipOk ? `Doesn't match the ${form.country} format.` : null}>
            <Input testId="escrow-f-postal" value={form.postal_code || ""}
                   onChange={(e) => set("postal_code", e.target.value)}
                   className={inputCls(touched ? !!form.postal_code && zipOk : null)} />
          </Field>
          <Field label="Address line 1" required>
            <Input testId="escrow-f-address1" value={form.address_line1 || ""}
                   onChange={(e) => set("address_line1", e.target.value)}
                   className={inputCls(touched ? !!form.address_line1 : null)} />
          </Field>
          <Field label="Address line 2">
            <Input testId="escrow-f-address2" value={form.address_line2 || ""}
                   onChange={(e) => set("address_line2", e.target.value)} />
          </Field>
        </div>
      </div>

      <Field label={fmt?.tax_id?.label || "Tax ID"}
             error={touched && form.tax_id && !taxOk ? "Doesn't match the country format." : null}>
        <Input testId="escrow-f-tax-id" value={form.tax_id || ""}
               onChange={(e) => set("tax_id", e.target.value)}
               className={inputCls(touched ? (form.tax_id ? taxOk : null) : null)} />
        <Hint fmt={fmt} field="tax_id" />
      </Field>
      <Field label={fmt?.vat?.label || "GST / VAT"}
             error={touched && form.gst_or_vat && !vatOk ? "Doesn't match the country format." : null}>
        <Input testId="escrow-f-vat" value={form.gst_or_vat || ""}
               onChange={(e) => set("gst_or_vat", e.target.value)}
               className={inputCls(touched ? (form.gst_or_vat ? vatOk : null) : null)} />
        <Hint fmt={fmt} field="vat" />
      </Field>

      {!individual && <>
      <Field label="Regulator / licence authority">
        <Input testId="escrow-f-regulator" value={form.regulator || ""}
               onChange={(e) => set("regulator", e.target.value)} />
      </Field>
      <Field label="Licence number">
        <Input testId="escrow-f-licence-number" value={form.licence_number || ""}
               onChange={(e) => set("licence_number", e.target.value)} />
      </Field>
      <Field label="Licence expiry (YYYY-MM-DD)">
        <Input testId="escrow-f-licence-expiry" type="date" value={form.licence_expiry || ""}
               onChange={(e) => set("licence_expiry", e.target.value)} />
      </Field>
      </>}
      <Field label="Website">
        <Input testId="escrow-f-website" value={form.website || ""}
               onChange={(e) => set("website", e.target.value)} />
      </Field>

      <Field label="Primary contact email" required
             error={touched && !form.primary_contact_email ? "Required." : null}>
        <EmailInput testId="escrow-f-contact-email" value={form.primary_contact_email || ""}
                    onChange={(e) => set("primary_contact_email", e.target.value)} />
      </Field>
      {/* v52cz rev7 — ISD prefix dropdown + length-validated local number */}
      <Field label="Mobile number"
             hint={country?.phone_code ? `Pre-selected +${country.phone_code} — click to change` : "Pick a country above to pre-select the ISD code"}>
        <PhonePrefixInput testId="escrow-f-mobile-phone"
                          value={form.mobile_phone || form.primary_contact_phone || ""}
                          onChange={(v) => { set("mobile_phone", v);
                                              set("primary_contact_phone", v); }}
                          countries={countries}
                          defaultCountry={form.country} />
      </Field>
      <Field label="Office telephone"
             hint={country?.phone_code ? `Pre-selected +${country.phone_code} — click to change` : "Pick a country above to pre-select the ISD code"}>
        <PhonePrefixInput testId="escrow-f-office-phone"
                          value={form.office_phone || ""}
                          onChange={(v) => set("office_phone", v)}
                          countries={countries}
                          defaultCountry={form.country} />
      </Field>

      <div className="md:col-span-2 flex items-center justify-between">
        {touched && !allOk ? (
          <div className="text-xs text-red-700" data-testid="escrow-core-missing">
            {requiredMissing.length
              ? `Missing: ${requiredMissing.join(", ")}`
              : "Fix the highlighted fields before continuing."}
          </div>
        ) : <span />}
        <button type="button" onClick={submit} disabled={saving}
                data-testid="escrow-reg-next-1"
                className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white disabled:opacity-50 hover:bg-brand-navy-deep">
          {saving ? "Saving…" : "Save and continue"}
        </button>
      </div>
    </div>
  );
}
