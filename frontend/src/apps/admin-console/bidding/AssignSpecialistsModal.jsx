import { useEffect, useState } from "react";

/**
 * v56 — AssignSpecialistsModal. Lets an admin assign (or clear) a specialist
 * staff member per role on a bid. Each dropdown lists only staff holding that
 * role, tagged with their country scope ("Global" when blank). Calls
 * onAssign(role, staffId) which POSTs /bids/{id}/assign.
 */
const ASSIGN_ROLES = [
  ["escrow_agent", "Escrow Agent"],
  ["certifier", "Certifier"],
  ["legal_counsel", "Legal Counsel"],
  ["accounting", "Accounting"],
  ["committee_member", "Committee Member"],
];

const scopeTag = (s) =>
  (s.country_scope && s.country_scope.length) ? s.country_scope.join("/") : "Global";

export default function AssignSpecialistsModal({ bid, staffList, onAssign, onClose }) {
  const [assignments, setAssignments] = useState({});
  const [saving, setSaving] = useState(null);

  useEffect(() => {
    if (!bid) return;
    const a = { ...(bid.assignments || {}) };
    // Legacy certifier field compatibility.
    if (!a.certifier && bid.assigned_certifier_id) a.certifier = bid.assigned_certifier_id;
    setAssignments(a);
  }, [bid]);

  if (!bid) return null;

  const change = async (role, staffId) => {
    setSaving(role);
    try {
      const res = await onAssign(role, staffId);
      // Server returns the authoritative assignments map.
      if (res && res.assignments) setAssignments(res.assignments);
      else setAssignments((prev) => {
        const next = { ...prev };
        if (staffId) next[role] = staffId; else delete next[role];
        return next;
      });
    } finally {
      setSaving(null);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4"
      data-testid="assign-specialists-modal">
      <div className="bg-white rounded-lg p-6 max-w-lg w-full space-y-4">
        <div>
          <h3 className="text-lg font-serif text-brand-navy">Assign specialists</h3>
          <div className="text-xs text-brand-navy/60 font-mono mt-0.5">
            {bid.bid_ref} · {bid.notice_ref}
          </div>
        </div>

        <div className="space-y-3">
          {ASSIGN_ROLES.map(([role, label]) => {
            const eligible = (staffList || []).filter(
              (s) => (s.roles || [s.role] || []).includes(role) && s.is_active !== false
            );
            const current = assignments[role] || "";
            return (
              <label key={role} className="block text-sm" data-testid={`assign-row-${role}`}>
                <span className="text-[10px] uppercase tracking-widest text-brand-navy/60">{label}</span>
                <select value={current} disabled={saving === role}
                  onChange={(e) => change(role, e.target.value)}
                  data-testid={`assign-select-${role}`}
                  className="mt-1 w-full border border-brand-navy/20 rounded px-3 py-2 text-sm bg-white disabled:opacity-50">
                  <option value="">Unassigned — any {label} in country scope</option>
                  {eligible.map((s) => (
                    <option key={s.id} value={s.id}>
                      {(s.name || s.email)} — {scopeTag(s)}
                    </option>
                  ))}
                </select>
                {eligible.length === 0 && (
                  <span className="text-[10px] text-amber-700">No active staff hold this role.</span>
                )}
              </label>
            );
          })}
        </div>

        <div className="flex justify-end">
          <button onClick={onClose} data-testid="assign-specialists-close"
            className="px-4 py-2 text-sm border rounded">Done</button>
        </div>
      </div>
    </div>
  );
}
