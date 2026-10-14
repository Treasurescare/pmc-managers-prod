/**
 * EscrowBankingStep — rewritten for v52cz rev6.
 *
 * - Each bank row has its OWN country picker so an institution can hold
 *   accounts in multiple jurisdictions.
 * - Bank name is a type-ahead backed by `masters_banks` (filtered by the
 *   picked country). Picking a bank auto-fills SWIFT prefix + default
 *   currency; free-text entry still works when a country isn't seeded.
 * - IBAN and SWIFT are live-validated against the international banking
 *   formats (SWIFT BIC is 8 or 11 chars; IBAN uses the ISO 13616 shape).
 * - Country-specific routing fields appear only when relevant (US ABA
 *   routing, UK sort code, India IFSC).
 */
import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Field, Input } from "@/apps/registration-portal/sections/FormPrimitives";
import { mastersApi, showApiError } from "@/lib/api";

const SWIFT_RX = /^[A-Z]{6}[A-Z0-9]{2}([A-Z0-9]{3})?$/;
const IBAN_RX  = /^[A-Z]{2}\d{2}[A-Z0-9]{10,30}$/;
const ABA_RX   = /^\d{9}$/;
const SORT_RX  = /^\d{2}-?\d{2}-?\d{2}$/;
const IFSC_RX  = /^[A-Z]{4}0[A-Z0-9]{6}$/;

function validSwift(v)  { return !v || SWIFT_RX.test(String(v).trim().toUpperCase()); }
function validIban(v)   {
  if (!v) return true;
  const s = String(v).replace(/\s+/g, "").toUpperCase();
  return IBAN_RX.test(s);
}

const BASE_INPUT = "mt-1 w-full px-4 py-3 border focus:outline-none text-brand-navy bg-white";
const cls = (ok) => BASE_INPUT + " " +
  (ok === false ? "border-red-500 focus:border-red-500"
                : "border-brand-navy/20 focus:border-brand-navy-soft");

function BankCountrySelect({ testId, value, countries, onPick, placeholder }) {
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");
  const sel = countries.find((c) => c.code === value);
  const query = q.trim().toLowerCase();
  const filtered = (query
    ? countries.filter((c) =>
        (c.name + " " + c.code + " " + (c.phone_code || "")).toLowerCase().includes(query))
    : countries).slice(0, 80);
  return (
    <div className="relative">
      <input className={cls(null)} placeholder={placeholder}
             data-testid={testId} autoComplete="off"
             value={open ? q : (sel ? `${sel.emoji ? sel.emoji + " " : ""}${sel.name} (${sel.code})` : "")}
             onFocus={() => { setOpen(true); setQ(""); }}
             onChange={(e) => { setQ(e.target.value); setOpen(true); }}
             onBlur={() => setTimeout(() => setOpen(false), 150)} />
      {open && (
        <div className="absolute z-30 left-0 right-0 mt-1 max-h-56 overflow-auto bg-white border border-brand-navy/20 shadow-lg">
          {filtered.map((c) => (
            <button type="button" key={c.code}
                    onMouseDown={(e) => { e.preventDefault(); onPick(c); setOpen(false); setQ(""); }}
                    className="block w-full text-left px-3 py-2 text-sm text-brand-navy hover:bg-brand-pale">
              {c.emoji ? `${c.emoji} ` : ""}{c.name} <span className="text-brand-navy/50 text-xs">({c.code})</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}

function BankNameAutocomplete({ testId, value, banks, country, onPickBank, onType, onAddCustom }) {
  const [open, setOpen] = useState(false);
  const matches = banks.slice(0, 40);
  const typed = (value || "").trim();
  const exact = banks.some((b) => b.name.toLowerCase() === typed.toLowerCase());
  const canAdd = typed.length >= 2 && !exact;
  return (
    <div className="relative">
      <input className={cls(null)}
             data-testid={testId} autoComplete="off"
             value={value || ""}
             placeholder={banks.length ? "Type to search bank…" : "Enter bank name"}
             onFocus={() => setOpen(true)}
             onChange={(e) => { onType(e.target.value); setOpen(true); }}
             onBlur={() => setTimeout(() => setOpen(false), 150)} />
      {open && (matches.length > 0 || canAdd) && (
        <div className="absolute z-30 left-0 right-0 mt-1 max-h-56 overflow-auto bg-white border border-brand-navy/20 shadow-lg">
          {matches.map((b) => (
            <button type="button" key={b.name}
                    onMouseDown={(e) => { e.preventDefault(); onPickBank(b); setOpen(false); }}
                    className="block w-full text-left px-3 py-2 text-sm text-brand-navy hover:bg-brand-pale"
                    data-testid={`${testId}-opt-${b.swift_prefix}`}>
              <span className="block">{b.name}</span>
              <span className="block text-[11px] text-brand-navy/50">
                SWIFT prefix {b.swift_prefix} · {b.currencies.join(", ")}
              </span>
            </button>
          ))}
          {canAdd && (
            <button type="button"
                    onMouseDown={(e) => { e.preventDefault(); onAddCustom(typed); setOpen(false); }}
                    data-testid={`${testId}-add-custom`}
                    className="block w-full text-left px-3 py-2 text-sm text-brand-navy bg-brand-pale/60 hover:bg-brand-pale border-t border-brand-navy/10">
              <span className="block font-semibold">+ Add “{typed}”</span>
              <span className="block text-[11px] text-brand-navy/50">
                Not listed — save it to the {country || ""} bank master so it's selectable next time
              </span>
            </button>
          )}
        </div>
      )}
    </div>
  );
}

function BankRow({ row, idx, countries, onPatch, onRemove, canRemove }) {
  const [banks, setBanks] = useState([]);
  const [bankQ, setBankQ] = useState(row.institution_name || "");

  useEffect(() => {
    if (!row.bank_country) { setBanks([]); return; }
    mastersApi.listBanks(row.bank_country, bankQ).then(setBanks).catch(() => setBanks([]));
  }, [row.bank_country, bankQ]);

  // "+" affordance: bank missing from the master → persist it, refresh the
  // list, keep it selected. Lets registrants self-serve instead of bouncing.
  const addCustomBank = async (name) => {
    if (!row.bank_country) { toast.error("Pick the bank's country first"); return; }
    try {
      const b = await mastersApi.suggestBank({ country_code: row.bank_country, name });
      toast.success(`"${b.name}" added to the ${row.bank_country} bank list`);
      setBankQ("");
      setBanks(await mastersApi.listBanks(row.bank_country, ""));
      onPatch({ institution_name: b.name });
    } catch (e) { showApiError(e); }
  };

  // Load state/city for the picked bank country so Branch is cascaded.
  const [states, setStates] = useState([]);
  const [cities, setCities] = useState([]);
  useEffect(() => {
    if (!row.bank_country) { setStates([]); setCities([]); return; }
    mastersApi.listStates(row.bank_country).then(setStates).catch(() => setStates([]));
  }, [row.bank_country]);
  useEffect(() => {
    if (!row.bank_country || !row.bank_state) { setCities([]); return; }
    mastersApi.listCities(row.bank_country, row.bank_state, "").then(setCities).catch(() => setCities([]));
  }, [row.bank_country, row.bank_state]);

  const needsSort    = row.bank_country === "GB";
  const needsRouting = row.bank_country === "US";
  const needsIfsc    = row.bank_country === "IN";

  const ibanOk  = validIban(row.iban);
  const swiftOk = validSwift(row.swift);
  const abaOk   = !needsRouting || !row.routing_number || ABA_RX.test(row.routing_number);
  const sortOk  = !needsSort    || !row.sort_code       || SORT_RX.test(row.sort_code);
  const ifscOk  = !needsIfsc    || !row.bank_code       || IFSC_RX.test(row.bank_code.toUpperCase());

  return (
    <div className="grid md:grid-cols-3 gap-4 border-b border-brand-navy/10 pb-5"
         data-testid={`escrow-bank-row-${idx}`}>
      <Field label="Bank country" required>
        <BankCountrySelect testId={`escrow-bank-${idx}-country`}
                           countries={countries}
                           value={row.bank_country}
                           placeholder="Pick the country of the bank…"
                           onPick={(c) => onPatch({
                             bank_country: c.code,
                             bank_state: "", bank_city: "",
                             institution_name: "", swift: "", iban: "",
                             bank_code: "", sort_code: "", routing_number: "",
                           })} />
      </Field>
      <Field label="Bank" required>
        <BankNameAutocomplete testId={`escrow-bank-${idx}-name`}
                              value={row.institution_name}
                              banks={banks}
                              country={row.bank_country}
                              onAddCustom={addCustomBank}
                              onType={(v) => { setBankQ(v); onPatch({ institution_name: v }); }}
                              onPickBank={(b) => onPatch({
                                institution_name: b.name,
                                swift: row.swift || (b.swift_prefix ? b.swift_prefix + "XXX" : ""),
                                currency: b.currencies?.[0] || row.currency || "USD",
                              })} />
      </Field>
      <Field label="Currency">
        <Input testId={`escrow-bank-${idx}-currency`} value={row.currency || "USD"}
               onChange={(e) => onPatch({ currency: e.target.value.toUpperCase() })} />
      </Field>

      <Field label="State / Province">
        <select data-testid={`escrow-bank-${idx}-state`}
                className={cls(null)}
                value={row.bank_state || ""}
                disabled={!row.bank_country}
                onChange={(e) => {
                  const s = states.find((x) => x.state_code === e.target.value);
                  onPatch({ bank_state: e.target.value, bank_city: "",
                            branch: s ? `${s.name}` : "" });
                }}>
          <option value="">Pick a state…</option>
          {states.map((s) => (
            <option key={s.state_code} value={s.state_code}>{s.name}</option>
          ))}
        </select>
      </Field>
      <Field label="City / Branch location">
        <input list={`escrow-bank-${idx}-city-dl`} className={cls(null)}
               data-testid={`escrow-bank-${idx}-city`}
               value={row.bank_city || ""} disabled={!row.bank_state}
               placeholder={row.bank_state ? "Type to search city…" : "Pick a state first"}
               onChange={(e) => onPatch({ bank_city: e.target.value,
                                           branch: e.target.value || row.branch })} />
        <datalist id={`escrow-bank-${idx}-city-dl`}>
          {cities.map((c, i) => <option key={i} value={c.name} />)}
        </datalist>
      </Field>
      <Field label="Branch (free text)">
        <Input testId={`escrow-bank-${idx}-branch`} value={row.branch || ""}
               onChange={(e) => onPatch({ branch: e.target.value })} />
      </Field>

      <Field label="Account name" required>
        <Input testId={`escrow-bank-${idx}-account-name`} value={row.account_name || ""}
               onChange={(e) => onPatch({ account_name: e.target.value })} />
      </Field>
      <Field label="Account number" required>
        <Input testId={`escrow-bank-${idx}-account-number`} value={row.account_number || ""}
               onChange={(e) => onPatch({ account_number: e.target.value })} />
      </Field>
      <Field label="SWIFT / BIC"
             error={row.swift && !swiftOk ? "SWIFT must be 8 or 11 chars (A-Z0-9)." : null}>
        <Input testId={`escrow-bank-${idx}-swift`} value={row.swift || ""}
               onChange={(e) => onPatch({ swift: e.target.value.toUpperCase() })}
               className={cls(row.swift ? swiftOk : null)} />
      </Field>

      <Field label="IBAN"
             error={row.iban && !ibanOk ? "IBAN must start with 2-letter country code, 2 digits, up to 30 chars." : null}>
        <Input testId={`escrow-bank-${idx}-iban`} value={row.iban || ""}
               onChange={(e) => onPatch({ iban: e.target.value.toUpperCase() })}
               className={cls(row.iban ? ibanOk : null)} />
      </Field>
      {needsIfsc && (
        <Field label="IFSC (India)"
               error={row.bank_code && !ifscOk ? "IFSC must be 11 chars: 4 letters, 0, 6 alphanumerics." : null}>
          <Input testId={`escrow-bank-${idx}-ifsc`} value={row.bank_code || ""}
                 onChange={(e) => onPatch({ bank_code: e.target.value.toUpperCase() })}
                 className={cls(row.bank_code ? ifscOk : null)} />
        </Field>
      )}
      {needsRouting && (
        <Field label="ABA Routing number (US)"
               error={row.routing_number && !abaOk ? "ABA routing must be 9 digits." : null}>
          <Input testId={`escrow-bank-${idx}-aba`} value={row.routing_number || ""}
                 onChange={(e) => onPatch({ routing_number: e.target.value })}
                 className={cls(row.routing_number ? abaOk : null)} />
        </Field>
      )}
      {needsSort && (
        <Field label="Sort code (UK)"
               error={row.sort_code && !sortOk ? "Sort code must be 6 digits (optionally dashed)." : null}>
          <Input testId={`escrow-bank-${idx}-sort`} value={row.sort_code || ""}
                 onChange={(e) => onPatch({ sort_code: e.target.value })}
                 className={cls(row.sort_code ? sortOk : null)} />
        </Field>
      )}

      <Field label="Correspondent bank">
        <Input testId={`escrow-bank-${idx}-corr`} value={row.correspondent_bank || ""}
               onChange={(e) => onPatch({ correspondent_bank: e.target.value })} />
      </Field>
      <Field label="Correspondent SWIFT"
             error={row.correspondent_swift && !validSwift(row.correspondent_swift)
                    ? "Invalid SWIFT." : null}>
        <Input testId={`escrow-bank-${idx}-corr-swift`} value={row.correspondent_swift || ""}
               onChange={(e) => onPatch({ correspondent_swift: e.target.value.toUpperCase() })}
               className={cls(row.correspondent_swift ? validSwift(row.correspondent_swift) : null)} />
      </Field>
      <Field label="Settlement cutoff (e.g. 16:00 London)">
        <Input testId={`escrow-bank-${idx}-cutoff`} value={row.settlement_cutoff || ""}
               onChange={(e) => onPatch({ settlement_cutoff: e.target.value })} />
      </Field>

      {canRemove && (
        <div className="md:col-span-3 flex justify-end">
          <button type="button" onClick={onRemove}
                  data-testid={`escrow-bank-${idx}-remove`}
                  className="text-xs text-red-700 uppercase tracking-widest hover:underline">
            × Remove this bank
          </button>
        </div>
      )}
    </div>
  );
}

export default function EscrowBankingStep({ banking, onChange }) {
  const [countries, setCountries] = useState([]);
  useEffect(() => { mastersApi.listCountriesPublic().then(setCountries).catch(() => setCountries([])); }, []);
  const list = banking?.length ? banking : [{ currency: "USD" }];

  const patch = (i, delta) =>
    onChange(list.map((b, idx) => (idx === i ? { ...b, ...delta } : b)));
  const remove = (i) => onChange(list.filter((_, idx) => idx !== i));
  const add = () => onChange([...list, { currency: "USD" }]);

  return (
    <div className="space-y-6" data-testid="escrow-banking-step">
      <div className="text-xs text-brand-navy/70">
        Add every account you can hold funds in. Pick the bank's country first;
        we'll surface the local SWIFT, IBAN and routing fields.
      </div>
      {list.map((row, i) => (
        <BankRow key={i} row={row} idx={i} countries={countries}
                 onPatch={(d) => patch(i, d)}
                 onRemove={() => remove(i)}
                 canRemove={list.length > 1} />
      ))}
      <button type="button" onClick={add}
              data-testid="escrow-bank-add"
              className="text-xs uppercase tracking-widest text-brand-navy hover:underline">
        + Add another bank
      </button>
    </div>
  );
}
