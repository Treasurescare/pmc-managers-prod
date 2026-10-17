import { useEffect, useMemo, useState } from "react";

export function Field({ label, children, hint, error, required }) {
  return (
    <label className="block">
      <span className="pmc-label flex items-center gap-2">
        <span>{label}</span>
        {/* v52cy — the previous `*` was a thin red asterisk that admins
            kept missing. Replaced with a bold REQUIRED pill so mandatory
            fields visually jump out of the Section D/E grid. */}
        {required && (
          <span className="inline-flex items-center text-[9px] font-bold tracking-widest px-1.5 py-0.5 bg-red-600 text-white rounded-sm"
                aria-label="required" data-testid="field-required-pill">
            REQUIRED
          </span>
        )}
      </span>
      {children}
      {error && <span className="block text-[11px] text-red-600 mt-1">{error}</span>}
      {!error && hint && <span className="block text-[11px] text-brand-navy/50 mt-1">{hint}</span>}
    </label>
  );
}

export function Input({ testId, ...rest }) {
  return (
    <input
      data-testid={testId}
      className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white"
      {...rest}
    />
  );
}

/**
 * v52cy — NumericInput: preserves commas and spaces in the display while
 * typing (so "1,000" stays "1,000") and only commits a parsed number to
 * form state on blur / explicit commit. The previous turnover + employees
 * fields called `parseFloat(replace(/,/g,""))` on every keystroke, which
 * made it look as if the comma key was blocked ("1,000" immediately
 * became 1000 on screen).
 *
 * Props:
 *   value       — number (or null) currently in form state
 *   onCommit    — fn(number|null) called on blur with the parsed value
 *   integer     — true for employees-count style fields
 */
export function NumericInput({ testId, value, onCommit, integer = false, ...rest }) {
  const formatted = value == null || value === "" ? "" :
    (integer ? Number(value).toLocaleString("en-US", { maximumFractionDigits: 0 })
             : Number(value).toLocaleString("en-US"));
  const [raw, setRaw] = useState(formatted);
  const [focused, setFocused] = useState(false);
  // Keep the raw string in sync with external value changes while not focused
  // (e.g. after a save round-trip reformats the number).
  useEffect(() => { if (!focused) setRaw(formatted); }, [formatted, focused]);
  const commit = () => {
    setFocused(false);
    const stripped = raw.replace(/[^\d.\-]/g, "");
    if (stripped === "" || stripped === "-" || stripped === ".") {
      onCommit && onCommit(null);
      setRaw("");
      return;
    }
    const n = integer ? parseInt(stripped, 10) : parseFloat(stripped);
    if (isNaN(n)) { onCommit && onCommit(null); setRaw(""); return; }
    onCommit && onCommit(n);
    setRaw(integer ? n.toLocaleString("en-US", { maximumFractionDigits: 0 })
                   : n.toLocaleString("en-US"));
  };
  return (
    <input
      data-testid={testId}
      type="text"
      inputMode={integer ? "numeric" : "decimal"}
      value={raw}
      onFocus={() => setFocused(true)}
      onChange={(e) => setRaw(e.target.value.replace(/[^\d,.\-\s]/g, ""))}
      onBlur={commit}
      onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); commit(); } }}
      className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white"
      {...rest}
    />
  );
}

/**
 * Bug #30 — Client-side validated email input. Shows inline error until the
 * user enters a syntactically valid address. Non-blocking (submits still fire
 * — the backend has authoritative validation) but stops silent typos.
 */
const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/;
export function EmailInput({ testId, value, onChange, ...rest }) {
  const [touched, setTouched] = useState(false);
  const showError = touched && value && !EMAIL_RE.test(String(value).trim());
  return (
    <>
      <input
        type="email"
        inputMode="email"
        autoComplete="email"
        data-testid={testId}
        value={value || ""}
        onChange={onChange}
        onBlur={() => setTouched(true)}
        aria-invalid={showError || undefined}
        className={"mt-1 w-full px-4 py-3 border focus:outline-none text-brand-navy bg-white " +
          (showError ? "border-red-500 focus:border-red-500"
                     : "border-brand-navy/20 focus:border-brand-navy-soft")}
        {...rest}
      />
      {showError && (
        <span className="block text-[11px] text-red-600 mt-1"
              data-testid={testId ? `${testId}-error` : undefined}>
          Enter a valid email like name@company.com
        </span>
      )}
    </>
  );
}

/**
 * Bug #30 — Digits-only phone input with sensible length rules. Accepts an
 * optional leading '+' and spaces/hyphens, but blocks alpha characters. When
 * the user pastes garbage we still preserve the raw value in state (so nothing
 * is lost) — we just surface an inline error until it's cleaned up.
 */
const PHONE_RE = /^\+?[0-9][0-9\s\-()]{6,19}$/;
// v46t — tighter E.164 rule: after stripping spaces/hyphens/brackets the digit
// count must be 7-15 and (if provided) start with '+'.
const E164_RE = /^\+?[1-9]\d{6,14}$/;
export function PhoneInput({ testId, value, onChange, ...rest }) {
  const [touched, setTouched] = useState(false);
  const raw = value == null ? "" : String(value);
  const compact = raw.replace(/[\s\-()]/g, "");
  const shapeOk = !raw || PHONE_RE.test(raw.trim());
  const e164Ok = !compact || E164_RE.test(compact);
  const showError = touched && raw && (!shapeOk || !e164Ok);
  return (
    <>
      <input
        type="tel"
        inputMode="tel"
        autoComplete="tel"
        data-testid={testId}
        value={raw}
        onChange={(e) => {
          // Strip alpha eagerly so users can't leave stray letters behind.
          const cleaned = e.target.value.replace(/[^\d+\s\-()]/g, "");
          onChange({ ...e, target: { ...e.target, value: cleaned } });
        }}
        onBlur={() => setTouched(true)}
        aria-invalid={showError || undefined}
        className={"mt-1 w-full px-4 py-3 border focus:outline-none text-brand-navy bg-white " +
          (showError ? "border-red-500 focus:border-red-500"
                     : "border-brand-navy/20 focus:border-brand-navy-soft")}
        {...rest}
      />
      {showError && (
        <span className="block text-[11px] text-red-600 mt-1"
              data-testid={testId ? `${testId}-error` : undefined}>
          Enter international format 7–15 digits, e.g. +7 701 555 0100
        </span>
      )}
    </>
  );
}

/**
 * v54e — Phone with country ISD dropdown. The ISD code is picked from the
 * countries master (native select type-ahead works — focus and type "ind"
 * to jump to India); the national number accepts digits/spaces/hyphens and
 * is live-validated to 4–14 digits. Stored as "+91 98765 43210" so existing
 * backend fields and E.164 checks keep working.
 */
export function PhoneWithIsd({ testId, value, onChange, countries = [], defaultCountry }) {
  const parsed = (() => {
    const m = /^\s*\+(\d{1,4})[\s\-]*(.*)$/.exec(String(value || ""));
    return m ? { isd: m[1], national: m[2] } : { isd: "", national: String(value || "") };
  })();
  const defaultIsd = useMemo(() => {
    const c = (countries || []).find((x) => x.code === defaultCountry);
    return c?.phone_code ? String(c.phone_code).replace(/^\+/, "") : "";
  }, [countries, defaultCountry]);
  const isd = parsed.isd || defaultIsd;
  const national = parsed.national || "";

  const emit = (nextIsd, nextNationalRaw) => {
    const n = String(nextNationalRaw || "").replace(/[^\d\s\-()]/g, "").trim();
    const v = n ? (nextIsd ? `+${nextIsd} ${n}` : n) : "";
    onChange({ target: { value: v } });
  };

  const digits = national.replace(/[^\d]/g, "");
  const showError = !!national && (digits.length < 4 || digits.length > 14);

  const options = useMemo(() => {
    const seen = new Map();
    for (const c of countries || []) {
      const pc = String(c.phone_code || "").replace(/^\+/, "").trim();
      if (!pc) continue;
      if (!seen.has(pc)) seen.set(pc, []);
      seen.get(pc).push(c.code);
    }
    return [...seen.entries()].sort((a, b) => Number(a[0]) - Number(b[0]));
  }, [countries]);

  return (
    <div data-testid={testId ? `${testId}-with-isd` : undefined}>
      <div className="mt-1 flex gap-2">
        <select
          value={isd}
          onChange={(e) => emit(e.target.value, national)}
          data-testid={testId ? `${testId}-isd` : undefined}
          className="w-36 shrink-0 px-2 py-3 border border-brand-navy/20 bg-white text-brand-navy text-sm focus:outline-none focus:border-brand-navy-soft">
          <option value="">+ ISD</option>
          {options.map(([pc, codes]) => (
            <option key={pc} value={pc}>
              +{pc} · {codes.slice(0, 3).join("/")}{codes.length > 3 ? "…" : ""}
            </option>
          ))}
        </select>
        <input
          type="tel"
          inputMode="tel"
          data-testid={testId}
          value={national}
          onChange={(e) => emit(isd, e.target.value)}
          placeholder="number without country code"
          aria-invalid={showError || undefined}
          className={"flex-1 px-4 py-3 border focus:outline-none text-brand-navy bg-white " +
            (showError ? "border-red-500 focus:border-red-500"
                       : "border-brand-navy/20 focus:border-brand-navy-soft")} />
      </div>
      {showError && (
        <span className="block text-[11px] text-red-600 mt-1"
              data-testid={testId ? `${testId}-error` : undefined}>
          Enter the national number without the country code — 4 to 14 digits.
        </span>
      )}
    </div>
  );
}
