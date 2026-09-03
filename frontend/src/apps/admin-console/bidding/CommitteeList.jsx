import { useState } from "react";
import { toast } from "sonner";

const API = process.env.REACT_APP_BACKEND_URL;

/**
 * CommitteeList v2 — adds dissolve + resend-invite actions.
 *   * Dissolve  → closes an open committee with status="dissolved" + audit reason
 *   * Resend    → per-external-invitee resend of the accept email
 */
export default function CommitteeList({ committees, onChange }) {
  const [busyId, setBusyId] = useState(null);

  const dissolve = async (c) => {
    const reason = window.prompt("Reason for dissolving this committee (≥8 chars):", "");
    if (!reason || reason.trim().length < 8) {
      toast.error("Dissolve reason must be at least 8 characters.");
      return;
    }
    setBusyId(c.id);
    try {
      const r = await fetch(`${API}/api/v1/committees/close`, {
        method: "POST", credentials: "include",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          committee_id: c.id, decision: "dissolved", remarks: reason.trim(),
        }),
      });
      if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
      toast.success("Committee dissolved");
      onChange?.();
    } catch (e) { toast.error(e.message); }
    finally { setBusyId(null); }
  };

  const resendInvite = async (c, invIdx) => {
    setBusyId(`${c.id}-${invIdx}`);
    try {
      const r = await fetch(`${API}/api/v1/committees/${c.id}/external/${invIdx}/resend`, {
        method: "POST", credentials: "include",
      });
      if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
      toast.success("Invite resent");
    } catch (e) { toast.error(e.message); }
    finally { setBusyId(null); }
  };

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

              {c.status === "open" && (
                <div className="mt-2 flex flex-wrap gap-2">
                  <button type="button" onClick={() => dissolve(c)} disabled={busyId === c.id}
                    data-testid={`committee-dissolve-${c.notice_ref}`}
                    className="text-[10px] uppercase tracking-widest px-3 py-1 border border-red-400 text-red-700 hover:bg-red-50 disabled:opacity-50">
                    {busyId === c.id ? "Dissolving…" : "Dissolve committee"}
                  </button>
                </div>
              )}

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
                        {inv.status !== "accepted" && c.status === "open" && (
                          <button type="button" onClick={() => resendInvite(c, i)}
                            disabled={busyId === `${c.id}-${i}`}
                            data-testid={`committee-resend-${c.notice_ref}-${i}`}
                            className="text-[10px] uppercase tracking-widest px-2 py-0.5 border border-brand-navy/30 hover:bg-brand-navy hover:text-white">
                            {busyId === `${c.id}-${i}` ? "…" : "Resend"}
                          </button>
                        )}
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
