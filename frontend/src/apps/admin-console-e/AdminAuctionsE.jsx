import { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { reverseAuctionApi, adminApi, showApiError } from "@/lib/api";
import AdminEShell from "./AdminEShell";
import MoneyFilterBar, { matchesMoneyFilter } from "@/components/MoneyFilterBar";

/**
 * v50m — Admin Reverse-Auctions tab (bug #39-41).
 * Lists every auction (draft / live / closed) with inline Start / Close
 * buttons that call the live backend; also provides a Create form bound
 * to a notice picker so new drafts actually appear in the list.
 */
export default function AdminAuctionsE() {
  const [rows, setRows] = useState([]);
  const [notices, setNotices] = useState([]);
  const [loading, setLoading] = useState(true);
  const [showNew, setShowNew] = useState(false);
  const [draft, setDraft] = useState({
    notice_ref: "", title: "", starting_price: 0, floor_price: 0,
    duration_minutes: 60, bid_decrement: 1000, currency: "USD",
  });
  const [busyId, setBusyId] = useState(null);
  // v51x — inline invite + participant panels per auction row.
  const [inviteFor, setInviteFor] = useState(null);   // auction id
  const [inviteEmails, setInviteEmails] = useState("");
  const [inviteNote, setInviteNote] = useState("");
  const [inviteBusy, setInviteBusy] = useState(false);
  const [autoSend, setAutoSend] = useState(true);     // v51z — email now via Resend
  const [partsFor, setPartsFor] = useState({});       // aid -> { count, items }
  // v51ab — client-side filter + inline edit for drafts.
  const [filter, setFilter] = useState({});
  const [editingAid, setEditingAid] = useState(null);
  const [editDraft, setEditDraft] = useState(null);
  const [editBusy, setEditBusy] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [a, n] = await Promise.all([
        reverseAuctionApi.list(),
        adminApi.listAllNotices({ limit: 500 }).catch(() => ({ items: [] })),
      ]);
      setRows(a.items || []);
      setNotices(n.items || []);
    } catch (e) { showApiError(e); }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const create = async () => {
    if (!draft.notice_ref) { toast.error("Pick a notice first."); return; }
    if (!draft.title.trim()) { toast.error("Give the auction a title."); return; }
    if (Number(draft.floor_price) >= Number(draft.starting_price)) {
      toast.error("Floor price must be lower than starting price."); return;
    }
    try {
      // v52by — bug #64: backend's Pydantic ReverseAuctionIn expects
      // `min_decrement`, not `bid_decrement`. Previous payload silently
      // failed with "field required" and the admin saw a cryptic 422.
      const r = await reverseAuctionApi.create({
        ...draft,
        starting_price: Number(draft.starting_price),
        floor_price: Number(draft.floor_price),
        duration_minutes: Number(draft.duration_minutes),
        min_decrement: Number(draft.bid_decrement) || 1,
      });
      toast.success(`Auction drafted · ${r.id} · Register ≥2 participants, then Start.`);
      setShowNew(false);
      setDraft({ notice_ref: "", title: "", starting_price: 0, floor_price: 0,
                 duration_minutes: 60, bid_decrement: 1000, currency: "USD" });
      // v52by — bug #59: optimistic prepend so admins see their new draft
      // without waiting for the refetch.
      setRows((cur) => [{ ...r, participant_count: 0 }, ...cur.filter((x) => x.id !== r.id)]);
      load();
    } catch (e) { showApiError(e); }
  };

  const start = async (aid) => {
    setBusyId(aid);
    try {
      await reverseAuctionApi.start(aid);
      toast.success("Auction is now LIVE.");
      load();
    } catch (e) { showApiError(e, { fallbackTitle: "Cannot start auction" }); }
    finally { setBusyId(null); }
  };
  const close = async (aid) => {
    setBusyId(aid);
    try {
      const res = await reverseAuctionApi.close(aid);
      toast.success(res.already_closed ? "Auction was already closed." : "Auction closed.");
      load();
    } catch (e) { showApiError(e, { fallbackTitle: "Cannot close auction" }); }
    finally { setBusyId(null); }
  };

  // v51ab — inline edit for draft auctions.
  const openEdit = (a) => {
    setEditingAid(a.id);
    setEditDraft({
      title: a.title || "",
      starting_price: a.starting_price,
      floor_price: a.floor_price,
      min_decrement: a.min_decrement,
      duration_minutes: a.duration_minutes || Math.round((a.anti_snipe_seconds || 0) / 60) || 60,
      currency: a.currency || "USD",
      anti_snipe_seconds: a.anti_snipe_seconds ?? 30,
      notice_ref: a.notice_ref,
    });
  };
  const cancelEdit = () => { setEditingAid(null); setEditDraft(null); };
  const saveEdit = async () => {
    if (!editingAid || !editDraft) return;
    const sp = Number(editDraft.starting_price || 0);
    const fp = Number(editDraft.floor_price || 0);
    if (sp <= 0) return toast.error("Starting price must be greater than 0");
    if (fp >= sp) return toast.error("Floor price must be lower than starting price");
    setEditBusy(true);
    try {
      await reverseAuctionApi.update(editingAid, {
        title: (editDraft.title || "").trim(),
        starting_price: sp, floor_price: fp,
        min_decrement: Number(editDraft.min_decrement || 0),
        duration_minutes: Number(editDraft.duration_minutes || 0),
        currency: editDraft.currency,
        anti_snipe_seconds: Number(editDraft.anti_snipe_seconds || 0),
        notice_ref: editDraft.notice_ref,
      });
      toast.success("Auction updated.");
      cancelEdit(); load();
    } catch (e) { showApiError(e, { fallbackTitle: "Cannot update auction" }); }
    finally { setEditBusy(false); }
  };

  const filteredRows = useMemo(() => (rows || []).filter((a) => matchesMoneyFilter({
    text: `${a.title || ""} ${a.notice_ref || ""} ${a.created_by || ""} ${a.updated_by || ""}`,
    created_at: a.created_at, expires_at: a.end_at,
    created_by: a.created_by || a.updated_by, status: a.status,
  }, filter)), [rows, filter]);

  // v51x — fetch current participants/invitations when the admin expands a
  // row. The Start button needs ≥2 participants; this surfaces the gap so
  // the admin can either invite more vendors or wait for pending accepts.
  const loadParticipants = async (aid) => {
    try {
      const [a, inv] = await Promise.all([
        reverseAuctionApi.get(aid),
        reverseAuctionApi.listInvitations(aid).catch(() => ({ items: [] })),
      ]);
      setPartsFor((prev) => ({
        ...prev,
        [aid]: {
          count: (a.participants || []).length,
          participants: a.participants || [],
          invitations: inv.items || inv || [],
        },
      }));
    } catch (e) { showApiError(e); }
  };

  const toggleInvite = (aid) => {
    if (inviteFor === aid) { setInviteFor(null); return; }
    setInviteFor(aid);
    setInviteEmails("");
    setInviteNote("");
    loadParticipants(aid);
  };

  const sendInvites = async (aid) => {
    const emails = inviteEmails.split(/[\s,;\n]+/).map((e) => e.trim()).filter((e) => e && e.includes("@"));
    if (emails.length === 0) { toast.error("Enter at least one vendor email."); return; }
    setInviteBusy(true);
    try {
      // v51z — pass auto_send so the backend emails each vendor via Resend
      // using the default (or built-in) invitation template.
      const r = await reverseAuctionApi.invite(aid, emails, inviteNote || null, {
        origin_url: window.location.origin,
        auto_send: autoSend,
      });
      const emailed = r.auto_sent || 0;
      toast.success(
        autoSend && emailed > 0
          ? `${r.count} invite${r.count === 1 ? "" : "s"} prepared · ${emailed} emailed via Resend.`
          : `${r.count} invite${r.count === 1 ? "" : "s"} prepared · share the links below.`
      );
      setInviteEmails("");
      await loadParticipants(aid);
    } catch (e) { showApiError(e, { fallbackTitle: "Cannot send invites" }); }
    finally { setInviteBusy(false); }
  };

  const pill = (s) => {
    const cls = { draft: "pmc-pill", live: "pmc-pill pmc-pill--success",
                  closed: "pmc-pill pmc-pill--info" }[s] || "pmc-pill";
    return <span className={cls} data-testid={`auction-status-${s}`}>{s}</span>;
  };

  return (
    <AdminEShell active="Reverse auctions"
                 crumb={<>Money &amp; compliance / <b>Reverse auctions</b></>}>
      <div className="p-6" data-testid="admin-auctions-e">
        <div className="flex items-center justify-between mb-4 gap-3 flex-wrap">
          <div>
            <h1 className="text-2xl font-serif">Reverse auctions</h1>
            <div className="text-sm text-brand-navy/60 mt-1">
              Live descending-price rounds. Draft → ≥2 participants registered → Start → bidders drive price down → Close.
            </div>
          </div>
          <button type="button" onClick={() => setShowNew((v) => !v)}
                  data-testid="admin-auction-new-toggle"
                  className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            {showNew ? "Cancel" : "New auction"}
          </button>
        </div>

        {showNew && (
          <div className="border border-brand-navy/20 bg-white p-5 grid gap-3 md:grid-cols-3 mb-5"
               data-testid="admin-auction-new-form">
            <label className="md:col-span-2"><span className="pmc-label">Notice</span>
              <select value={draft.notice_ref}
                      onChange={(e) => setDraft({ ...draft, notice_ref: e.target.value })}
                      data-testid="auction-notice-picker"
                      className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white text-brand-navy">
                <option value="">— pick a notice —</option>
                {notices.map((n) => (
                  <option key={n.id || n.notice_ref} value={n.notice_ref}>
                    {n.notice_ref} — {n.title}
                  </option>
                ))}
              </select>
            </label>
            <label><span className="pmc-label">Currency</span>
              <select value={draft.currency}
                      onChange={(e) => setDraft({ ...draft, currency: e.target.value })}
                      className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white text-brand-navy">
                {["USD","EUR","GBP","INR","KZT","AED"].map((c) => <option key={c}>{c}</option>)}
              </select>
            </label>
            <label className="md:col-span-3"><span className="pmc-label">Title</span>
              <input value={draft.title}
                     onChange={(e) => setDraft({ ...draft, title: e.target.value })}
                     placeholder="e.g. OPD Renovation — Round 1"
                     data-testid="auction-title-input"
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
            <label><span className="pmc-label">Starting price</span>
              <input type="number" value={draft.starting_price}
                     onChange={(e) => setDraft({ ...draft, starting_price: e.target.value })}
                     data-testid="auction-start-price"
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
            <label><span className="pmc-label">Floor price</span>
              <input type="number" value={draft.floor_price}
                     onChange={(e) => setDraft({ ...draft, floor_price: e.target.value })}
                     data-testid="auction-floor-price"
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
            <label><span className="pmc-label">Bid decrement</span>
              <input type="number" value={draft.bid_decrement}
                     onChange={(e) => setDraft({ ...draft, bid_decrement: e.target.value })}
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
            <label><span className="pmc-label">Duration (minutes)</span>
              <input type="number" value={draft.duration_minutes}
                     onChange={(e) => setDraft({ ...draft, duration_minutes: e.target.value })}
                     className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
            <div className="md:col-span-3 flex justify-end">
              <button onClick={create} data-testid="auction-create-btn"
                      className="px-6 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white hover:bg-brand-navy-soft/90">
                Create draft auction
              </button>
            </div>
          </div>
        )}

        <MoneyFilterBar
          testid="auction-filter"
          onChange={setFilter}
          presetScope="auctions"
          statusOptions={[
            { value: "draft", label: "Draft" },
            { value: "live",  label: "Live" },
            { value: "closed", label: "Closed" },
          ]}
        />

        {loading && <div className="p-6 text-sm text-brand-navy/50">Loading auctions…</div>}
        {!loading && rows.length === 0 && (
          <div className="p-8 text-sm text-brand-navy/50 bg-white border border-brand-navy/10 text-center"
               data-testid="admin-auction-empty">
            No reverse auctions yet. Click "New auction" to create your first one.
          </div>
        )}
        {!loading && rows.length > 0 && filteredRows.length === 0 && (
          <div className="p-8 text-sm text-brand-navy/50 bg-white border border-brand-navy/10 text-center"
               data-testid="admin-auction-empty-filtered">
            No reverse auctions match the current filters. Clear them to see all {rows.length}.
          </div>
        )}

        {!loading && filteredRows.length > 0 && (
          <div className="bg-white border border-brand-navy/10 divide-y divide-brand-navy/10"
               data-testid="admin-auction-list">
            {filteredRows.map((a) => {
              const part = partsFor[a.id];
              const expanded = inviteFor === a.id;
              return (
              <div key={a.id} className="p-4" data-testid={`auction-row-${a.id}`}>
                <div className="grid gap-3 md:grid-cols-[2fr_1fr_1fr_auto] items-center">
                  <div className="min-w-0">
                    <div className="font-semibold text-brand-navy">{a.title}</div>
                    <div className="text-xs text-brand-navy/60 font-mono">
                      {a.notice_ref} · created {a.created_at?.slice(0, 10)}
                    </div>
                  </div>
                  <div className="text-xs">
                    <div className="pmc-label">Start → Floor</div>
                    <div className="font-mono">
                      {a.currency} {Number(a.starting_price).toLocaleString()} →{" "}
                      {Number(a.floor_price).toLocaleString()}
                    </div>
                  </div>
                  <div className="flex items-center gap-2 flex-wrap">
                    {pill(a.status)}
                    {a.status === "draft" && typeof a.participant_count === "number" && (
                      <span
                        data-testid={`auction-readiness-${a.id}`}
                        title={a.participant_count >= 2
                          ? "Enough participants — ready to Start"
                          : `Needs at least 2 registered participants (currently ${a.participant_count})`}
                        className={`text-[10px] uppercase tracking-widest px-2 py-0.5 border ${
                          a.participant_count >= 2
                            ? "bg-emerald-50 border-emerald-300 text-emerald-800"
                            : "bg-amber-50 border-amber-300 text-amber-900"
                        }`}>
                        {a.participant_count >= 2
                          ? `✓ ${a.participant_count}/2 ready`
                          : `${a.participant_count}/2 participants`}
                      </span>
                    )}
                  </div>
                  <div className="flex gap-2 justify-end flex-wrap">
                    {a.status === "draft" && (
                      <button type="button" onClick={() => openEdit(a)}
                              data-testid={`auction-edit-${a.id}`}
                              className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy/5">
                        Edit
                      </button>
                    )}
                    {a.status !== "closed" && (
                      <button type="button" onClick={() => toggleInvite(a.id)}
                              data-testid={`auction-invite-toggle-${a.id}`}
                              className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/40 text-brand-navy hover:bg-brand-navy/5">
                        {expanded ? "Hide invites" : "Invite vendors"}
                      </button>
                    )}
                    {a.status === "draft" && (
                      <button type="button" onClick={() => start(a.id)}
                              disabled={busyId === a.id}
                              data-testid={`auction-start-${a.id}`}
                              data-ra-start-id={a.id}
                              title={(a.participant_count ?? 0) < 2 ? "Only 0-1 vendor is registered. Clicking Start will show the server's exact gate message." : "Start the auction"}
                              className="px-3 py-1.5 text-[11px] uppercase tracking-widest bg-emerald-700 text-white hover:bg-emerald-800 disabled:opacity-50">
                        {busyId === a.id ? "…" : `Start · ${a.participant_count ?? 0}/2`}
                      </button>
                    )}
                    {a.status === "live" && (
                      <button type="button" onClick={() => close(a.id)}
                              disabled={busyId === a.id}
                              data-testid={`auction-close-${a.id}`}
                              className="px-3 py-1.5 text-[11px] uppercase tracking-widest bg-red-700 text-white hover:bg-red-800 disabled:opacity-50">
                        {busyId === a.id ? "…" : "Close"}
                      </button>
                    )}
                    <a href={`/auctions/${a.id}/live`}
                       target="_blank" rel="noopener noreferrer"
                       data-testid={`auction-open-${a.id}`}
                       className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white">
                      Open room
                    </a>
                  </div>
                </div>
                {editingAid === a.id && editDraft && (
                  <div className="mt-3 border-t border-brand-navy/10 pt-3 grid gap-3 md:grid-cols-3"
                       data-testid={`auction-edit-panel-${a.id}`}>
                    <label className="md:col-span-2"><span className="pmc-label">Title</span>
                      <input value={editDraft.title}
                             onChange={(e) => setEditDraft({ ...editDraft, title: e.target.value })}
                             data-testid={`auction-edit-title-${a.id}`}
                             className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
                    <label><span className="pmc-label">Currency</span>
                      <select value={editDraft.currency}
                              onChange={(e) => setEditDraft({ ...editDraft, currency: e.target.value })}
                              data-testid={`auction-edit-currency-${a.id}`}
                              className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                        {["USD","EUR","GBP","INR","KZT","AED"].map((c) => <option key={c}>{c}</option>)}
                      </select></label>
                    <label><span className="pmc-label">Starting price</span>
                      <input type="number" value={editDraft.starting_price}
                             onChange={(e) => setEditDraft({ ...editDraft, starting_price: e.target.value })}
                             data-testid={`auction-edit-start-${a.id}`}
                             className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
                    <label><span className="pmc-label">Floor price</span>
                      <input type="number" value={editDraft.floor_price}
                             onChange={(e) => setEditDraft({ ...editDraft, floor_price: e.target.value })}
                             data-testid={`auction-edit-floor-${a.id}`}
                             className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
                    <label><span className="pmc-label">Min decrement</span>
                      <input type="number" value={editDraft.min_decrement}
                             onChange={(e) => setEditDraft({ ...editDraft, min_decrement: e.target.value })}
                             data-testid={`auction-edit-decrement-${a.id}`}
                             className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
                    <label><span className="pmc-label">Duration (min)</span>
                      <input type="number" value={editDraft.duration_minutes}
                             onChange={(e) => setEditDraft({ ...editDraft, duration_minutes: e.target.value })}
                             data-testid={`auction-edit-duration-${a.id}`}
                             className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
                    <label><span className="pmc-label">Anti-snipe (sec)</span>
                      <input type="number" value={editDraft.anti_snipe_seconds}
                             onChange={(e) => setEditDraft({ ...editDraft, anti_snipe_seconds: e.target.value })}
                             data-testid={`auction-edit-antisnipe-${a.id}`}
                             className="mt-1 w-full px-3 py-2 border border-brand-navy/20"/></label>
                    <div className="md:col-span-3 flex justify-end gap-2 flex-wrap">
                      <button type="button" onClick={cancelEdit} disabled={editBusy}
                              data-testid={`auction-edit-cancel-${a.id}`}
                              className="px-4 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy/80 hover:bg-brand-navy/5 disabled:opacity-40">
                        Cancel
                      </button>
                      <button type="button" onClick={saveEdit} disabled={editBusy}
                              data-testid={`auction-edit-save-${a.id}`}
                              className="px-5 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white disabled:opacity-40">
                        {editBusy ? "Saving…" : "Save changes"}
                      </button>
                    </div>
                  </div>
                )}
                {expanded && (
                  <div className="mt-3 border-t border-brand-navy/10 pt-3 grid gap-3 md:grid-cols-2"
                       data-testid={`auction-invite-panel-${a.id}`}>
                    <div>
                      <div className="pmc-label">Invite vendors by email</div>
                      <p className="text-xs text-brand-navy/60 mt-1 mb-2">
                        Paste one or more vendor emails (comma, space or newline separated).
                        Each gets a unique join link; auctions need ≥2 registered participants before Start.
                      </p>
                      <textarea rows={3} value={inviteEmails}
                                onChange={(e) => setInviteEmails(e.target.value)}
                                placeholder="vendor1@example.com, vendor2@example.com"
                                data-testid={`auction-invite-emails-${a.id}`}
                                className="w-full px-3 py-2 border border-brand-navy/20 text-sm font-mono"/>
                      <input value={inviteNote}
                             onChange={(e) => setInviteNote(e.target.value)}
                             placeholder="Optional note shown to vendor"
                             data-testid={`auction-invite-note-${a.id}`}
                             className="mt-2 w-full px-3 py-2 border border-brand-navy/20 text-sm"/>
                      <label className="mt-2 flex items-center gap-2 text-xs text-brand-navy/70 cursor-pointer">
                        <input type="checkbox" checked={autoSend}
                               onChange={(e) => setAutoSend(e.target.checked)}
                               data-testid={`auction-invite-autosend-${a.id}`} />
                        Email vendors now via Resend (unchecked = links only, no email)
                      </label>
                      <button type="button" onClick={() => sendInvites(a.id)}
                              disabled={inviteBusy}
                              data-testid={`auction-invite-send-${a.id}`}
                              className="mt-2 px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white disabled:opacity-50">
                        {inviteBusy ? "Preparing…" : (autoSend ? "Email invites now" : "Create invite links")}
                      </button>
                    </div>
                    <div>
                      <div className="pmc-label">
                        Registered participants {part ? `(${part.count})` : ""}
                      </div>
                      {!part && <div className="text-xs text-brand-navy/50 mt-2">Loading…</div>}
                      {part && part.participants.length === 0 && (
                        <div className="text-xs text-brand-navy/60 mt-2 italic">
                          No vendors have joined yet. Send them the invite links below.
                        </div>
                      )}
                      {part && part.participants.length > 0 && (
                        <ul className="mt-2 text-xs space-y-1" data-testid={`auction-participants-${a.id}`}>
                          {part.participants.map((p) => (
                            <li key={p.id || p.vendor_id} className="flex justify-between gap-2">
                              <span>{p.company_name || p.vendor_email}</span>
                              <span className="font-mono text-brand-navy/50">{p.alias}</span>
                            </li>
                          ))}
                        </ul>
                      )}
                      {part && part.invitations.length > 0 && (
                        <div className="mt-3">
                          <div className="pmc-label">Pending invite links</div>
                          <ul className="mt-1 text-[11px] font-mono space-y-1 max-h-40 overflow-y-auto"
                              data-testid={`auction-invite-pending-list-${a.id}`}>
                            {part.invitations.map((inv) => {
                              const url = `${window.location.origin}/vendor/auction/invite/${inv.token}`;
                              return (
                                <li key={inv.token}
                                    data-testid={`auction-invite-pending-${inv.token}`}
                                    className="flex justify-between gap-2 items-center">
                                  <span className="truncate">{inv.email}</span>
                                  <button type="button"
                                          onClick={() => { navigator.clipboard?.writeText(url); toast.success("Link copied"); }}
                                          className="text-brand-navy underline whitespace-nowrap">Copy link</button>
                                </li>
                              );
                            })}
                          </ul>
                        </div>
                      )}
                    </div>
                  </div>
                )}
              </div>
              );
            })}
          </div>
        )}
      </div>
    </AdminEShell>
  );
}
