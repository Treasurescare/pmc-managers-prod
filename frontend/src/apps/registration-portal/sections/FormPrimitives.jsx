export function Field({ label, children, hint }) {
  return (
    <label className="block">
      <span className="pmc-label">{label}</span>
      {children}
      {hint && <span className="block text-[11px] text-brand-navy/50 mt-1">{hint}</span>}
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
