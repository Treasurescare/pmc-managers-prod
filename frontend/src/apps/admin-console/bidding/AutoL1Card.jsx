import { useEffect, useState } from "react";
import { toast } from "sonner";
import { comparisonApi, showApiError } from "@/lib/api";

const AwardL1 = ({ noticeRef, win, onDone }) => {
  const [open, setOpen] = useState(false);
  const [notes, setNotes] = useState("");
  const [busy, setBusy] = useState(false);
  const go = () => { setBusy(true); comparisonApi.awardL1(noticeRef, { notes: notes || null }).then((x) => { toast.success(`Awarded to ${x.company_name} (${x.awarded})`); setOpen(false); onDone(); }).catch(showApiError).finally(() => setBusy(false)); };
  if (!open) return <button type="button" className="pmc-btn pmc-btn--primary" onClick={() => setOpen(true)} data-testid={`award-l1-btn-${noticeRef}`}>Award to L1</button>;
  return (
    <div className="border border-emerald-300 bg-emerald-50 p-3 space-y-2 text-sm" data-testid={`award-l1-confirm-${noticeRef}`}>
      <div>Award <b>{noticeRef}</b> to <b>{win.company_name}</b> ({win.bid_ref}) at <b>{win.price_currency} {win.price_amount?.toLocaleString()}</b>? This is your committee sign-off and is recorded in the audit trail.</div>
      <input className="w-full px-2 py-1 border border-brand-navy/20 text-xs" placeholder="Note for the award record (optional)" value={notes} onChange={(e) => setNotes(e.target.value)} data-testid={`award-l1-notes-${noticeRef}`} />
      <div className="flex gap-2"><button type="button" className="pmc-btn pmc-btn--primary" disabled={busy} onClick={go} data-testid={`award-l1-confirm-btn-${noticeRef}`}>{busy ? "Awarding…" : "Confirm award"}</button>
        <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => setOpen(false)} data-testid={`award-l1-cancel-${noticeRef}`}>Cancel</button></div>
    </div>);
};

export const AutoL1Card = ({ noticeRef, openedAt }) => {
  const [d, setD] = useState(null);
  const [tick, setTick] = useState(0);
  useEffect(() => { comparisonApi.latestL1(noticeRef).then(setD).catch(() => setD(null)); }, [noticeRef, openedAt, tick]);
  const r = d?.result;
  if (!r) return null;
  const awarded = (r.ranked || []).find((x) => x.status === "awarded");
  return (
    <div className="border border-brand-navy/15 bg-white p-3 space-y-2" data-testid={`auto-l1-${noticeRef}`}>
      <div className="pmc-label">Automatic ranking after price opening {d.run_at ? `\u00b7 ${d.run_at.slice(0, 16).replace("T", " ")} UTC` : ""}</div>
      {r.award_method === "weighted" && <div className="text-xs bg-amber-50 border border-amber-300 p-2">This tender picks the winner by weighted marks \u2014 use the Award recommendation report; this L1 list is for reference.</div>}
      {!r.ranked?.length ? <div className="text-xs text-brand-navy/60">No qualified bid with a price to rank.</div> : (
        <table className="w-full text-xs"><tbody>
          {r.ranked.map((x) => (
            <tr key={x.bid_id} className="border-t border-brand-navy/10" data-testid={`auto-l1-row-${x.rank}`}>
              <td className="py-1 font-mono font-bold">L{x.rank}</td><td>{x.company_name}</td><td className="font-mono">{x.bid_ref}</td>
              <td className="text-right font-mono">{x.price_currency} {x.price_amount?.toLocaleString()}</td>
              <td className="text-right">{x.compliant ? "compliant" : x.compliance_flags.join(", ")}</td>
            </tr>))}
        </tbody></table>)}
      <div className="text-[11px] text-brand-navy/60">Only bids that passed the criteria and proof review are ranked. The committee still scores (if needed) and awards.</div>
      {awarded ? <div className="text-sm text-emerald-800" data-testid={`award-l1-done-${noticeRef}`}>Awarded to <b>{awarded.company_name}</b> ({awarded.bid_ref}).</div>
        : r.award_method !== "weighted" && r.l1_winner && <AwardL1 noticeRef={noticeRef} win={r.l1_winner} onDone={() => setTick((t) => t + 1)} />}
    </div>);
};
