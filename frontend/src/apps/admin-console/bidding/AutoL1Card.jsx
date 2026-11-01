import { useEffect, useState } from "react";
import { comparisonApi } from "@/lib/api";

export const AutoL1Card = ({ noticeRef, openedAt }) => {
  const [d, setD] = useState(null);
  useEffect(() => { comparisonApi.latestL1(noticeRef).then(setD).catch(() => setD(null)); }, [noticeRef, openedAt]);
  const r = d?.result;
  if (!r) return null;
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
    </div>);
};
