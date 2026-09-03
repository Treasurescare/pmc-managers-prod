import { toast } from "sonner";

/**
 * CommitteeForm v2 — Bucket B UX overhaul.
 *
 *  * Members: replaces Ctrl/Cmd multi-select with a clear checkbox grid.
 *  * Chair : dropdown auto-filtered to CURRENTLY-selected members only.
 *  * Quorum: capped by number of members with live inline hint.
 *
 * Contract with parent is unchanged so BiddingOpsPanel doesn't need to move.
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

  const toggleMember = (id, on) => {
    const set = new Set(comDraft.members);
    if (on) set.add(id); else set.delete(id);
    const next = Array.from(set);
    // Auto-clear chair if it's no longer among selected members.
    const nextChair = next.includes(comDraft.chair) ? comDraft.chair : "";
    // Cap quorum to member count.
    const q = Math.max(1, Math.min(parseInt(comDraft.quorum, 10) || 1, next.length || 1));
    setComDraft({ ...comDraft, members: next, chair: nextChair, quorum: q });
  };

  // Chair dropdown = intersection(selected members, admin pool).
  const chairPool = admins.filter((a) => comDraft.members.includes(a.id));

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
        <span className="pmc-label">Chairperson (from selected members)</span>
        <select value={comDraft.chair} disabled={chairPool.length === 0}
          onChange={(e) => setComDraft({ ...comDraft, chair: e.target.value })}
          className="mt-1 w-full px-3 py-2 border border-brand-navy/20 disabled:bg-brand-navy/5"
          data-testid="committee-chair">
          <option value="">{chairPool.length ? "Select…" : "Tick members below first"}</option>
          {chairPool.map((a) => <option key={a.id} value={a.id}>{a.email}</option>)}
        </select>
      </label>
      <label className="text-sm">
        <span className="pmc-label">Quorum (≤ {comDraft.members.length || 1})</span>
        <input type="number" min="1" max={comDraft.members.length || 1} value={comDraft.quorum}
          onChange={(e) => setComDraft({ ...comDraft, quorum: e.target.value })}
          data-testid="committee-quorum"
          className="mt-1 w-full px-3 py-2 border border-brand-navy/20" />
      </label>

      <div className="md:col-span-4">
        <div className="pmc-label mb-2">
          Members ({comDraft.members.length} selected) · tick to include
        </div>
        <div className="grid gap-1 md:grid-cols-2 max-h-64 overflow-y-auto border border-brand-navy/10 p-3"
             data-testid="committee-members-grid">
          {staffList.map((a) => {
            const on = comDraft.members.includes(a.id);
            return (
              <label key={a.id} data-testid={`committee-member-row-${a.id}`}
                className={`flex items-start gap-2 p-1.5 text-xs border ${on ? "border-brand-navy bg-brand-navy/5" : "border-transparent hover:bg-brand-navy/5"}`}>
                <input type="checkbox" checked={on}
                  onChange={(e) => toggleMember(a.id, e.target.checked)}
                  data-testid={`committee-member-check-${a.id}`}
                  className="mt-1"/>
                <span className="flex-1 min-w-0">
                  <span className="font-semibold text-brand-navy">{a.email}</span>
                  <span className="block text-brand-navy/60">
                    {a.designation || (a.roles || []).join(", ") || "—"}
                  </span>
                </span>
              </label>
            );
          })}
        </div>
      </div>

      <div className="md:col-span-4 border-t border-brand-navy/10 pt-3">
        <div className="pmc-label">External invitees (optional — will receive email invite with tender &amp; bid summary)</div>
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
          disabled={!comDraft.chair || comDraft.members.length === 0}
          className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90 disabled:opacity-40 disabled:cursor-not-allowed">
          Form committee
        </button>
      </div>
    </div>
  );
}
