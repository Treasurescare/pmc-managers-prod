/**
 * PhonePrefixInput — v52cz rev7
 *
 * Single phone field with:
 *   • left-hand country-code dropdown (searchable) pre-selected from the
 *     Core country, but changeable per field
 *   • right-hand local-number input, digits-only, length-validated against
 *     the ITU E.164 rules (min 4, max 15 incl. country code → local length
 *     derived from the dial code length)
 *
 * The combined value is stored as E.164: "+<cc><digits>" so backend callers
 * see a single canonical string.
 *
 * Props:
 *   value             – E.164 string ("+919876543210") or ""
 *   onChange(e164)    – fires with the composed E.164 string
 *   defaultCountry    – ISO-2 code to prefix with when value is empty
 *   countries         – list of {code, name, emoji, phone_code} from masters
 *   testId            – test id prefix
 */
import { useEffect, useMemo, useState } from "react";

function parseE164(v, dialCodes) {
  const s = String(v || "").trim();
  if (!s.startsWith("+")) return { dial: "", local: s.replace(/\D/g, "") };
  const digits = s.slice(1).replace(/\s|-/g, "");
  // Greedy longest match against known dial codes (1–4 digits).
  for (let len = 4; len >= 1; len--) {
    const d = digits.slice(0, len);
    if (dialCodes.has(d)) return { dial: d, local: digits.slice(len) };
  }
  return { dial: "", local: digits };
}

export default function PhonePrefixInput({ value, onChange, defaultCountry,
                                            countries = [], testId, disabled }) {
  const dialCodes = useMemo(() => {
    const s = new Set();
    for (const c of countries) if (c.phone_code) s.add(String(c.phone_code));
    return s;
  }, [countries]);
  const parsed = parseE164(value, dialCodes);
  const defDial = useMemo(() => {
    const c = countries.find((x) => x.code === defaultCountry);
    return c?.phone_code ? String(c.phone_code) : "";
  }, [defaultCountry, countries]);
  const [dial, setDial] = useState(parsed.dial || defDial || "");
  const [local, setLocal] = useState(parsed.local || "");
  const [open, setOpen] = useState(false);
  const [q, setQ] = useState("");

  // Keep the local-state dial in sync with external pre-select changes.
  useEffect(() => {
    if (!parsed.dial && defDial && !dial) setDial(defDial);
    // Also mirror an external value change (e.g. resume from draft).
  // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [defDial]);

  // Local-number length rules. Pragmatic defaults: 7–15 subscriber digits
  // minus the dial-code length. Covers 99% of countries without needing a
  // dedicated per-country master.
  const localMin = Math.max(4, 7 - (dial?.length || 0));
  const localMax = Math.max(localMin, 15 - (dial?.length || 0));
  const ok = !local || (local.length >= localMin && local.length <= localMax);

  const emit = (nextDial, nextLocal) => {
    const d = (nextDial || "").replace(/\D/g, "");
    const n = (nextLocal || "").replace(/\D/g, "");
    onChange(n || d ? `+${d}${n}` : "");
  };

  const filtered = (() => {
    const query = q.trim().toLowerCase();
    const base = query
      ? countries.filter((c) => (c.name + " +" + (c.phone_code || "")).toLowerCase().includes(query))
      : countries;
    return base.slice(0, 80);
  })();

  const inputCls = (good) => "flex-1 min-w-0 px-3 py-3 border focus:outline-none text-brand-navy bg-white " +
    (good === false ? "border-red-500" : "border-brand-navy/20 focus:border-brand-navy-soft");

  return (
    <div data-testid={testId}>
      <div className="flex gap-2 relative">
        <button type="button" disabled={disabled}
                onClick={() => setOpen((o) => !o)}
                data-testid={`${testId}-dial-btn`}
                className="px-3 py-3 border border-brand-navy/20 text-brand-navy bg-white min-w-[90px] text-left">
          {dial ? `+${dial}` : "+ dial"}
        </button>
        <input type="tel" inputMode="numeric" value={local} disabled={disabled}
               onChange={(e) => {
                 const v = e.target.value.replace(/\D/g, "").slice(0, localMax);
                 setLocal(v); emit(dial, v);
               }}
               placeholder={local ? "" : `${localMin}–${localMax} digits`}
               data-testid={`${testId}-local`}
               className={inputCls(ok)} />
        {open && !disabled && (
          <div className="absolute z-30 top-full left-0 mt-1 w-[280px] max-h-56 overflow-auto bg-white border border-brand-navy/20 shadow-lg">
            <div className="p-2 border-b border-brand-navy/10">
              <input autoFocus placeholder="Search country or code…"
                     value={q} onChange={(e) => setQ(e.target.value)}
                     className="w-full px-2 py-1 border border-brand-navy/20 text-sm" />
            </div>
            {filtered.map((c) => (
              <button type="button" key={c.code}
                      onClick={() => { setDial(String(c.phone_code || "")); setOpen(false); setQ("");
                                        emit(String(c.phone_code || ""), local); }}
                      className="block w-full text-left px-3 py-2 text-sm text-brand-navy hover:bg-brand-pale"
                      data-testid={`${testId}-opt-${c.code}`}>
                {c.emoji ? `${c.emoji} ` : ""}{c.name} <span className="text-brand-navy/50 text-xs">+{c.phone_code}</span>
              </button>
            ))}
          </div>
        )}
      </div>
      {!ok && local && (
        <div className="text-[11px] text-red-700 mt-1">
          Must be {localMin}–{localMax} digits for +{dial}
        </div>
      )}
    </div>
  );
}
