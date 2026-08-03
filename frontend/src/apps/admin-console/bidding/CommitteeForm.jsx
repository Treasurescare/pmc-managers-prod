import { toast } from "sonner";

/**
 * CommitteeForm — extracted from BiddingOpsPanel to reduce complexity.
 * Renders the "Form Committee" editor (notice ref, chair, members, quorum,
 * external invitees). Delegates the actual submit to the parent so the
 * parent still owns reload orchestration.
 */
export default function CommitteeForm({
  comDraft, setComDraft,
  extDraft, setExtDraft,
  staffList, admins,
  onSubmit,
}) {
  const addExtInvitee = () => {
    if (!extDraft.email || !extDraft.name) return toast.error("External invitee name and email required");
    setComDraft({ ...comDraft, external_invitees: [...comDraft.external_invitees, { ...extDraft }] });
    setExtDraft({ email: "", name: "", designation: "" });
  };
  const removeExtInvitee = (i) => {
    const copy = [...comDraft.external_invitees];
    copy.splice(i, 1);
    setComDraft({ ...comDraft, external_invitees: copy });
  };

  return (
    <div className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-3 md:grid-cols-4"
         data-testid="committee-new-form">
      <label className="md:col-span-2 text-sm">
        <span className="pmc-label">Notice ref (e.g. PMC-NOT-2026-0001)</span>
        <input value={comDraft.notice_ref}
          onChange={(e) => setComDraft({ ...comDraft, notice_ref: e.target.value })}
          className="mt-1 w-full px-3 py-2 border border-brand-navy/20"
          data-testid="committee-notice-ref" />
      </label>
      <label className="text-sm">
        <span className="pmc-label">Chairperson</span>
        <select value={comDraft.chair}
          onChange={(e) => setComDraft({ ...comDraft, chair: e.target.value })}
          className="mt-1 w-full px-3 py-2 border border-brand-navy/20"
          data-testid="committee-chair">
          <option value="">Select…</option>
          {admins.map((a) => <option key={a.id} value={a.id}>{a.email}</option>)}
        </select>
      </label>
      <label className="text-sm">
        <span className="pmc-label">Quorum</span>
        <input type="number" min="1" value={comDraft.quorum}
          onChange={(e) => setComDraft({ ...comDraft, quorum: e.target.value })}
          className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
      </label>
      <label className="md:col-span-4 text-sm">
        <span className="pmc-label">Members (hold Ctrl/Cmd to multi-select) · shows designation</span>
        <select multiple value={comDraft.members}
          onChange={(e) => setComDraft({
            ...comDraft,
            members: Array.from(e.target.selectedOptions, (o) => o.value),
          })}
          className="mt-1 w-full px-3 py-2 border border-brand-navy/20 h-32"
          data-testid="committee-members">
          {staffList.map((a) => (
            <option key={a.id} value={a.id}>
              {a.email} — {a.designation || (a.roles || []).join(", ")}
            </option>
          ))}
        </select>
      </label>

      <div className="md:col-span-4 border-t border-brand-navy/10 pt-3">
        <div className="pmc-label">External invitees (optional — will receive email invite with tender & bid summary)</div>
        <div className="grid gap-2 md:grid-cols-4 mt-2">
          <input value={extDraft.name}
                 onChange={(e) => setExtDraft({ ...extDraft, name: e.target.value })}
                 placeholder="Full name" data-testid="ext-invite-name"
                 className="px-3 py-2 border border-brand-navy/20 text-sm" />
          <input value={extDraft.email}
                 onChange={(e) => setExtDraft({ ...extDraft, email: e.target.value })}
                 placeholder="Email" type="email" data-testid="ext-invite-email"
                 className="px-3 py-2 border border-brand-navy/20 text-sm" />
          <input value={extDraft.designation}
                 onChange={(e) => setExtDraft({ ...extDraft, designation: e.target.value })}
                 placeholder="Designation (e.g. Independent Engineer)"
                 data-testid="ext-invite-designation"
                 className="px-3 py-2 border border-brand-navy/20 text-sm" />
          <button type="button" onClick={addExtInvitee}
                  data-testid="ext-invite-add"
                  className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
            Add invitee
          </button>
        </div>
        {comDraft.external_invitees.length > 0 && (
          <ul className="mt-2 text-sm space-y-1" data-testid="ext-invitees-list">
            {comDraft.external_invitees.map((inv, i) => (
              <li key={`${inv.email}-${i}`} className="flex items-center gap-2">
                <span className="flex-1">
                  <strong>{inv.name}</strong> · {inv.email}
                  {inv.designation && <span className="text-brand-navy/60"> · {inv.designation}</span>}
                </span>
                <button type="button" onClick={() => removeExtInvitee(i)}
                        className="text-xs text-red-600 hover:underline">Remove</button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="md:col-span-4 flex justify-end">
        <button onClick={onSubmit} data-testid="committee-create-submit"
          className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
          Form committee
        </button>
      </div>
    </div>
  );
}
