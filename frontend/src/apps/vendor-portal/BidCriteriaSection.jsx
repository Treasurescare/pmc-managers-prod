const OPS = { gte: "at least", lte: "at most", eq: "exactly" };
const RULE = { lead: "the lead member alone", combined: "all members combined", each: "every member" };
const teamItem = (c, members) => !!members?.length && c.answer_type !== "text" && ["each", "combined"].includes(c.consortium_rule || "each");

const isMand = (c) => c.mandatory ?? c.kind === "must_pass";

export const criteriaReady = (criteria, answers, docs, members, memberAnswers = {}) => criteria.every((c) => {
  const v = answers[c.id];
  const needsAnswer = isMand(c);
  const filled = (x) => x !== undefined && x !== null && x !== "";
  const proofOk = !c.proof_required || docs.some((d) => d.criterion_id === c.id) || (!needsAnswer && !filled(v)) || v === false;
  const teamOk = !(teamItem(c, members) && needsAnswer && (c.consortium_rule || "each") === "each")
    || members.every((m) => filled((memberAnswers[c.id] || {})[m.vendor_id]));
  return (!needsAnswer || filled(v)) && proofOk && teamOk;
});

const AnswerInput = ({ c, value, onChange }) => {
  const cls = "mt-1 w-full border rounded-md px-3 py-2 text-sm";
  if (c.answer_type === "yes_no") {
    return (
      <div className="flex gap-4 mt-1 text-sm">
        {[[true, "Yes"], [false, "No"]].map(([v, l]) => (
          <label key={l} className="flex gap-1 items-center"><input type="radio" checked={value === v} onChange={() => onChange(v)} data-testid={`crit-ans-${c.id}-${l.toLowerCase()}`} />{l}</label>))}
      </div>);
  }
  if (c.answer_type === "text") return <textarea rows={3} className={cls} value={value || ""} onChange={(e) => onChange(e.target.value)} data-testid={`crit-ans-${c.id}`} />;
  return <input type="number" className={cls} value={value ?? ""} onChange={(e) => onChange(e.target.value)} placeholder={c.unit ? `In ${c.unit}` : ""} data-testid={`crit-ans-${c.id}`} />;
};

export default function BidCriteriaSection({ criteria, answers, setAnswer, docs, onUpload, prefilled, members, memberAnswers = {}, setMemberAnswer, minOptional = null }) {
  if (!criteria.length) return null;
  const ready = criteriaReady(criteria, answers, docs, members, memberAnswers);
  const opt = criteria.filter((c) => c.kind === "must_pass" && !isMand(c)).length;
  return (
    <div className="space-y-3" data-testid="bid-criteria">
      <div className="text-sm font-semibold text-slate-900">Tender criteria <span className="text-red-600">*</span></div>
      <div className="text-xs text-slate-600">Answer each item and attach the proof asked for. Your answers and proofs are sealed with your bid and checked automatically when bids are opened.</div>
      {opt > 0 && <div className="text-xs bg-amber-50 border border-amber-300 rounded p-2" data-testid="bid-criteria-rule">To qualify you must meet <b>every mandatory</b> criterion and <b>at least {Math.min(minOptional ?? opt, opt)} of the {opt} optional</b> pass/fail criteria.</div>}
      {criteria.map((c) => {
        const proofs = docs.filter((d) => d.criterion_id === c.id);
        return (
          <div key={c.id} className="border rounded-md p-3 bg-white" data-testid={`crit-item-${c.id}`}>
            <div className="text-sm font-medium text-slate-900">{c.title}
              <span className={`ml-2 text-[10px] uppercase tracking-widest ${isMand(c) ? "text-red-700" : "text-slate-500"}`} data-testid={`crit-badge-${c.id}`}>{isMand(c) ? "Mandatory" : "Optional"} · {c.kind === "must_pass" ? "pass / fail" : `scored · up to ${c.max_points} pts`}</span></div>
            <div className="text-xs text-slate-600">
              {c.answer_type === "number" && <>Requirement: {OPS[c.operator]} {Number(c.threshold).toLocaleString()} {c.unit}{c.period ? ` · ${c.period}` : ""}</>}
              {c.answer_type === "yes_no" && "Requirement: Yes"}
              {c.answer_type === "text" && "Written answer, marked by evaluators"}
            </div>
            <AnswerInput c={c} value={answers[c.id]} onChange={(v) => setAnswer(c.id, v)} />
            {members?.length > 0 && c.answer_type !== "text" && <div className="text-[11px] text-slate-600 mt-1" data-testid={`crit-rule-${c.id}`}>For this consortium, this must be met by {RULE[c.consortium_rule || "each"]}.{teamItem(c, members) ? " The box above is your company's (lead) figure; enter each member's figure below." : ""}</div>}
            {teamItem(c, members) && members.map((m) => (
              <div key={m.vendor_id} className="mt-1 pl-3 border-l" data-testid={`crit-member-${c.id}-${m.vendor_id}`}>
                <div className="text-xs font-medium">{m.company_name}</div>
                <AnswerInput c={{ ...c, id: `${c.id}-${m.vendor_id}` }} value={(memberAnswers[c.id] || {})[m.vendor_id]} onChange={(v) => setMemberAnswer(c.id, m.vendor_id, v)} />
              </div>))}
            {prefilled[c.id] !== undefined && <div className="text-[11px] text-emerald-700 mt-1">Filled from your PMC profile — check it's still correct.</div>}
            {(c.proof || c.proof_required) && (
              <div className="mt-2 flex items-center gap-2 flex-wrap text-xs">
                <span>Proof: {c.proof || "Supporting document"}{c.proof_required ? <span className="text-red-600"> *</span> : " (optional)"}</span>
                <label className="px-2 py-1 border border-amber-500 bg-amber-50 rounded cursor-pointer" data-testid={`crit-proof-upload-${c.id}`}>
                  + Upload<input type="file" hidden onChange={(e) => e.target.files?.[0] && onUpload(c.id, e.target.files[0], e.target)} data-testid={`crit-proof-input-${c.id}`} />
                </label>
                {proofs.map((p) => <span key={p.key} className="text-emerald-800">✓ {p.filename}</span>)}
              </div>)}
          </div>);
      })}
      <div className={`text-xs ${ready ? "text-emerald-700" : "text-amber-700"}`} data-testid="bid-criteria-status">{ready ? "All mandatory criteria answered ✓" : "Answer every mandatory item and attach the required proofs to submit."}</div>
    </div>
  );
}
