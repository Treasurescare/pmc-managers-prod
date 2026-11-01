import { useState } from "react";
import { toast } from "sonner";
import { criteriaApi, showApiError, uploadsApi } from "@/lib/api";

const VERDICT = { match: ["AI: matches", "text-emerald-800 bg-emerald-50 border-emerald-300"], mismatch: ["AI: does not match", "text-red-800 bg-red-50 border-red-300"],
  unclear: ["AI: unclear", "text-amber-900 bg-amber-50 border-amber-300"] };
const STATUS = { pending: "Awaiting committee", accepted: "Accepted by all members", rejected: "Rejected — bid disqualified" };

const AiFinding = ({ pr }) => {
  if (pr.ai_status === "pending" || pr.ai_status === "running") return <div className="text-[11px] text-brand-navy/60" data-testid="proof-ai-pending">AI is reading the proof…</div>;
  const [label, cls] = VERDICT[pr.ai?.verdict] || VERDICT.unclear;
  return (
    <div className={`border px-2 py-1 text-[11px] ${cls}`} data-testid="proof-ai-finding">
      <b>{label}</b>{pr.ai?.found_value ? ` · document shows: ${pr.ai.found_value}` : ""}<div>{pr.ai?.details}</div>
    </div>);
};

export const ProofReview = ({ refKey, b, r, me, member, open, reload }) => {
  const pr = b.proof_reviews?.[r.criterion_id];
  const [comment, setComment] = useState("");
  if (!pr) return null;
  const mine = pr.votes?.[me];
  const votes = Object.values(pr.votes || {});
  const label = pr.status === "pending" && b.decision ? "Not needed — bid disqualified" : STATUS[pr.status];
  const cast = (decision) => criteriaApi.proofVote(refKey, b.bid_id, r.criterion_id, { decision, comment: comment || null })
    .then((x) => { toast.success(x.status === "pending" ? `Recorded (${x.votes} of ${x.needed} members)` : `Proof ${x.status}`); setComment(""); reload(); }).catch(showApiError);
  return (
    <tr data-testid={`proof-review-${b.bid_ref}-${r.criterion_id}`}><td colSpan={4} className="pb-2">
      <div className="ml-3 pl-3 border-l-2 border-brand-gold space-y-1">
        <div className="flex flex-wrap gap-2 items-center text-[11px]">
          <b>Proof check</b>
          {(b.proof_files?.[r.criterion_id] || []).map((f) => <button key={f.key} type="button" className="underline" onClick={() => uploadsApi.openFile(f.key)} data-testid={`proof-file-${f.key}`}>{f.filename}</button>)}
          <span className={`px-1.5 ${pr.status === "rejected" ? "bg-red-100 text-red-900" : pr.status === "accepted" ? "bg-emerald-100 text-emerald-900" : "bg-amber-100 text-amber-900"}`} data-testid={`proof-status-${b.bid_ref}-${r.criterion_id}`}>{label}</span>
        </div>
        <AiFinding pr={pr} />
        {votes.map((v) => <div key={v.by} className="text-[11px]">{v.by}: <b>{v.decision === "accept" ? "Accepted" : "Rejected"}</b>{v.comment ? ` — ${v.comment}` : ""}</div>)}
        {open && member && pr.status === "pending" && (
          <div className="flex flex-wrap gap-2 items-center">
            <input className="px-2 py-1 border border-brand-navy/20 text-xs flex-1 min-w-[220px]" placeholder={mine ? "Change your decision — comment (required to reject)" : "Your comment (required to reject)"}
              value={comment} onChange={(e) => setComment(e.target.value)} data-testid={`proof-comment-${b.bid_ref}-${r.criterion_id}`} />
            <button type="button" className="text-[11px] px-2 py-1 bg-emerald-700 text-white" onClick={() => cast("accept")} data-testid={`proof-accept-${b.bid_ref}-${r.criterion_id}`}>Accept</button>
            <button type="button" className="text-[11px] px-2 py-1 bg-red-700 text-white" onClick={() => cast("reject")} data-testid={`proof-reject-${b.bid_ref}-${r.criterion_id}`}>Reject</button>
            {mine && <span className="text-[11px] text-brand-navy/60">You {mine.decision}ed</span>}
          </div>)}
      </div>
    </td></tr>);
};
