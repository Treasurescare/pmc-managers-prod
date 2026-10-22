import { useEffect, useMemo, useRef, useState } from "react";
import { mastersApi } from "@/lib/api";
import { useCountries } from "@/components/CountryPicker";

let _curCache = null;

// Shared active-currency catalogue (ISO-4217), fetched once and cached.
export function useCurrencies() {
  const [rows, setRows] = useState(_curCache || []);
  useEffect(() => {
    if (_curCache) return;
    mastersApi.listCurrenciesPublic()
      .then((r) => { _curCache = Array.isArray(r) ? r : []; setRows(_curCache); })
      .catch(() => setRows([]));
  }, []);
  return rows;
}

const up = (v) => String(v || "").toUpperCase();

// Currency <select> that default-loads a country's accepted currencies
// (primary preselected) but still lets the user pick ANY active currency.
// preserveInitial=true keeps an existing saved value on first mount (edit
// forms); when false (create forms) the country's primary is applied on mount.
export function CurrencySelect({
  country, value, onChange, testId, className = "", preserveInitial = false,
}) {
  const currencies = useCurrencies();
  const countries = useCountries();
  const meta = useMemo(
    () => countries.find((c) => up(c.code) === up(country)),
    [countries, country],
  );
  const accepted = useMemo(() => {
    const a = (meta?.accepted_currencies && meta.accepted_currencies.length)
      ? meta.accepted_currencies
      : (meta?.currency ? [meta.currency] : []);
    return a.map(up);
  }, [meta]);
  const primary = up(meta?.currency || accepted[0] || "");

  const lastCountry = useRef(undefined);
  useEffect(() => {
    if (!meta) return;
    const firstRun = lastCountry.current === undefined;
    const changed = !firstRun && lastCountry.current !== country;
    lastCountry.current = country;
    if (firstRun && preserveInitial) return;
    if (!firstRun && !changed) return;
    if (primary && up(value) !== primary) onChange(primary);
  }, [country, meta, primary, accepted, value, onChange, preserveInitial]);

  const ordered = (() => {
    const list = accepted.slice();
    const i = list.indexOf(primary);
    if (primary && i > 0) { list.splice(i, 1); list.unshift(primary); }
    else if (primary && i < 0) list.unshift(primary);
    return list;
  })();
  const byCode = {};
  currencies.forEach((c) => { byCode[up(c.code)] = c; });
  const acceptedList = ordered.map((code) => byCode[code]).filter(Boolean);
  const otherList = currencies.filter((c) => !accepted.includes(up(c.code)));
  const known = currencies.some((c) => up(c.code) === up(value));

  return (
    <select
      value={value || ""}
      onChange={(e) => onChange(e.target.value)}
      data-testid={testId}
      className={className || "mt-1 w-full px-3 py-2 border normal-case tracking-normal"}
    >
      {!known && value && <option value={value}>{up(value)}</option>}
      {acceptedList.length > 0 && (
        <optgroup label={country ? `Accepted in ${up(country)}` : "Accepted"}>
          {acceptedList.map((c) => (
            <option key={`a-${c.code}`} value={c.code}>
              {c.code} · {c.name}{c.symbol ? ` (${c.symbol})` : ""}{up(c.code) === primary ? " — default" : ""}
            </option>
          ))}
        </optgroup>
      )}
      <optgroup label="All currencies">
        {otherList.map((c) => (
          <option key={`o-${c.code}`} value={c.code}>
            {c.code} · {c.name}{c.symbol ? ` (${c.symbol})` : ""}
          </option>
        ))}
      </optgroup>
    </select>
  );
}
