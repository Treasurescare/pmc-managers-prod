import { useEffect, useState } from "react";
import { criteriaApi } from "@/lib/api";

const WORD = { qualified: "Qualified", not_qualified: "Not qualified", doubt_raised: "Under committee review", disqualified: "Disqualified by the committee" };

export default function CriteriaResultNotices() {
  const [items, setItems] = useState([]);
  useEffect(() => { criteriaApi.myResults().then((r) => setItems(r.items || [])).catch(() => {}); }, []);
  if (!items.length) return null;
  return (
    <div className="space-y-3" style={{ marginBottom: 16 }} data-testid="vmb-criteria-results">
      <div className="pmc-eyebrow">Criteria results</div>
      {items.map((it) => {
        const n = it.notice;
        return (
          <details key={it.bid_id} className="border bg-white p-3" data-testid={`vmb-result-${it.bid_id}`}>
            <summary className="cursor-pointer text-sm">
              <b>{it.bid_ref}</b> · {it.notice_ref}{it.consortium ? ` · consortium ${it.consortium}` : ""} — <b data-testid={`vmb-result-status-${it.bid_id}`}>{WORD[n.status] || n.status}</b>
              <span className="text-xs text-slate-500"> ({n.kind === "final" ? "final" : "preliminary"} · {n.qualified_count} of {n.bids_total} bids qualified)</span>
            </summary>
            {n.kind !== "final" && <p className="text-xs text-slate-600 mt-2">First result from the system. The committee may still review documents; the final result comes before price opening.</p>}
            {n.status === "disqualified" && n.decision_note && <p className="text-xs mt-2"><b>Committee note:</b> {n.decision_note}</p>}
            <table className="w-full text-xs mt-2"><tbody>
              {n.results.map((r) => (
                <tr key={r.title} className="border-t align-top"><td className="py-1 pr-2">{r.title}</td>
                  <td className={`py-1 pr-2 font-semibold ${r.outcome === "Failed" ? "text-red-700" : r.outcome === "Passed" ? "text-emerald-800" : ""}`}>{r.outcome}</td>
                  <td className="py-1">{r.reason || ""}</td></tr>))}
            </tbody></table>
          </details>);
      })}
    </div>);
}
