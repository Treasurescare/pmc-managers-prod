/**
 * CommitteeList — extracted from BiddingOpsPanel. Renders the "Active committees"
 * grid with per-committee external-invitee acceptance status.
 */
export default function CommitteeList({ committees }) {
  if (!committees.length) return null;
  return (
    <div className="mb-6">
      <div className="pmc-label mb-2">Active committees</div>
      <div className="grid gap-3 md:grid-cols-2">
        {committees.map((c) => {
          const ext = c.external_invitees || [];
          const acc = ext.filter((e) => e.status === "accepted").length;
          const dec = ext.filter((e) => e.status === "declined").length;
          const pending = ext.length - acc - dec;
          return (
            <div key={c.id} className="border border-brand-navy/10 bg-white p-4 text-sm"
                 data-testid={`committee-row-${c.notice_ref}`}>
              <div className="flex items-baseline justify-between gap-2">
                <div className="font-mono text-xs text-brand-navy-soft">{c.notice_ref}</div>
                <div className="text-xs">
                  Status: <strong className={c.status === "open" ? "text-emerald-700" : "text-brand-navy/60"}>{c.status}</strong>
                </div>
              </div>
              <div className="mt-1 text-xs text-brand-navy/70">
                {c.member_ids?.length || 0} internal · quorum {c.quorum}
              </div>
              {ext.length > 0 && (
                <div className="mt-3 border-t border-brand-navy/10 pt-2"
                     data-testid={`committee-ext-${c.notice_ref}`}>
                  <div className="pmc-label">External invitees ({ext.length})</div>
                  <div className="flex gap-3 text-[11px] mt-1">
                    <span className="text-emerald-700">✓ Accepted: {acc}</span>
                    <span className="text-red-600">✗ Declined: {dec}</span>
                    <span className="text-amber-600">⏳ Pending: {pending}</span>
                  </div>
                  <ul className="mt-2 space-y-1">
                    {ext.map((inv, i) => (
                      <li key={`${inv.email}-${i}`} className="text-xs flex items-center gap-2"
                          data-testid={`committee-ext-row-${c.notice_ref}-${i}`}>
                        <span className={
                          inv.status === "accepted" ? "text-emerald-700 font-semibold"
                          : inv.status === "declined" ? "text-red-600 font-semibold"
                          : "text-amber-700"
                        }>
                          {inv.status === "accepted" ? "✓" : inv.status === "declined" ? "✗" : "⏳"}
                        </span>
                        <span className="flex-1">
                          <strong>{inv.name}</strong> · {inv.email}
                          {inv.designation && <span className="text-brand-navy/60"> · {inv.designation}</span>}
                        </span>
                        <span className="text-brand-navy/40">{inv.status}</span>
                      </li>
                    ))}
                  </ul>
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}
