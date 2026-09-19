import { useState } from "react";
import { toast } from "sonner";
import { api, formatApiError, showApiError } from "@/lib/api";

/**
 * CommitteeList v3 — dissolve + resend-invite via `api` axios helper.
 *
 *   * Root-cause bug (2026-09-19): the previous version used a raw `fetch()`
 *     that never attached the `X-CSRF-Token` header, so the backend
 *     `POST /api/v1/committees/close` returned HTTP 403 "CSRF token missing
 *     or invalid" — the committee stayed open, and the operator saw two
 *     zombie active committees they could not dissolve. Because of the 403,
 *     `create_committee` then returned HTTP 409 ("Open committee already
 *     exists for this tender") when they tried to form a new one — hence
 *     the "neither formed" report.
 *   * Fix: use the shared `api` axios instance (which already adds the CSRF
 *     header on every non-GET request) instead of raw `fetch`.
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
      await api.post("/api/v1/committees/close", {
        committee_id: c.id, decision: "dissolved", remarks: reason.trim(),
      });
      toast.success("Committee dissolved", {
        description: `${c.notice_ref} · reason: "${reason.trim().slice(0, 80)}${reason.trim().length > 80 ? '…' : ''}"`,
      });
      onChange?.();
    } catch (e) { showApiError(e, { fallbackTitle: "Dissolve failed" }); }
    finally { setBusyId(null); }
  };

  const resendInvite = async (c, invIdx) => {
    setBusyId(`${c.id}-${invIdx}`);
    try {
      await api.post(`/api/v1/committees/${c.id}/external/${invIdx}/resend`);
      toast.success("Invite resent", {
        description: `An email is on its way to ${c.external_invitees?.[invIdx]?.email || "the invitee"}.`,
      });
    } catch (e) { showApiError(e, { fallbackTitle: "Resend failed" }); }
    finally { setBusyId(null); }
  };

  if (!committees.length) return null;
  // Only show OPEN committees under "Active committees". Dissolved / closed
  // committees appear in a "Recently closed" strip below so the operator
  // still has audit visibility but doesn't confuse them with active ones.
  const active = committees.filter((c) => c.status === "open");
  const closed = committees.filter((c) => c.status !== "open");
  if (!active.length && !closed.length) return null;
  return (
    <div className="mb-6">
      <div className="pmc-label mb-2">Active committees ({active.length})</div>
      <div className="grid gap-3 md:grid-cols-2">
        {active.map((c) => {
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
      {closed.length > 0 && (
        <div className="mt-6" data-testid="committee-closed-section">
          <div className="pmc-label mb-2 text-brand-navy/60">Recently closed / dissolved ({closed.length})</div>
          <div className="grid gap-2 md:grid-cols-2">
            {closed.slice(0, 6).map((c) => (
              <div key={c.id} className="border border-slate-200 bg-slate-50/50 p-3 text-xs opacity-70"
                   data-testid={`committee-closed-${c.notice_ref}`}>
                <div className="flex items-baseline justify-between">
                  <span className="font-mono text-brand-navy-soft">{c.notice_ref}</span>
                  <span className="uppercase tracking-widest text-[10px] text-brand-navy/60">{c.status}</span>
                </div>
                {c.close_remarks && (
                  <div className="mt-1 italic text-brand-navy/60 line-clamp-2">Reason: {c.close_remarks}</div>
                )}
                {c.closed_at && (
                  <div className="mt-1 text-brand-navy/40">Closed {c.closed_at.slice(0, 10)}</div>
                )}
              </div>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
