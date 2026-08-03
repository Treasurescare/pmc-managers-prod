const ROLE_LABELS = {
  admin: "Admin", reviewer: "Reviewer", escrow_agent: "Escrow Agent",
  certifier: "Certifier", legal_counsel: "Legal Counsel",
  accounting: "Accounting", committee_member: "Committee Member",
  auditor: "Auditor", support: "Support",
};

/**
 * StaffTab — extracted from MastersPanel. New-staff form + roster table.
 */
export default function StaffTab({
  staff, showStaffNew, setShowStaffNew,
  staffDraft, setStaffDraft, onCreate, onToggleRole,
}) {
  return (
    <>
      <div className="flex justify-between mb-4">
        <div className="text-sm text-brand-navy/70">{staff.length} staff records</div>
        <button onClick={() => setShowStaffNew(!showStaffNew)} data-testid="staff-new-toggle"
          className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
          {showStaffNew ? "Cancel" : "New Staff"}
        </button>
      </div>
      {showStaffNew && (
        <div className="bg-white border p-4 mb-4 grid gap-2 md:grid-cols-3" data-testid="staff-new-form">
          <input placeholder="Email" value={staffDraft.email}
            onChange={(e) => setStaffDraft({ ...staffDraft, email: e.target.value.toLowerCase() })}
            className="px-3 py-2 border" data-testid="staff-email" />
          <input placeholder="Full name" value={staffDraft.name}
            onChange={(e) => setStaffDraft({ ...staffDraft, name: e.target.value })}
            className="px-3 py-2 border" data-testid="staff-name" />
          <input placeholder="Password" value={staffDraft.password}
            onChange={(e) => setStaffDraft({ ...staffDraft, password: e.target.value })}
            className="px-3 py-2 border" data-testid="staff-password" />
          <div className="md:col-span-3">
            <div className="pmc-label mb-1">Roles (multi-select)</div>
            <div className="grid grid-cols-3 gap-1 text-xs">
              {Object.entries(ROLE_LABELS).map(([r, l]) => (
                <label key={r} className="flex items-center gap-1">
                  <input type="checkbox" checked={staffDraft.roles.includes(r)}
                    onChange={() => onToggleRole(r)} data-testid={`staff-role-${r}`} />
                  {l}
                </label>
              ))}
            </div>
          </div>
          <label className="text-sm">
            <span>Hierarchy level</span>
            <input type="number" min="1" max="10" value={staffDraft.hierarchy_level}
              onChange={(e) => setStaffDraft({ ...staffDraft, hierarchy_level: Number(e.target.value) })}
              className="mt-1 w-full px-3 py-2 border" />
          </label>
          <button onClick={onCreate} data-testid="staff-create"
            className="md:col-span-3 px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white">
            Create staff
          </button>
        </div>
      )}
      <div className="bg-white border">
        <table className="w-full text-sm">
          <thead className="text-xs text-brand-navy/60 border-b">
            <tr><th className="text-left px-3 py-2">Email</th><th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Roles</th><th className="text-center px-3 py-2">Level</th>
              <th className="text-center px-3 py-2">Active</th></tr>
          </thead>
          <tbody>
            {staff.map((s) => (
              <tr key={s.id} className="border-t" data-testid={`staff-row-${s.email}`}>
                <td className="px-3 py-2 font-mono text-xs">{s.email}</td>
                <td className="px-3 py-2">{s.name}</td>
                <td className="px-3 py-2 text-xs">{(s.roles || [s.role]).join(", ")}</td>
                <td className="px-3 py-2 text-center">{s.hierarchy_level}</td>
                <td className="px-3 py-2 text-center">{s.is_active !== false ? "✓" : "×"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </>
  );
}
