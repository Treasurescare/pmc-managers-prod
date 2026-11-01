import { useEffect, useState } from "react";
import { Link, useParams } from "react-router-dom";
import { bidApi, formatApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";

const RES = { pass: ["Met", "text-emerald-800 bg-emerald-50"], fail: ["Not met", "text-red-800 bg-red-50"] };
const money = (c, v) => (v === null || v === undefined ? "—" : `${c || ""} ${Number(v).toLocaleString(undefined, { maximumFractionDigits: 2 })}`);

const RankBox = ({ d }) => (
  <div className="grid grid-cols-1 md:grid-cols-3 gap-3" data-testid="debrief-rank">
    {[["Your ranking", d.rank ? `L${d.rank.position} of ${d.rank.of}` : "Not ranked"], ["Your price", d.rank ? money(d.rank.currency, d.rank.your_price) : "Not opened"],
      ["Awarded price", d.awarded_price != null ? money(d.currency, d.awarded_price) : "—"]].map(([k, v], i) => (
      <div key={k} className="border border-brand-navy/15 p-4 bg-white"><div className="text-[11px] uppercase tracking-widest text-brand-navy/60">{k}</div>
        <div className="text-2xl font-serif mt-1" data-testid={["debrief-ranking", "debrief-your-price", "debrief-awarded-price"][i]}>{v}</div></div>))}
  </div>);

const CriteriaTable = ({ rows }) => (
  <table className="w-full text-sm bg-white border border-brand-navy/15" data-testid="debrief-criteria">
    <thead><tr className="text-left text-[11px] uppercase tracking-widest text-brand-navy/60"><th className="p-2">Criterion</th><th>Your answer</th><th>Result</th><th>Proof review</th></tr></thead>
    <tbody>{rows.map((c, i) => {
      const [lab, cls] = RES[c.result] || [c.kind === "scored" ? `${c.points ?? 0} pts` : "—", "text-brand-navy"];
      const pr = c.proof_review;
      return (
        <tr key={i} className="border-t border-brand-navy/10 align-top" data-testid={`debrief-crit-${i}`}>
          <td className="p-2"><b>{c.title}</b><div className="text-[11px] text-brand-navy/60">{c.mandatory ? "Mandatory" : "Optional"} · {c.rule}</div></td>
          <td className="p-2">{String(c.declared ?? "—")} {c.unit || ""}</td>
          <td className="p-2"><span className={`px-2 py-0.5 text-xs ${cls}`}>{lab}</span>{c.reason && <div className="text-[11px] mt-1">{c.reason}</div>}</td>
          <td className="p-2 text-xs">{!pr ? "—" : pr.status === "accepted" ? "Accepted by the committee" : pr.status === "rejected"
            ? <>Rejected{pr.rejected_comments.map((m, j) => <div key={j} className="text-red-800">“{m}”</div>)}</> : "Not reviewed (bid already decided)"}</td>
        </tr>);
    })}</tbody>
  </table>);

export default function VendorBidDebriefE() {
  const { bidId } = useParams();
  const [d, setD] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => { bidApi.debrief(bidId).then(setD).catch((e) => setErr(formatApiError(e))); }, [bidId]);
  return (
    <VendorPortalChrome active="/vendor/mybids">
      <div className="max-w-5xl space-y-5 p-1" data-testid="debrief-page">
        <Link to="/vendor/mybids" className="text-sm underline" data-testid="debrief-back">← Back to my bids</Link>
        {err && <div className="border border-amber-300 bg-amber-50 p-3 text-sm" data-testid="debrief-error">{err}</div>}
        {!d && !err && <div className="text-sm">Loading…</div>}
        {d && <>
          <div><div className="text-[11px] uppercase tracking-widest text-brand-gold">Bid debrief · {d.bid_ref}</div>
            <h1 className="font-serif text-3xl text-brand-navy">{d.notice_title || d.notice_ref}</h1>
            <div className="text-xs text-brand-navy/60 font-mono">{d.notice_ref} · winner picked by {d.award_method === "weighted" ? "weighted marks" : "lowest compliant price (L1)"}</div></div>
          <div className="border-l-4 border-brand-gold bg-white p-4 text-sm [&_ul]:list-disc [&_ul]:pl-5" data-testid="debrief-summary" dangerouslySetInnerHTML={{ __html: d.summary_html }} />
          {d.optional_summary && d.qualification_status !== "not_qualified" && <div className="text-sm" data-testid="debrief-optional">Optional criteria met: <b>{d.optional_summary.passed} of {d.optional_summary.total}</b> (at least {d.optional_summary.required} required)</div>}
          <RankBox d={d} />
          {d.criteria.length > 0 && <CriteriaTable rows={d.criteria} />}
          {d.emd_refund_due_at && <div className="text-sm" data-testid="debrief-emd">Your EMD will be refunded by <b>{d.emd_refund_due_at.slice(0, 10)}</b>.</div>}
          <p className="text-xs text-brand-navy/60">Questions about this decision? Use Messages within 5 days of the result to raise a clarification or complaint.</p>
        </>}
      </div>
    </VendorPortalChrome>);
}
