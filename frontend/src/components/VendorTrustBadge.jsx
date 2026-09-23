/**
 * v46 — Vendor trust badge (Platinum / Gold / Silver / Bronze / None).
 *
 * Rendered anywhere a vendor's public score matters: landing "Trusted vendors"
 * strip, public vendor profile, admin moderation table, vendor portal peer
 * search results.
 */
const TIER_STYLES = {
  platinum: { bg: "bg-slate-900",  fg: "text-amber-100",   label: "Platinum" },
  gold:     { bg: "bg-amber-500",   fg: "text-white",       label: "Gold" },
  silver:   { bg: "bg-slate-300",   fg: "text-slate-900",   label: "Silver" },
  bronze:   { bg: "bg-orange-700",  fg: "text-orange-50",   label: "Bronze" },
  none:     { bg: "bg-slate-100",   fg: "text-slate-500",   label: "Unrated" },
};

export function VendorTrustBadge({ tier = "none", score = null, count = 0, compact = false, testid }) {
  const t = TIER_STYLES[tier] || TIER_STYLES.none;
  return (
    <span data-testid={testid || `trust-badge-${tier}`}
          className={`inline-flex items-center gap-2 px-3 py-1 text-[11px] font-semibold uppercase tracking-widest ${t.bg} ${t.fg}`}>
      <svg aria-hidden width="14" height="14" viewBox="0 0 24 24" fill="currentColor">
        <path d="M12 2l3 6.5 7 .8-5.3 4.7 1.6 6.9L12 17l-6.3 3.9 1.6-6.9L2 9.3l7-.8L12 2z"/>
      </svg>
      <span>{t.label}</span>
      {!compact && score !== null && (
        <span className="opacity-80 font-mono normal-case tracking-normal">
          · {score}/100 · {count} review{count === 1 ? "" : "s"}
        </span>
      )}
    </span>
  );
}

export default VendorTrustBadge;
