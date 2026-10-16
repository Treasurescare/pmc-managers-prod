import { useEffect, useState } from "react";
import { toast } from "sonner";
import { InfoDot } from "@/components/InfoDot";
import { useListPager } from "@/components/ListPager";
import { permissionsApi } from "@/lib/api";

const ROLE_LABELS = {
  admin: "Admin", reviewer: "Reviewer", escrow_agent: "Escrow Agent",
  certifier: "Certifier", legal_counsel: "Legal Counsel",
  accounting: "Accounting", committee_member: "Committee Member",
  auditor: "Auditor", support: "Support",
};

// v53p — map role → the Staff Portal queue the user will land on after sign-in.
const ROLE_QUEUE = {
  admin: "/admin  — full admin console (all pages in sidebar)",
  reviewer: "/admin — review notices, bids, vendor registrations",
  escrow_agent: "/staff — EMD-paid bids awaiting escrow acceptance",
  certifier: "/staff — admin-flagged bids + assigned site inspections",
  legal_counsel: "/staff — certifier-cleared bids awaiting legal review",
  accounting: "/staff — legal-cleared bids awaiting accounting",
  committee_member: "/staff — accounting-cleared bids awaiting committee award",
  auditor: "/staff — read-only audit ledger access",
  support: "/staff — vendor and bid support tickets",
};

const ACTIONS = ["view", "create", "modify", "delete", "publish"];

/**
 * StaffTab — new-staff form + roster table with inline edit / role change /
 * activation toggle / password reset. Backed by PATCH /api/v1/staff/{id}.
 */
export default function StaffTab({
  staff, showStaffNew, setShowStaffNew,
  staffDraft, setStaffDraft, onCreate, onToggleRole, onUpdate,
}) {
  const [editingId, setEditingId] = useState(null);
  const [editDraft, setEditDraft] = useState(null);
  const [saving, setSaving] = useState(false);
  const { paged, controls } = useListPager(staff, { testid: "staff-pager" });
  // v53p — permission preview drawer. Lazy-loaded on first open.
  const [permPreviewOpen, setPermPreviewOpen] = useState(false);
  const [permRows, setPermRows] = useState(null);
  useEffect(() => {
    if (!permPreviewOpen || permRows) return;
    permissionsApi.get()
      .then((r) => setPermRows(r.rows || []))
      .catch(() => setPermRows([]));
  }, [permPreviewOpen, permRows]);

  const previewRoles = (showStaffNew ? staffDraft.roles : (editDraft?.roles || []));

  const startEdit = (s) => {
    setEditingId(s.id);
    setEditDraft({
      name: s.name || "",
      roles: [...(s.roles || (s.role ? [s.role] : []))],
      hierarchy_level: s.hierarchy_level || 3,
      is_active: s.is_active !== false,
      is_escrow_signatory: !!s.is_escrow_signatory,
      password: "",
    });
  };
  const cancelEdit = () => { setEditingId(null); setEditDraft(null); };
  const toggleEditRole = (r) => {
    setEditDraft((d) => ({
      ...d,
      roles: d.roles.includes(r) ? d.roles.filter((x) => x !== r) : [...d.roles, r],
    }));
  };
  const saveEdit = async (s) => {
    if (!editDraft.roles.length) return toast.error("At least one role is required");
    setSaving(true);
    try {
      // Only send changed / non-empty fields
      const patch = {
        name: editDraft.name,
        roles: editDraft.roles,
        hierarchy_level: editDraft.hierarchy_level,
        is_active: editDraft.is_active,
        is_escrow_signatory: !!editDraft.is_escrow_signatory,
      };
      if (editDraft.password) patch.password = editDraft.password;
      await onUpdate(s.id, patch);
      cancelEdit();
    } finally {
      setSaving(false);
    }
  };
  const toggleActive = (s) => onUpdate(s.id, { is_active: !(s.is_active !== false) });

  // MP-01 fix — clone an existing staff member's role setup into the new-staff form
  const cloneFrom = (s) => {
    setStaffDraft({
      email: "", name: "", password: "",
      roles: [...(s.roles || (s.role ? [s.role] : ["reviewer"]))],
      hierarchy_level: s.hierarchy_level || 3,
    });
    setShowStaffNew(true);
    window?.scrollTo?.({ top: 0, behavior: "smooth" });
  };

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
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Email<InfoDot tip="Login email. Auto-lowercased. Must be unique across all staff records." />
            <input placeholder="Email" value={staffDraft.email}
              onChange={(e) => setStaffDraft({ ...staffDraft, email: e.target.value.toLowerCase() })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="staff-email" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Full name<InfoDot tip="Displayed on committee sign-offs and audit log entries." />
            <input placeholder="Full name" value={staffDraft.name}
              onChange={(e) => setStaffDraft({ ...staffDraft, name: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="staff-name" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Password<InfoDot tip="Initial password. The staff member is forced to change it on first login." />
            <input placeholder="Password" value={staffDraft.password}
              onChange={(e) => setStaffDraft({ ...staffDraft, password: e.target.value })}
              className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" data-testid="staff-password" />
          </label>
          <div className="md:col-span-3">
            <div className="pmc-label mb-1">Roles (multi-select)<InfoDot tip="One user can hold multiple roles. Roles drive dashboard visibility and permission-matrix gates." /></div>
            <div className="grid grid-cols-3 gap-1 text-xs">
              {Object.entries(ROLE_LABELS).map(([r, l]) => (
                <label key={r} className="flex items-center gap-1">
                  <input type="checkbox" checked={staffDraft.roles.includes(r)}
                    onChange={() => onToggleRole(r)} data-testid={`staff-role-${r}`} />
                  {l}
                </label>
              ))}
            </div>
            {/* v53p — permission preview drawer trigger */}
            <button type="button"
                    onClick={() => setPermPreviewOpen(!permPreviewOpen)}
                    disabled={!staffDraft.roles.length}
                    data-testid="staff-perm-preview-toggle"
                    className="mt-2 text-[11px] underline text-brand-navy disabled:opacity-40 disabled:no-underline">
              {permPreviewOpen ? "Hide" : "Preview"} what this staff can do →
            </button>
          </div>
          <label className="text-sm">
            <span>Hierarchy level</span>
            <input type="number" min="1" max="10" value={staffDraft.hierarchy_level}
              onChange={(e) => setStaffDraft({ ...staffDraft, hierarchy_level: Number(e.target.value) })}
              className="mt-1 w-full px-3 py-2 border" />
          </label>
          {/* v53k — mark staff as PMC-side escrow signatory. Only ticked
              rows appear in the "PMC officer" dropdown when creating a
              joint escrow account. Without this the EMD escrow accept
              step has no routable signer. */}
          <label className="text-sm flex items-center gap-2 md:col-span-2">
            <input type="checkbox" checked={!!staffDraft.is_escrow_signatory}
              onChange={(e) => setStaffDraft({ ...staffDraft, is_escrow_signatory: e.target.checked })}
              data-testid="staff-escrow-signatory" />
            <span>Escrow signatory <InfoDot tip="Tick to let this staff member be picked as the PMC co-signer on a joint EMD escrow account." /></span>
          </label>
          <button onClick={onCreate} data-testid="staff-create"
            className="md:col-span-3 px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white">
            Create staff
          </button>

          {/* v53p — Permission preview drawer. Shows the exact rows from
              the permission matrix for the currently-ticked roles plus
              the landing route they'll see after sign-in. Avoids the "every
              new staff seems to get admin access" confusion. */}
          {permPreviewOpen && previewRoles.length > 0 && (
            <div className="md:col-span-3 border-2 border-brand-navy/30 bg-brand-pale/60 p-4"
                 data-testid="staff-perm-preview">
              <div className="font-semibold text-brand-navy mb-2">
                Permission preview for roles: {previewRoles.map((r) => ROLE_LABELS[r] || r).join(", ")}
              </div>
              <div className="text-xs text-brand-navy/70 mb-3">
                Landing routes after sign-in:
                <ul className="list-disc ml-5 mt-1">
                  {previewRoles.map((r) => (
                    <li key={r} data-testid={`staff-perm-route-${r}`}>
                      <b>{ROLE_LABELS[r] || r}:</b> {ROLE_QUEUE[r] || "/staff — specialist queue"}
                    </li>
                  ))}
                </ul>
              </div>
              {permRows === null && <div className="text-xs text-brand-navy/50 italic">Loading permission matrix…</div>}
              {permRows !== null && (
                <div className="bg-white border border-brand-navy/15 overflow-x-auto">
                  <table className="w-full text-xs">
                    <thead className="bg-brand-navy/5 text-brand-navy/70 uppercase tracking-wider">
                      <tr>
                        <th className="px-2 py-1 text-left">Role</th>
                        <th className="px-2 py-1 text-left">Doc type</th>
                        {ACTIONS.map((a) => <th key={a} className="px-2 py-1 text-center capitalize">{a}</th>)}
                      </tr>
                    </thead>
                    <tbody>
                      {previewRoles.flatMap((r) =>
                        permRows.filter((row) => row.role === r).map((row, i) => (
                          <tr key={`${r}-${i}`} className="border-t border-brand-navy/10"
                              data-testid={`staff-perm-row-${r}-${row.document_type}`}>
                            <td className="px-2 py-1 font-semibold">{ROLE_LABELS[r] || r}</td>
                            <td className="px-2 py-1 font-mono">{row.document_type}</td>
                            {ACTIONS.map((a) => (
                              <td key={a} className="px-2 py-1 text-center">
                                {row[a] ? <span className="text-emerald-600">✓</span> : <span className="text-brand-navy/20">·</span>}
                              </td>
                            ))}
                          </tr>
                        ))
                      )}
                      {previewRoles.every((r) => !permRows.some((row) => row.role === r)) && (
                        <tr><td colSpan={ACTIONS.length + 2} className="px-2 py-3 text-brand-navy/50 italic">
                          No explicit permission rows configured for these roles yet — defaults from Admin → Permissions apply.
                        </td></tr>
                      )}
                    </tbody>
                  </table>
                </div>
              )}
              <div className="text-[10px] text-brand-navy/50 mt-2">
                Admin role always has implicit full access; it is not shown in the matrix.
              </div>
            </div>
          )}
        </div>
      )}
      <div className="bg-white border">
        <table className="w-full text-sm">
          <thead className="text-xs text-brand-navy/60 border-b">
            <tr>
              <th className="text-left px-3 py-2">Email</th>
              <th className="text-left px-3 py-2">Name</th>
              <th className="text-left px-3 py-2">Roles</th>
              <th className="text-center px-3 py-2">Level</th>
              <th className="text-center px-3 py-2">Active</th>
              <th className="text-center px-3 py-2">Actions</th>
            </tr>
          </thead>
          <tbody>
            {paged.map((s) => {
              const isEditing = editingId === s.id;
              if (isEditing) {
                return (
                  <tr key={s.id} className="border-t bg-amber-50/50" data-testid={`staff-edit-row-${s.email}`}>
                    <td className="px-3 py-3 font-mono text-xs align-top">{s.email}</td>
                    <td className="px-3 py-3 align-top">
                      <input value={editDraft.name}
                        onChange={(e) => setEditDraft({ ...editDraft, name: e.target.value })}
                        className="w-full px-2 py-1 border text-sm" data-testid={`staff-edit-name-${s.email}`} />
                      <input type="password" placeholder="Reset password (leave blank to keep)"
                        value={editDraft.password}
                        onChange={(e) => setEditDraft({ ...editDraft, password: e.target.value })}
                        className="w-full px-2 py-1 border text-xs mt-1"
                        data-testid={`staff-edit-password-${s.email}`} />
                    </td>
                    <td className="px-3 py-3 align-top" colSpan={2}>
                      <div className="grid grid-cols-2 gap-1 text-xs">
                        {Object.entries(ROLE_LABELS).map(([r, l]) => (
                          <label key={r} className="flex items-center gap-1">
                            <input type="checkbox" checked={editDraft.roles.includes(r)}
                              onChange={() => toggleEditRole(r)}
                              data-testid={`staff-edit-role-${s.email}-${r}`} />
                            {l}
                          </label>
                        ))}
                      </div>
                      <label className="text-xs mt-2 block">
                        <span>Hierarchy level</span>
                        <input type="number" min="1" max="10" value={editDraft.hierarchy_level}
                          onChange={(e) => setEditDraft({ ...editDraft, hierarchy_level: Number(e.target.value) })}
                          className="mt-1 w-24 px-2 py-1 border"
                          data-testid={`staff-edit-level-${s.email}`} />
                      </label>
                    </td>
                    <td className="px-3 py-3 text-center align-top">
                      <label className="inline-flex items-center gap-1 text-xs cursor-pointer">
                        <input type="checkbox" checked={editDraft.is_active}
                          onChange={(e) => setEditDraft({ ...editDraft, is_active: e.target.checked })}
                          data-testid={`staff-edit-active-${s.email}`} />
                        Active
                      </label>
                      {/* v53k — toggle the PMC escrow-signatory flag inline. */}
                      <label className="inline-flex items-center gap-1 text-xs cursor-pointer mt-1 block">
                        <input type="checkbox" checked={!!editDraft.is_escrow_signatory}
                          onChange={(e) => setEditDraft({ ...editDraft, is_escrow_signatory: e.target.checked })}
                          data-testid={`staff-edit-escrow-signatory-${s.email}`} />
                        Escrow signatory
                      </label>
                    </td>
                    <td className="px-3 py-3 text-center align-top">
                      <div className="flex flex-col gap-1">
                        <button type="button" onClick={() => saveEdit(s)} disabled={saving}
                          data-testid={`staff-save-${s.email}`}
                          className="text-[10px] uppercase tracking-widest px-2 py-1 bg-brand-navy text-white disabled:opacity-50">
                          {saving ? "Saving…" : "Save"}
                        </button>
                        <button type="button" onClick={cancelEdit}
                          data-testid={`staff-cancel-${s.email}`}
                          className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy">
                          Cancel
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              }
              return (
                <tr key={s.id} className="border-t" data-testid={`staff-row-${s.email}`}>
                  <td className="px-3 py-2 font-mono text-xs">{s.email}</td>
                  <td className="px-3 py-2">{s.name}</td>
                  <td className="px-3 py-2 text-xs">
                    {(s.roles || [s.role]).join(", ")}
                    {s.is_escrow_signatory && (
                      <span data-testid={`staff-escrow-badge-${s.email}`}
                            title="Appears in the PMC-side dropdown when creating a joint escrow account"
                            className="ml-1 text-[9px] uppercase tracking-widest text-emerald-800 bg-emerald-50 border border-emerald-300 px-1.5 py-0.5">
                        escrow-signer
                      </span>
                    )}
                  </td>
                  <td className="px-3 py-2 text-center">{s.hierarchy_level}</td>
                  <td className="px-3 py-2 text-center">
                    <button type="button" onClick={() => toggleActive(s)}
                      data-testid={`staff-toggle-active-${s.email}`}
                      className={`text-xs font-semibold ${s.is_active !== false ? "text-emerald-700" : "text-slate-400"} hover:underline`}
                      title="Click to toggle activation">
                      {s.is_active !== false ? "✓" : "×"}
                    </button>
                  </td>
                  <td className="px-3 py-2 text-center">
                    <div className="flex items-center justify-center gap-1">
                      <button type="button" onClick={() => startEdit(s)}
                        data-testid={`staff-edit-${s.email}`}
                        className="text-[10px] uppercase tracking-widest px-2 py-1 bg-brand-navy text-white hover:bg-brand-navy-soft">
                        Edit
                      </button>
                      <button type="button" onClick={() => cloneFrom(s)}
                        data-testid={`staff-clone-${s.email}`}
                        className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy hover:bg-brand-navy hover:text-white">
                        Clone
                      </button>
                    </div>
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
        {controls}
      </div>
    </>
  );
}
