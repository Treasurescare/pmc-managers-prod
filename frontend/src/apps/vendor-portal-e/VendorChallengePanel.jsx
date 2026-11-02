import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { challengeApi, showApiError } from "@/lib/api";

const GROUNDS = [["criteria", "Unfair or unclear criteria"], ["evaluation", "Evaluation of my bid"], ["proof_review", "Proof review decision"],
  ["price", "Price comparison / ranking"], ["process", "Tender process or timing"], ["other", "Other"]];
export const STATUS = { lodged: "Lodged — awaiting committee", under_review: "Under committee review", upheld: "Upheld — award suspended",
  meeting_scheduled: "Resolution meeting scheduled", resolved: "Resolved", dismissed: "Dismissed", appealed: "Appeal with senior officer", closed: "Closed — final" };
const box = "border border-brand-navy/15 bg-white p-4 space-y-2";
const fmt = (s) => (s ? s.slice(0, 16).replace("T", " ") + " UTC" : "—");

const LodgeForm = ({ bidId, onDone }) => {
  const [g, setG] = useState("evaluation");
  const [t, setT] = useState("");
  const go = () => challengeApi.lodge(bidId, { grounds: g, details: t }).then(() => { toast.success("Challenge lodged"); setT(""); onDone(); }).catch(showApiError);
  return (
    <div className="space-y-2" data-testid="challenge-form">
      <select className="px-3 py-2 border border-brand-navy/20 text-sm" value={g} onChange={(e) => setG(e.target.value)} data-testid="challenge-grounds">
        {GROUNDS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select>
      <textarea className="w-full px-3 py-2 border border-brand-navy/20 text-sm" rows={4} value={t} onChange={(e) => setT(e.target.value)}
        placeholder="Explain what you believe was wrong and why (at least 20 characters)" data-testid="challenge-details" />
      <button type="button" className="pmc-btn pmc-btn--primary" disabled={t.trim().length < 20} onClick={go} data-testid="challenge-submit">Lodge challenge</button>
    </div>);
};

const AppealForm = ({ c, onDone }) => {
  const [t, setT] = useState("");
  return (
    <div className="space-y-2" data-testid={`appeal-form-${c.id}`}>
      <textarea className="w-full px-3 py-2 border border-brand-navy/20 text-sm" rows={3} value={t} onChange={(e) => setT(e.target.value)}
        placeholder="Why should a senior officer review this decision? (at least 20 characters)" data-testid="appeal-reason" />
      <button type="button" className="pmc-btn pmc-btn--secondary" disabled={t.trim().length < 20} data-testid="appeal-submit"
        onClick={() => challengeApi.appeal(c.id, t).then(() => { toast.success("Appeal sent to a senior officer"); onDone(); }).catch(showApiError)}>Appeal (one time only)</button>
    </div>);
};

const MyChallenge = ({ c, onDone }) => (
  <div className="border-t border-brand-navy/10 pt-2 text-sm" data-testid={`my-challenge-${c.id}`}>
    <div className="flex justify-between flex-wrap gap-2"><b>{c.challenge_ref}</b><span className="text-xs px-2 py-0.5 bg-brand-navy/5" data-testid="my-challenge-status">{STATUS[c.status] || c.status}</span></div>
    <p className="text-brand-navy/70">{c.details}</p>
    {c.meeting && <p className="text-xs">Meeting: {fmt(c.meeting.scheduled_at)} · {c.meeting.location}</p>}
    {c.resolution && <p className="text-xs">Outcome: <b>{c.resolution.outcome === "confirm_award" ? "Award confirmed" : "Award withdrawn — tender re-evaluated"}</b></p>}
    {c.appeal_decision && <p className="text-xs">Appeal: <b>{c.appeal_decision === "uphold" ? "upheld" : "dismissed (final)"}</b> — {c.appeal_decision_reason}</p>}
    {c.status === "dismissed" && !c.appealed_at && c.appeal_deadline > new Date().toISOString() && <><p className="text-xs">You may appeal until {fmt(c.appeal_deadline)}.</p><AppealForm c={c} onDone={onDone} /></>}
  </div>);

export const VendorChallengePanel = ({ bidId }) => {
  const [s, setS] = useState(null);
  const load = useCallback(() => challengeApi.mine(bidId).then(setS).catch(() => setS(null)), [bidId]);
  useEffect(() => { load(); }, [load]);
  if (!s) return null;
  const st = s.standstill;
  return (
    <div className={box} data-testid="challenge-panel">
      <div className="text-[11px] uppercase tracking-widest text-brand-gold">Bid challenge</div>
      <p className="text-sm" data-testid="challenge-standstill">{st.running
        ? <>The standstill period ({st.days} days) runs until <b>{fmt(st.ends_at)}</b>. No contract can be signed before then, and you can lodge one formal challenge during this time.</>
        : st.awarded ? <>The {st.days}-day standstill period ended on {fmt(st.ends_at)}.</> : <>The standstill period starts when the tender is awarded.</>}</p>
      {s.can_lodge ? <LodgeForm bidId={bidId} onDone={load} /> : s.why_not && !s.challenges.length && <p className="text-xs text-brand-navy/60" data-testid="challenge-why-not">{s.why_not}</p>}
      {s.challenges.map((c) => <MyChallenge key={c.id} c={c} onDone={load} />)}
    </div>);
};
