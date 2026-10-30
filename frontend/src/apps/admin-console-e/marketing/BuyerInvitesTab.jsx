import { useEffect, useState } from "react";
import { toast } from "sonner";
import { marketingApi, showApiError } from "@/lib/api";

const inp = "px-3 py-2 border border-brand-navy/20 bg-white text-sm w-full";
const EMPTY = { organisation: "", contact_name: "", email: "", country: "", note: "" };
const TONE = { joined: "bg-emerald-700 text-white", clicked: "bg-amber-500 text-white", sent: "bg-brand-navy/10", failed: "bg-red-700 text-white" };

export const BuyerInvitesTab = () => {
  const [rows, setRows] = useState([]);
  const [f, setF] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const load = () => marketingApi.buyerInvites().then((r) => setRows(r.items || [])).catch(showApiError);
  useEffect(() => { load(); }, []);
  const send = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await marketingApi.sendBuyerInvite(f);
      r.email_sent ? toast.success(`Invite sent to ${f.email}`) : toast.error("Saved, but the email could not be sent");
      setF(EMPTY); load();
    } catch (err) { showApiError(err); } finally { setBusy(false); }
  };
  const joined = async (id) => { try { await marketingApi.markBuyerJoined(id); load(); } catch (e) { showApiError(e); } };
  const count = (s) => rows.filter((r) => r.status === s).length;
  return (
    <div className="grid gap-6 lg:grid-cols-[1fr_1.4fr]" data-testid="mkt-buyer-invites">
      <form onSubmit={send} className="border border-brand-navy/20 bg-white p-4 space-y-3">
        <div className="pmc-label">Invite a buyer to post tenders free</div>
        <input className={inp} required placeholder="Organisation, e.g. Almaty City Health Dept" value={f.organisation} onChange={(e) => setF({ ...f, organisation: e.target.value })} data-testid="bi-org" />
        <input className={inp} placeholder="Contact name (optional)" value={f.contact_name} onChange={(e) => setF({ ...f, contact_name: e.target.value })} data-testid="bi-name" />
        <input className={inp} required type="email" placeholder="Their work email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="bi-email" />
        <input className={inp} maxLength={2} placeholder="Country code (optional), e.g. KZ" value={f.country} onChange={(e) => setF({ ...f, country: e.target.value.toUpperCase() })} data-testid="bi-country" />
        <textarea className={inp} rows={5} placeholder="Personal note (optional) — leave empty for the standard invitation" value={f.note} onChange={(e) => setF({ ...f, note: e.target.value })} data-testid="bi-note" />
        <button className="pmc-btn pmc-btn--primary" disabled={busy} data-testid="bi-send">{busy ? "Sending…" : "Send invite"}</button>
        <div className="text-xs text-brand-navy/60">Send to one named person at a time. "Joined" turns on automatically once they have a buyer or staff account with that email.</div>
      </form>
      <div className="space-y-3">
        <div className="flex gap-4 text-sm" data-testid="bi-summary">
          <span>{rows.length} invited</span><span>{count("clicked")} clicked</span><span className="font-semibold">{count("joined")} joined</span>
        </div>
        <div className="border border-brand-navy/15 bg-white overflow-x-auto">
          <table className="w-full text-sm">
            <thead><tr className="text-left text-xs uppercase tracking-widest text-brand-navy/60">{["Organisation", "Contact", "Sent", "Status", ""].map((x) => <th key={x} className="p-2">{x}</th>)}</tr></thead>
            <tbody>{rows.map((r) => (
              <tr key={r.id} className="border-t border-brand-navy/10" data-testid={`bi-row-${r.id}`}>
                <td className="p-2 font-semibold">{r.organisation}{r.country ? ` · ${r.country}` : ""}</td>
                <td className="p-2">{r.contact_name || "—"}<div className="text-xs text-brand-navy/60">{r.email}</div></td>
                <td className="p-2">{r.created_at?.slice(0, 10)}</td>
                <td className="p-2"><span className={"px-2 py-0.5 text-xs uppercase " + (TONE[r.status] || "")} data-testid={`bi-status-${r.id}`}>{r.status}</span></td>
                <td className="p-2">{r.status !== "joined" && <button className="text-xs underline" onClick={() => joined(r.id)} data-testid={`bi-joined-${r.id}`}>Mark joined</button>}</td>
              </tr>))}
              {!rows.length && <tr><td colSpan={5} className="p-6 text-center text-brand-navy/60">No invites yet.</td></tr>}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
