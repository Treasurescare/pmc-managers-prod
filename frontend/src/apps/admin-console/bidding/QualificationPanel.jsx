import { Fragment, useEffect, useState } from "react";
import { toast } from "sonner";
import { criteriaApi, showApiError } from "@/lib/api";
import { ProofReview } from "./ProofReview";

const BADGE = {
  qualified: ["Qualified", "bg-emerald-100 text-emerald-900"],
  not_qualified: ["Not qualified", "bg-red-100 text-red-900"],
  disqualified: ["Disqualified by committee", "bg-red-200 text-red-900"],
  doubt_raised: ["Doubt raised — committee to decide", "bg-amber-100 text-amber-900"],
};
const RES = { pass: "Pass", fail: "Fail", points: "Points", pending: "To be marked", scored_by_evaluators: "Marked" };

const ResultRow = ({ r, act, open }) => (
  <tr className="border-t border-brand-navy/10 align-top">
    <td className="py-1 pr-2">{r.title}<div className="text-[10px] text-brand-navy/50">{r.kind === "must_pass" ? "must pass" : "scored"} · rule {r.rule}</div></td>
    <td className="py-1 pr-2">{r.value === true ? "Yes" : r.value === false ? "No" : typeof r.value === "number" ? r.value.toLocaleString() : r.value ?? "—"} {r.unit || ""}{r.applies_to && <div className="text-[10px] text-brand-navy/60">applies to {r.applies_to}</div>}{(r.member_values || []).map((m) => <div key={m.member} className="text-[10px]">{m.member}: {m.value === true ? "Yes" : m.value === false ? "No" : typeof m.value === "number" ? m.value.toLocaleString() : m.value ?? "—"}</div>)}<div className="text-[10px]">{r.proof_supplied ? "proof supplied" : "no proof"}</div></td>
    <td className={`py-1 pr-2 font-semibold ${r.result === "fail" ? "text-red-700" : r.result === "pass" ? "text-emerald-800" : ""}`}>
      {RES[r.result] || r.result}{r.points != null ? ` · ${r.points}/${r.max_points}` : ""}<div className="text-[10px] font-normal">{r.reason}</div></td>
    <td className="py-1 text-right whitespace-nowrap">{open && <>
      <button type="button" className="underline text-[11px] mr-2" onClick={() => act("doubt", r)} data-testid={`q-doubt-${r.criterion_id}`}>Raise doubt</button>
      {["pending", "scored_by_evaluators"].includes(r.result) && <button type="button" className="underline text-[11px]" onClick={() => act("score", r)} data-testid={`q-score-${r.criterion_id}`}>Give marks</button>}
    </>}</td>
  </tr>
);

const BidCard = ({ b, refKey, reload, open, me, member }) => {
  const [label, cls] = BADGE[b.status] || [b.status, ""];
  const act = async (kind, r) => {
    try {
      if (kind === "doubt") {
        const reason = window.prompt(`Why do you doubt "${r.title}" for ${b.supplier}? (logged, min 10 characters)`);
        if (!reason) return;
        await criteriaApi.doubt(refKey, b.bid_id, { criterion_id: r.criterion_id, reason });
        toast.success("Doubt recorded — the committee must decide before price opening");
      } else {
        const p = window.prompt(`Marks for "${r.title}" (0–${r.max_points})`);
        if (p === null || p === "") return;
        await criteriaApi.score(refKey, b.bid_id, { criterion_id: r.criterion_id, points: Number(p) });
        toast.success("Marks saved");
      }
      reload();
    } catch (e) { showApiError(e); }
  };
  const resolve = async (decision) => {
    const note = window.prompt(decision === "uphold" ? "Reason for keeping the system result (logged)" : "Reason for disqualifying (logged)");
    if (!note) return;
    try { await criteriaApi.resolve(refKey, b.bid_id, { decision, note }); toast.success("Decision recorded"); reload(); } catch (e) { showApiError(e); }
  };
  const openDoubts = (b.doubts || []).filter((d) => !d.resolved);
  return (
    <div className="border border-brand-navy/15 p-3 bg-white space-y-2" data-testid={`q-bid-${b.bid_ref}`}>
      <div className="flex justify-between gap-2 flex-wrap items-center">
        <div className="text-sm"><b>{b.supplier}</b> · {b.bid_ref}{b.max_points ? ` · ${b.auto_points}/${b.max_points} pts` : ""}</div>
        <span className={`text-[11px] px-2 py-0.5 ${cls}`} data-testid={`q-status-${b.bid_ref}`}>{label}</span>
      </div>
      <table className="w-full text-xs"><tbody>{(b.results || []).map((r) => <Fragment key={r.criterion_id}>
        <ResultRow r={r} act={act} open={open && !b.decision} />
        <ProofReview refKey={refKey} b={b} r={r} me={me} member={member} open={open && !b.decision} reload={reload} />
      </Fragment>)}</tbody></table>
      {openDoubts.map((d) => <div key={d.at} className="text-xs bg-amber-50 border border-amber-300 p-2">Doubt by {d.by}: {d.reason}</div>)}
      {open && openDoubts.length > 0 && <div className="flex gap-2">
        <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => resolve("uphold")} data-testid={`q-uphold-${b.bid_ref}`}>Keep system result</button>
        <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => resolve("disqualify")} data-testid={`q-disqualify-${b.bid_ref}`}>Disqualify</button>
      </div>}
      {b.decision_note && <div className="text-xs">Committee decision: {b.decision_note}</div>}
    </div>
  );
};

export const QualificationPanel = ({ noticeRef, commercialOpen, onChange }) => {
  const [d, setD] = useState(null);
  const load = () => criteriaApi.qualification(noticeRef).then((x) => { setD(x); onChange?.(); }).catch(() => setD(null));
  useEffect(() => { criteriaApi.qualification(noticeRef).then(setD).catch(() => setD(null)); }, [noticeRef]);
  if (!d || !d.criteria_count || !d.bids.length) return null;
  const q = d.bids.filter((b) => b.status === "qualified").length;
  const aiPending = d.bids.some((b) => Object.values(b.proof_reviews || {}).some((p) => ["pending", "failed"].includes(p.ai_status)));
  const rerun = () => criteriaApi.proofAiRun(noticeRef).then((x) => { toast.success(`AI read ${x.read} proof(s)`); load(); }).catch(showApiError);
  return (
    <div className="space-y-2" data-testid={`qualification-panel-${noticeRef}`}>
      <div className="pmc-label">System qualification check · {q} of {d.bids.length} bid(s) qualified</div>
      <p className="text-xs text-brand-navy/70">The system checked every bid against the tender criteria when the technical envelopes opened. Only qualified bids go to price opening.
        Committee members can't change a pass or fail; they can raise a logged doubt on a specific item and then decide. {commercialOpen ? "Price envelopes are open — results are final." : ""}</p>
      <p className="text-xs text-brand-navy/70" data-testid="proof-review-help">For qualified bids, the AI has read each must-pass proof and compared it with what the supplier declared. Every committee member ({d.committee_size}) must accept or reject each proof; one rejection disqualifies the bid. Price opening stays blocked until every proof is decided.
        {!commercialOpen && aiPending && <button type="button" className="underline ml-2" onClick={rerun} data-testid="proof-ai-rerun">Run / retry AI reading</button>}</p>
      {d.bids.map((b) => <BidCard key={b.bid_id} b={b} refKey={noticeRef} reload={load} open={!commercialOpen} me={d.me} member={d.i_am_member} />)}
    </div>
  );
};
