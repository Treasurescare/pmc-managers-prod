import { useEffect, useState } from "react";
import { staffApi } from "@/lib/api";

const ROLE_LABELS = {
  admin: "Admin", reviewer: "Reviewer", escrow_agent: "Escrow Agent",
  certifier: "Certifier", legal_counsel: "Legal Counsel",
  accounting: "Accounting", committee_member: "Committee Member",
  auditor: "Auditor", support: "Support",
};

// Map a role_code to the list of staff whose roles array (or legacy single role)
// contains that role. Backend admin_users keep `roles: [...]` for multi-role seats.
function filterStaffForRole(allStaff, roleCode) {
  return allStaff.filter((s) => {
    const r = s.roles || [s.role].filter(Boolean);
    return r.includes(roleCode);
  });
}

/**
 * MatrixEditor — v50h.
 * Adds per-step assignee picker: dropdown of staff whose role matches
 * the step's role_code. Leave the picker on "— Any user with this role —"
 * to keep pool-routing. Pick a specific person to lock the step.
 */
export default function MatrixEditor({ matrixDraft, setMatrixDraft, matrices, onSave }) {
  const [allStaff, setAllStaff] = useState([]);
  useEffect(() => {
    staffApi.listStaff().then((rows) => setAllStaff(Array.isArray(rows) ? rows : []))
      .catch(() => setAllStaff([]));
  }, []);

  const setStep = (i, patch) => {
    const arr = [...matrixDraft.steps];
    arr[i] = { ...arr[i], ...patch };
    setMatrixDraft({ ...matrixDraft, steps: arr });
  };
  const reorder = (i, j) => {
    const arr = [...matrixDraft.steps];
    [arr[i], arr[j]] = [arr[j], arr[i]];
    arr.forEach((x, idx) => { x.order = idx + 1; });
    setMatrixDraft({ ...matrixDraft, steps: arr });
  };

  return (
    <>
      <div className="bg-white border p-4 mb-4" data-testid="matrix-editor">
        <div className="flex gap-2 mb-3">
          <input value={matrixDraft.name}
            onChange={(e) => setMatrixDraft({ ...matrixDraft, name: e.target.value })}
            className="flex-1 px-3 py-2 border" placeholder="Matrix name" />
          <button onClick={onSave} data-testid="matrix-save"
            className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
            Save matrix
          </button>
        </div>
        <table className="w-full text-sm">
          <thead className="text-xs text-brand-navy/60">
            <tr>
              <th className="text-left w-6">#</th>
              <th className="text-left">Role</th>
              <th className="text-left">Assignee</th>
              <th className="text-left">Action</th>
              <th className="text-right w-16">SLA (h)</th>
              <th className="text-center w-14">Move</th>
              <th className="text-center w-8">Del</th>
            </tr>
          </thead>
          <tbody>
            {matrixDraft.steps.map((s, i) => {
              const roleStaff = filterStaffForRole(allStaff, s.role_code);
              return (
                <tr key={`step-${s.role_code}-${s.order ?? i}`} className="border-t align-top"
                    data-testid={`matrix-step-${i}`}>
                  <td className="py-2">{s.order}</td>
                  <td className="py-2 pr-2">
                    <select value={s.role_code}
                      onChange={(e) => setStep(i, { role_code: e.target.value, assignee_user_id: null, assignee_email: null, assignee_name: null })}
                      className="border px-2 py-1 text-xs w-full bg-white"
                      data-testid={`matrix-role-${i}`}>
                      {Object.entries(ROLE_LABELS).map(([r, l]) =>
                        <option key={r} value={r}>{l}</option>)}
                    </select>
                  </td>
                  <td className="py-2 pr-2">
                    <select value={s.assignee_user_id || ""}
                      onChange={(e) => {
                        const uid = e.target.value;
                        const u = roleStaff.find((x) => x.id === uid);
                        setStep(i, {
                          assignee_user_id: uid || null,
                          assignee_email: u ? u.email : null,
                          assignee_name: u ? u.name : null,
                        });
                      }}
                      className="border px-2 py-1 text-xs w-full bg-white"
                      data-testid={`matrix-assignee-${i}`}>
                      <option value="">— Any user with this role —</option>
                      {roleStaff.map((u) => (
                        <option key={u.id} value={u.id}>{u.name || u.email} · {u.email}</option>
                      ))}
                    </select>
                    {roleStaff.length === 0 && (
                      <div className="text-[10px] text-amber-700 mt-1">
                        No staff with role {ROLE_LABELS[s.role_code] || s.role_code} — add one in Masters → Staff.
                      </div>
                    )}
                  </td>
                  <td className="py-2 pr-2">
                    <input value={s.action_label}
                      onChange={(e) => setStep(i, { action_label: e.target.value })}
                      className="w-full border px-2 py-1 text-xs"
                      data-testid={`matrix-action-${i}`} />
                  </td>
                  <td className="py-2 text-right">
                    <input type="number" min="1" value={s.sla_hours}
                      onChange={(e) => setStep(i, { sla_hours: Number(e.target.value) })}
                      className="w-20 border px-2 py-0.5 text-right" />
                  </td>
                  <td className="py-2 text-center">
                    <button type="button" disabled={i === 0} onClick={() => reorder(i, i - 1)}
                      className="text-xs px-1 disabled:opacity-30"
                      data-testid={`matrix-up-${i}`}>↑</button>
                    <button type="button" disabled={i === matrixDraft.steps.length - 1}
                      onClick={() => reorder(i, i + 1)}
                      className="text-xs px-1 disabled:opacity-30"
                      data-testid={`matrix-down-${i}`}>↓</button>
                  </td>
                  <td className="py-2 text-center">
                    <button type="button"
                      onClick={() => {
                        const arr = matrixDraft.steps.filter((_, idx) => idx !== i);
                        arr.forEach((x, idx) => { x.order = idx + 1; });
                        setMatrixDraft({ ...matrixDraft, steps: arr });
                      }}
                      className="text-xs text-red-600 hover:underline"
                      data-testid={`matrix-del-${i}`}>×</button>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        <button type="button"
          onClick={() => {
            const nextOrder = matrixDraft.steps.length + 1;
            setMatrixDraft({ ...matrixDraft,
              steps: [...matrixDraft.steps, {
                order: nextOrder, role_code: "reviewer",
                action_label: "Review step", sla_hours: 24, required: true,
                assignee_user_id: null, assignee_email: null, assignee_name: null,
              }] });
          }}
          className="mt-3 px-3 py-1.5 text-xs border border-dashed border-brand-navy/30 hover:bg-slate-50"
          data-testid="matrix-add-step">+ Add step</button>
      </div>
      <div className="bg-white border">
        <div className="pmc-label p-3 border-b">Saved matrices</div>
        {matrices.map((m) => (
          <div key={m.id} className="border-b p-3 text-sm" data-testid={`matrix-row-${m.name}`}>
            <strong>{m.name}</strong> · {m.steps?.length} steps · applies to {m.applies_to}
            {m.steps && m.steps.some((s) => s.assignee_email) && (
              <span className="ml-2 text-[10px] text-emerald-800 bg-emerald-100 px-1.5 py-0.5">
                has assignees
              </span>
            )}
          </div>
        ))}
        {matrices.length === 0 && <div className="p-6 text-sm text-slate-500">No matrices saved yet.</div>}
      </div>
    </>
  );
}
