const OPS = { gte: "at least", lte: "at most", eq: "exactly" };

export const criteriaReady = (criteria, answers, docs) => criteria.every((c) => {
  const v = answers[c.id];
  const needsAnswer = c.kind === "must_pass" || c.scoring === "auto";
  const answered = v !== undefined && v !== null && v !== "";
  const proofOk = !c.proof_required || docs.some((d) => d.criterion_id === c.id);
  return (!needsAnswer || answered) && proofOk;
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

export default function BidCriteriaSection({ criteria, answers, setAnswer, docs, onUpload, prefilled }) {
  if (!criteria.length) return null;
  const ready = criteriaReady(criteria, answers, docs);
  return (
    <div className="space-y-3" data-testid="bid-criteria">
      <div className="text-sm font-semibold text-slate-900">Tender criteria <span className="text-red-600">*</span></div>
      <div className="text-xs text-slate-600">Answer each item and attach the proof asked for. Your answers and proofs are sealed with your bid and checked automatically when bids are opened.</div>
      {criteria.map((c) => {
        const proofs = docs.filter((d) => d.criterion_id === c.id);
        return (
          <div key={c.id} className="border rounded-md p-3 bg-white" data-testid={`crit-item-${c.id}`}>
            <div className="text-sm font-medium text-slate-900">{c.title}
              <span className={`ml-2 text-[10px] uppercase tracking-widest ${c.kind === "must_pass" ? "text-red-700" : "text-slate-500"}`}>{c.kind === "must_pass" ? "Must pass" : `Scored · up to ${c.max_points} pts`}</span></div>
            <div className="text-xs text-slate-600">
              {c.answer_type === "number" && <>Requirement: {OPS[c.operator]} {Number(c.threshold).toLocaleString()} {c.unit}{c.period ? ` · ${c.period}` : ""}</>}
              {c.answer_type === "yes_no" && "Requirement: Yes"}
              {c.answer_type === "text" && "Written answer, marked by evaluators"}
            </div>
            <AnswerInput c={c} value={answers[c.id]} onChange={(v) => setAnswer(c.id, v)} />
            {prefilled[c.id] !== undefined && <div className="text-[11px] text-emerald-700 mt-1">Filled from your PMC profile — check it's still correct.</div>}
            {c.proof && (
              <div className="mt-2 flex items-center gap-2 flex-wrap text-xs">
                <span>Proof: {c.proof}{c.proof_required ? <span className="text-red-600"> *</span> : " (optional)"}</span>
                <label className="px-2 py-1 border border-amber-500 bg-amber-50 rounded cursor-pointer" data-testid={`crit-proof-upload-${c.id}`}>
                  + Upload<input type="file" hidden onChange={(e) => e.target.files?.[0] && onUpload(c.id, e.target.files[0], e.target)} data-testid={`crit-proof-input-${c.id}`} />
                </label>
                {proofs.map((p) => <span key={p.key} className="text-emerald-800">✓ {p.filename}</span>)}
              </div>)}
          </div>);
      })}
      <div className={`text-xs ${ready ? "text-emerald-700" : "text-amber-700"}`} data-testid="bid-criteria-status">{ready ? "All criteria answered ✓" : "Answer every must-pass item and attach the required proofs to submit."}</div>
    </div>
  );
}
