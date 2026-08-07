import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { meetingsApi, formatApiError } from "@/lib/api";

/** Wave 41 — Admin meeting scheduler with Jitsi Meet embed. */
export default function MeetingsPanel() {
  const [items, setItems] = useState([]);
  const [notices, setNotices] = useState([]);
  const [showNew, setShowNew] = useState(false);
  const [showInvitees, setShowInvitees] = useState(null); // meeting.id
  const [draft, setDraft] = useState({
    subject: "", agenda: "", notice_ref: "",
    scheduled_at: "", duration_min: 45, provider: "jitsi",
    invitees_text: "",
  });

  const load = useCallback(() => {
    meetingsApi.list().then((d) => setItems(d.items || []))
      .catch((e) => toast.error(formatApiError(e)));
  }, []);

  useEffect(() => {
    load();
    fetch(`${process.env.REACT_APP_BACKEND_URL}/api/v1/notices?limit=200`)
      .then((r) => r.json()).then((d) => setNotices(d.items || []))
      .catch(() => {});
  }, [load]);

  const parseInvitees = () => {
    return draft.invitees_text.split("\n")
      .map((line) => line.trim()).filter(Boolean)
      .map((line) => {
        const [email, name, role] = line.split(",").map((s) => (s || "").trim());
        if (!email || !email.includes("@")) return null;
        return { email, name: name || undefined, role: role || "attendee" };
      })
      .filter(Boolean);
  };

  const create = async () => {
    if (!draft.subject) { toast.error("Subject required"); return; }
    if (!draft.scheduled_at) { toast.error("Scheduled time required"); return; }
    const invitees = parseInvitees();
    if (invitees.length === 0) { toast.error("Add at least one invitee"); return; }
    try {
      const payload = {
        subject: draft.subject,
        agenda: draft.agenda || undefined,
        notice_ref: draft.notice_ref || undefined,
        scheduled_at: new Date(draft.scheduled_at).toISOString(),
        duration_min: parseInt(draft.duration_min, 10),
        provider: draft.provider,
        invitees,
      };
      const res = await meetingsApi.create(payload);
      toast.success(`${draft.provider === "zoom" ? "Zoom" : "Jitsi"} meeting scheduled · ${invitees.length} invitees`);
      setShowInvitees(res.id);
      setShowNew(false);
      setDraft({ subject: "", agenda: "", notice_ref: "",
                 scheduled_at: "", duration_min: 45, provider: "jitsi", invitees_text: "" });
      load();
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const cancel = async (mid) => {
    if (!window.confirm("Cancel this meeting?")) return;
    try { await meetingsApi.cancel(mid); toast.success("Cancelled"); load(); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  const copyLink = (url) => {
    const full = `${window.location.origin}${url}`;
    navigator.clipboard?.writeText(full);
    toast.success("Invite link copied");
  };

  const badge = (s) => ({
    scheduled: "bg-emerald-100 text-emerald-800 border-emerald-300",
    live:      "bg-sky-100 text-sky-800 border-sky-300",
    ended:     "bg-slate-200 text-slate-700 border-slate-400",
    cancelled: "bg-red-100 text-red-700 border-red-300",
  }[s] || "bg-gray-100 text-gray-700 border-gray-300");

  return (
    <div data-testid="admin-meetings-panel">
      <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
        <div className="text-sm text-brand-navy/70">
          Schedule pre-bid meetings and evaluation calls · each invitee gets a magic-link that drops them into a private Jitsi video room · local recording available inside the room.
        </div>
        <button type="button" onClick={() => setShowNew(!showNew)} data-testid="mtg-new-toggle"
          className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          {showNew ? "Cancel" : "Schedule meeting"}
        </button>
      </div>

      {showNew && (
        <div className="border border-brand-navy-soft/40 bg-white p-6 mb-6 grid gap-4 md:grid-cols-2" data-testid="mtg-new-form">
          <label className="col-span-2"><span className="pmc-label">Subject</span>
            <input value={draft.subject} onChange={(e) => setDraft({ ...draft, subject: e.target.value })}
                   data-testid="mtg-subject"
                   placeholder="Pre-bid clarification meeting"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label className="col-span-2"><span className="pmc-label">Agenda</span>
            <textarea rows={3} value={draft.agenda} onChange={(e) => setDraft({ ...draft, agenda: e.target.value })}
                      data-testid="mtg-agenda"
                      className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Notice (optional)</span>
            <select value={draft.notice_ref} onChange={(e) => setDraft({ ...draft, notice_ref: e.target.value })}
                    className="mt-1 w-full px-4 py-3 border border-brand-navy/20">
              <option value="">— none —</option>
              {notices.map((n) => (
                <option key={n.id} value={n.notice_ref}>{n.notice_ref} — {n.title}</option>
              ))}
            </select></label>
          <label><span className="pmc-label">Scheduled at</span>
            <input type="datetime-local" value={draft.scheduled_at}
                   onChange={(e) => setDraft({ ...draft, scheduled_at: e.target.value })}
                   data-testid="mtg-when"
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label><span className="pmc-label">Duration (min)</span>
            <input type="number" value={draft.duration_min}
                   onChange={(e) => setDraft({ ...draft, duration_min: e.target.value })}
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20" /></label>
          <label className="col-span-2"><span className="pmc-label">Video provider</span>
            <div className="mt-1 grid grid-cols-2 gap-2">
              <button type="button" onClick={() => setDraft({ ...draft, provider: "jitsi" })}
                      data-testid="mtg-provider-jitsi"
                      className={`px-4 py-3 border ${draft.provider === "jitsi" ? "bg-brand-navy text-white border-brand-navy" : "border-brand-navy/20 text-brand-navy"}`}>
                Jitsi Meet · free · unlimited · local recording
              </button>
              <button type="button" onClick={() => setDraft({ ...draft, provider: "zoom" })}
                      data-testid="mtg-provider-zoom"
                      className={`px-4 py-3 border ${draft.provider === "zoom" ? "bg-brand-navy text-white border-brand-navy" : "border-brand-navy/20 text-brand-navy"}`}>
                Zoom · your Basic account · 40-min cap on 3+ ppl
              </button>
            </div>
          </label>
          <label className="col-span-2"><span className="pmc-label">
            Invitees — one per line, format: <span className="font-mono">email, name (optional), role (bidder/staff/observer/attendee)</span>
          </span>
            <textarea rows={5} value={draft.invitees_text}
                      onChange={(e) => setDraft({ ...draft, invitees_text: e.target.value })}
                      data-testid="mtg-invitees"
                      placeholder={"bidder1@company.com, Acme Ltd, bidder\nreviewer@pmc.com, Alice, staff"}
                      className="mt-1 w-full px-4 py-3 border border-brand-navy/20 font-mono text-sm" /></label>
          <div className="col-span-2 flex justify-end">
            <button type="button" onClick={create} data-testid="mtg-create"
              className="px-8 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
              Create meeting
            </button>
          </div>
        </div>
      )}

      <div className="border border-brand-navy/10 bg-white">
        {items.length === 0 && <div className="p-6 text-brand-navy/50 text-sm">No meetings scheduled yet.</div>}
        {items.map((m) => (
          <div key={m.id} className="p-4 border-b border-brand-navy/10" data-testid={`mtg-row-${m.id}`}>
            <div className="flex items-baseline gap-4 flex-wrap">
              <span className={`text-[10px] uppercase tracking-widest px-2 py-1 border ${badge(m.status)}`}>{m.status}</span>
              <span className={`text-[10px] uppercase tracking-widest px-2 py-1 border ${m.provider === "zoom" ? "border-sky-400 text-sky-700 bg-sky-50" : "border-emerald-400 text-emerald-700 bg-emerald-50"}`}>
                {m.provider || "jitsi"}
              </span>
              <span className="text-sm font-semibold text-brand-navy flex-1">{m.subject}</span>
              {m.notice_ref && <span className="font-mono text-xs text-brand-navy-soft">{m.notice_ref}</span>}
              <span className="text-xs text-brand-navy/60 font-mono">{m.scheduled_at?.slice(0, 16).replace("T", " ")} · {m.duration_min}min</span>
              <span className="text-xs text-brand-navy/60">{(m.invitees || []).length} invitees</span>
              <button type="button" onClick={() => setShowInvitees(showInvitees === m.id ? null : m.id)}
                      data-testid={`mtg-invitees-${m.id}`}
                      className="text-[10px] uppercase tracking-widest px-3 py-1 border border-brand-navy/30 hover:bg-brand-navy hover:text-white">
                {showInvitees === m.id ? "Hide" : "Invite links"}
              </button>
              {m.status !== "cancelled" && m.status !== "ended" && (
                <button type="button" onClick={() => cancel(m.id)}
                        className="text-[10px] uppercase tracking-widest px-2 py-1 border border-red-300 text-red-700 hover:bg-red-50">
                  Cancel
                </button>
              )}
            </div>
            {showInvitees === m.id && <InviteeLinks mid={m.id} onCopy={copyLink} />}
          </div>
        ))}
      </div>
    </div>
  );
}

function InviteeLinks({ mid, onCopy }) {
  const [details, setDetails] = useState(null);
  useEffect(() => {
    meetingsApi.get(mid).then(setDetails).catch(() => {});
  }, [mid]);
  if (!details) return <div className="mt-3 text-sm text-brand-navy/50">Loading invite links…</div>;
  return (
    <div className="mt-3 bg-brand-pale border border-brand-navy/10 p-4">
      <div className="pmc-label">Magic-link invite URLs</div>
      <div className="mt-2 space-y-2">
        {(details.invite_links || []).map((l) => (
          <div key={l.email} className="flex items-center gap-3 text-xs">
            <span className="w-56 truncate">{l.name} · <span className="text-brand-navy/60">{l.email}</span></span>
            <span className="text-[10px] uppercase tracking-widest text-brand-navy/50">{l.role}</span>
            <input readOnly value={`${window.location.origin}${l.url}`}
                   className="flex-1 px-2 py-1 border border-brand-navy/15 font-mono text-[11px] bg-white" />
            <button type="button" onClick={() => onCopy(l.url)}
                    className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/30 hover:bg-brand-navy hover:text-white">
              Copy
            </button>
            {l.joined_at && <span className="text-[10px] text-emerald-700">joined</span>}
          </div>
        ))}
      </div>
    </div>
  );
}
