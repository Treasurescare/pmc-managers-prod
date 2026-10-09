import { useState } from "react";

export function Field({ label, children, hint, error, required }) {
  return (
    <label className="block">
      <span className="pmc-label">
        {label}
        {required && <span className="text-red-600 ml-1" aria-label="required">*</span>}
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
