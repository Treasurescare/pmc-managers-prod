import { useState } from "react";
import { toast } from "sonner";
import { api, showApiError } from "@/lib/api";
import { useNoticeTerms } from "@/apps/notice-board-e/NoticeTermsBanner";

const WinnerFee = ({ n }) => {
  const t = useNoticeTerms(n.notice_ref);
  const [on, setOn] = useState(null);
  if (!t) return null;
  if (t.public_tender) return <span className="text-emerald-800" data-testid={`winner-fee-public-${n.notice_ref}`}>Public tender: no winner charge</span>;
  const val = on ?? t.winner_fee_enabled;
  const save = (v) => api.put(`/api/v1/notice-terms/${n.notice_ref}/winner-fee`, { enabled: v })
    .then(() => { setOn(v); toast.success(v ? "0.30% winner charge added; bidders will see it" : "Winner charge removed"); }).catch(showApiError);
  return (
    <label className="flex items-center gap-1" data-testid={`winner-fee-${n.notice_ref}`}>
      <input type="checkbox" checked={val} onChange={(e) => save(e.target.checked)} data-testid={`winner-fee-toggle-${n.notice_ref}`} />
      Private tender: charge the winning bidder 0.30% of the awarded value (shown to all bidders)
    </label>);
};

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
    ["criteria", mustPass > 0, mustPass ? `${mustPass} must-pass ${mustPass > 1 ? "criteria" : "criterion"}` : "Add at least one must-pass criterion"],
  ];
};

export const PublishChecklist = ({ n, onCriteria, onPublish }) => {
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
      {!n.is_published && <WinnerFee n={n} />}
      {onPublish && <button type="button" disabled={!ready} onClick={onPublish} title={ready ? "Publish this notice now" : "Tick all three items first"}
        className="ml-auto text-[10px] uppercase tracking-widest px-3 py-1 bg-emerald-700 text-white hover:bg-emerald-800 disabled:opacity-40 disabled:cursor-not-allowed"
        data-testid={`publish-checklist-publish-${n.notice_ref}`}>Publish</button>}
    </div>);
};
