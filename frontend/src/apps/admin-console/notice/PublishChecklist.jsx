const checks = (n) => {
  const dl = n.submission_deadline ? new Date(n.submission_deadline) : null;
  const pre = n.pre_bid_meeting_date ? new Date(n.pre_bid_meeting_date) : null;
  const datesOk = !!dl && dl > new Date() && (!pre || pre <= dl);
  const datesMsg = !dl ? "Set the bid submission deadline" : dl <= new Date() ? "Deadline is in the past — move it to a future date"
    : pre && pre > dl ? "Pre-bid meeting must be on or before the deadline" : "Deadline in the future";
  const mustPass = (n.tender_criteria || []).filter((c) => c.kind === "must_pass").length;
  return [
    ["document", !!n.primary_document?.url, n.primary_document?.url ? "Tender document attached" : "Attach the main tender document (Edit)"],
    ["dates", datesOk, datesMsg],
    ["criteria", mustPass > 0, mustPass ? `${mustPass} must-pass criterion${mustPass > 1 ? "s" : ""}` : "Add at least one must-pass criterion"],
  ];
};

export const PublishChecklist = ({ n, onCriteria }) => {
  const items = checks(n);
  const ready = items.every(([, ok]) => ok);
  return (
    <div className={`mt-2 border px-3 py-2 text-xs flex flex-wrap items-center gap-x-4 gap-y-1 ${ready ? "border-emerald-200 bg-emerald-50/60" : "border-amber-200 bg-amber-50/60"}`}
         data-testid={`publish-checklist-${n.notice_ref}`}>
      <b className={ready ? "text-emerald-800" : "text-amber-900"} data-testid={`publish-checklist-status-${n.notice_ref}`}>
        {ready ? "Ready to publish" : "Ready to publish?"}</b>
      {items.map(([k, ok, label]) => (
        <span key={k} className={ok ? "text-emerald-800" : "text-amber-900"} data-testid={`publish-check-${k}-${n.notice_ref}`} data-ok={ok}>
          {ok ? "✓" : "○"} {label}
          {k === "criteria" && !ok && <button type="button" className="underline ml-1" onClick={onCriteria} data-testid={`publish-check-criteria-open-${n.notice_ref}`}>Add now</button>}
        </span>))}
    </div>);
};
