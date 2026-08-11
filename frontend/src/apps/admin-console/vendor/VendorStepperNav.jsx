/**
 * Horizontal step nav for the admin's new-vendor form (Sections A–E + Final).
 * Split out from AdminVendorCreate.jsx for maintainability.
 */
export default function VendorStepperNav({ steps, step, setStep }) {
  return (
    <nav className="mt-6 flex flex-wrap gap-2" data-testid="admin-vendor-stepper">
      {steps.map(([code, label]) => (
        <button
          key={code}
          onClick={() => setStep(code)}
          data-testid={`admin-vendor-step-${code}`}
          className={
            "px-4 py-2 text-[11px] uppercase tracking-widest border " +
            (step === code
              ? "bg-brand-navy text-white border-brand-navy"
              : "bg-white text-brand-navy/70 border-brand-navy/20")
          }
        >
          {label}
        </button>
      ))}
    </nav>
  );
}
