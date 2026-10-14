/**
 * EscrowCoreForm — Step-1 ("Core") of the Escrow Institution registration.
 *
 * v52cz rev4 — rewritten against user feedback:
 *   a) country is a real dropdown (ISO-2 + phone code + emoji) backed by
 *      the masters_countries collection, not a free-text box.
 *   b) all mandatory fields show the same bold red REQUIRED pill as the
 *      vendor registration (Field primitive from registration-portal).
 *   c) registered address is a cascading country → state → city → zip →
 *      address 1 → address 2 block, with city/state loaded from masters
 *      and ZIP live-validated against the country's postal regex.
 *   d) reg-number / tax-id / VAT inputs live-validate against the
 *      country-specific regex coming from /masters/country-formats/{cc};
 *      the input's hint shows the local label + example (e.g. "CIN —
 *      L17110MH1973PLC019786"). Empty + regex-mismatch both block submit.
 */
import { useEffect, useMemo, useState } from "react";
import { Field, Input, EmailInput, PhoneInput } from "@/apps/registration-portal/sections/FormPrimitives";
import { mastersApi } from "@/lib/api";

const JOIN_ADDR = (f) => [
  f.address_line1, f.address_line2,
  f.city, f.state_name, f.postal_code,
  // Use country name when available, else code
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

/**
 * Props:
 *   form        – full form object (parent-owned state)
 *   set(k, v)   – setter for a single field
 *   onNext()    – called when the user clicks Save & continue AFTER local validation passes
 *   saving      – show spinner on the button
 */
export default function EscrowCoreForm({ form, set, onNext, saving }) {
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

  // Cascade: country → states → cities
  useEffect(() => {
    if (!form.country) { setStates([]); return; }
    mastersApi.listStates(form.country).then(setStates).catch(() => setStates([]));
  }, [form.country]);
  useEffect(() => {
    if (!form.country || !form.state_code) { setCities([]); return; }
    mastersApi.listCities(form.country, form.state_code, cityQ).then(setCities).catch(() => setCities([]));
  }, [form.country, form.state_code, cityQ]);

  // Derived validation state
  const zipRegex = country?.postal_code_regex;
  const zipFormat = country?.postal_code_format;
  const zipOk = regexValid(form.postal_code, zipRegex);
  const regOk = regexValid(form.reg_number, fmt?.reg_number?.regex);
  const taxOk = regexValid(form.tax_id, fmt?.tax_id?.regex);
  const vatOk = regexValid(form.gst_or_vat, fmt?.vat?.regex);

  // Required fields
  const requiredMissing = (() => {
    const miss = [];
    if (!form.legal_name) miss.push("Legal name");
    if (!form.country) miss.push("Country");
    if (!form.address_line1) miss.push("Address line 1");
    if (!form.city) miss.push("City");
    if (!form.state_code) miss.push("State / Province");
    if (!form.postal_code) miss.push("Postal / ZIP code");
    if (!form.reg_number) miss.push("Registration number");
    if (!form.primary_contact_email) miss.push("Primary contact email");
    return miss;
  })();
  const allOk = requiredMissing.length === 0 && zipOk && regOk && taxOk && vatOk;

  const submit = () => {
    setTouched(true);
    if (!allOk) return;
    // Compose the flat registered_address string the backend expects for
    // backwards compat, from the structured pieces.
    const addr = JOIN_ADDR({ ...form, _country_label: country?.name });
    set("registered_address", addr);
    onNext && onNext();
  };

  const inputCls = (ok) => "mt-1 w-full px-4 py-3 border focus:outline-none text-brand-navy bg-white " +
    (ok === false ? "border-red-500 focus:border-red-500"
                  : "border-brand-navy/20 focus:border-brand-navy-soft");

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
             hint={country?.phone_code ? `Dial code +${country.phone_code}` : undefined}>
        <select data-testid="escrow-f-country"
                value={form.country || ""}
                onChange={(e) => {
                  const cc = e.target.value;
                  const c = byCode.get(cc);
                  set("country", cc);
                  set("phone_country_code", c?.phone_code || "");
                  // Reset dependent fields.
                  set("state_code", ""); set("state_name", "");
                  set("city", ""); set("postal_code", "");
                }}
                className={inputCls(touched ? !!form.country : null)}>
          <option value="">Pick a country…</option>
          {countries.map((c) => (
            <option key={c.code} value={c.code}>
              {c.emoji ? `${c.emoji} ` : ""}{c.name} ({c.code}) +{c.phone_code}
            </option>
          ))}
        </select>
      </Field>

      <Field label={fmt?.reg_number?.label || "Registration number"} required
             error={touched && form.reg_number && !regOk ? "Doesn't match the country format." : null}>
        <Input testId="escrow-f-reg-number" value={form.reg_number || ""}
               onChange={(e) => set("reg_number", e.target.value)}
               className={inputCls(touched ? !!form.reg_number && regOk : null)} />
        <Hint fmt={fmt} field="reg_number" />
      </Field>

      {/* --- Structured registered address: country → state → city → zip → addr1/2 */}
      <div className="md:col-span-2 border-t border-brand-navy/10 pt-4 mt-1">
        <div className="pmc-label text-brand-navy/70 mb-2">REGISTERED ADDRESS</div>
        <div className="grid md:grid-cols-2 gap-5">
          <Field label="State / Province" required>
            <select data-testid="escrow-f-state"
                    value={form.state_code || ""}
                    disabled={!form.country}
                    onChange={(e) => {
                      const s = states.find((x) => x.state_code === e.target.value);
                      set("state_code", e.target.value);
                      set("state_name", s?.name || "");
                      set("city", "");
                    }}
                    className={inputCls(touched ? !!form.state_code : null)}>
              <option value="">{form.country
                ? (states.length ? "Pick a state…" : "No states for this country")
                : "Pick a country first"}</option>
              {states.map((s) => <option key={s.state_code} value={s.state_code}>{s.name}</option>)}
            </select>
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

      {/* --- Tax ids --- */}
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
      <Field label="Website">
        <Input testId="escrow-f-website" value={form.website || ""}
               onChange={(e) => set("website", e.target.value)} />
      </Field>

      <Field label="Primary contact email" required
             error={touched && !form.primary_contact_email ? "Required." : null}>
        <EmailInput testId="escrow-f-contact-email" value={form.primary_contact_email || ""}
                    onChange={(e) => set("primary_contact_email", e.target.value)} />
      </Field>
      <Field label="Primary contact phone"
             hint={country?.phone_code ? `Starts with +${country.phone_code}` : undefined}>
        <PhoneInput testId="escrow-f-contact-phone" value={form.primary_contact_phone || ""}
                    onChange={(e) => set("primary_contact_phone", e.target.value)} />
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
