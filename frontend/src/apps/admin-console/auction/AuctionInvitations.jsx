import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { reverseAuctionApi, showApiError } from "@/lib/api";

/**
 * v46b — Auction invitations widget. Renders inline on each auction row
 * in LiveAuctionsPanel. Admin pastes/types emails, clicks Invite, gets
 * back per-email invitation URLs to share via any channel.
 */
export default function AuctionInvitations({ auctionId }) {
  const [open, setOpen]           = useState(false);
  const [rows, setRows]           = useState([]);
  const [emails, setEmails]       = useState("");
  const [note, setNote]           = useState("");
  const [busy, setBusy]           = useState(false);

  const load = useCallback(async () => {
    try {
      const r = await reverseAuctionApi.listInvitations(auctionId);
      setRows(r.items || []);
    } catch (e) { showApiError(e); }
  }, [auctionId]);

  useEffect(() => { if (open) load(); }, [open, load]);

  const parseEmails = () => emails
    .split(/[\s,;\n]+/g).map((s) => s.trim())
    .filter((s) => s && s.includes("@"));

  const invite = async () => {
    const list = parseEmails();
    if (list.length === 0) {
      toast.error("Enter at least one valid email");
      return;
    }
    setBusy(true);
    try {
      const r = await reverseAuctionApi.invite(auctionId, list, note.trim() || null);
      toast.success(`Invited ${r.count} vendor${r.count === 1 ? "" : "s"}`);
      setEmails("");
      setNote("");
      await load();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const inviteUrl = (token) =>
    `${window.location.origin}/vendor/auction/invite/${token}`;

  const copy = async (token) => {
    try {
      await navigator.clipboard.writeText(inviteUrl(token));
      toast.success("Invitation URL copied");
    } catch {
      toast.error("Copy failed — long-press to select and copy manually");
    }
  };

  return (
    <div className="mt-3 border-t border-brand-navy/10 pt-3"
         data-testid={`invitations-${auctionId}`}>
      <button type="button" onClick={() => setOpen(!open)}
              data-testid={`ai-toggle-${auctionId}`}
              className="text-[10px] uppercase tracking-widest text-brand-navy-soft hover:underline">
        {open ? "Hide invitations" : `Invitations${rows.length ? ` (${rows.length})` : ""}`}
      </button>

      {open && (
        <div className="mt-3 grid gap-3 md:grid-cols-2">
          {/* Left: invite form */}
          <div className="border border-brand-navy/10 p-3 bg-brand-pale">
            <div className="pmc-label mb-2">Invite bidders</div>
            <textarea value={emails} onChange={(e) => setEmails(e.target.value)}
                      placeholder="one@example.com, two@example.com&#10;or one per line"
                      rows={4}
                      data-testid={`ai-emails-${auctionId}`}
                      className="w-full px-3 py-2 border text-xs font-mono" />
            <input value={note} onChange={(e) => setNote(e.target.value)}
                   placeholder="Optional note (round-2, best-and-final, ...)"
                   data-testid={`ai-note-${auctionId}`}
                   className="mt-2 w-full px-3 py-2 border text-xs" />
            <button type="button" onClick={invite} disabled={busy}
                    data-testid={`ai-send-${auctionId}`}
                    className="mt-2 w-full px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
              {busy ? "Sending…" : "Generate invitations"}
            </button>
            <div className="text-[10px] text-brand-navy/50 mt-2 leading-relaxed">
              Emails are matched to registered vendors when they sign in.
              Invitees automatically join the auction on accept — no manual
              registration needed.
            </div>
          </div>

          {/* Right: existing invitations */}
          <div className="border border-brand-navy/10 bg-white text-xs">
            <div className="pmc-label p-2 border-b flex justify-between">
              <span>Sent invitations</span>
              <span className="text-brand-navy/50">{rows.length}</span>
            </div>
            <div className="max-h-64 overflow-y-auto">
              {rows.length === 0 && (
                <div className="p-3 text-brand-navy/50">No invitations yet.</div>
              )}
              {rows.map((r) => (
                <div key={r.id} className="p-2 border-b flex items-center gap-2"
                     data-testid={`ai-row-${r.id}`}>
                  <div className="flex-1 min-w-0">
                    <div className="truncate font-mono">{r.email}</div>
                    <div className="text-[10px] text-brand-navy/50 flex gap-2">
                      {r.vendor_ref && <span>{r.vendor_ref}</span>}
                      {r.note && <span>· {r.note}</span>}
                      {r.resent_at && <span>· resent {r.resent_at.slice(0, 10)}</span>}
                    </div>
                  </div>
                  <span className={`text-[9px] uppercase tracking-widest px-2 py-0.5 ${r.joined ? "bg-emerald-100 text-emerald-800" : r.status === "accepted" ? "bg-blue-100 text-blue-800" : "bg-amber-100 text-amber-800"}`}>
                    {r.joined ? "joined" : r.status}
                  </span>
                  <button type="button" onClick={() => copy(r.token)}
                          data-testid={`ai-copy-${r.id}`}
                          className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 hover:bg-brand-navy hover:text-white">
                    Copy link
                  </button>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
