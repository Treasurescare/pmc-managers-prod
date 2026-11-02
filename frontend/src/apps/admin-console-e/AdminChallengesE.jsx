import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import AdminEShell from "./AdminEShell";
import { challengeApi, showApiError, BACKEND_URL } from "@/lib/api";
import { STATUS } from "@/apps/vendor-portal-e/VendorChallengePanel";

const inp = "px-3 py-2 border border-brand-navy/20 bg-white text-sm";
const fmt = (s) => (s ? s.slice(0, 16).replace("T", " ") + " UTC" : "—");

const Standstill = ({ t, onDone }) => {
  const [days, setDays] = useState(t.days);
  const [why, setWhy] = useState("");
  const save = () => challengeApi.standstill(t.notice_ref, { days: Number(days), reason: why })
    .then((r) => { toast.success(`Corrigendum ${r.corrigendum_no} published to all bidders`); setWhy(""); onDone(); }).catch(showApiError);
  return (
    <div className="bg-white border border-brand-navy/15 p-4 space-y-2" data-testid={`standstill-${t.notice_ref}`}>
      <div className="flex justify-between flex-wrap gap-2"><b className="font-mono text-sm">{t.notice_ref}</b>
        <a href={`${BACKEND_URL}/api/v1/bid-challenges/notice/${t.notice_ref}/register.pdf`} className="text-xs underline" data-testid={`register-pdf-${t.notice_ref}`}>Download challenge register (PDF)</a>
        <span className={`text-xs px-2 py-0.5 ${t.contract_block ? "bg-amber-100 text-amber-900" : "bg-emerald-100 text-emerald-900"}`} data-testid="standstill-signing">
          {t.contract_block ? "Contract signing blocked" : "Contract may be signed"}</span></div>
      <div className="text-sm">{t.days}-day standstill · awarded {fmt(t.started_at)} · ends {fmt(t.ends_at)}</div>
      {t.contract_block && <div className="text-xs text-amber-900" data-testid="standstill-reason">{t.contract_block}</div>}
      {t.running && <div className="flex flex-wrap gap-2 items-center">
        <input type="number" min={1} max={60} className={inp + " w-20"} value={days} onChange={(e) => setDays(e.target.value)} data-testid="standstill-days" />
        <input className={inp + " flex-1 min-w-[220px]"} placeholder="Reason (published as a corrigendum)" value={why} onChange={(e) => setWhy(e.target.value)} data-testid="standstill-reason-input" />
        <button type="button" className="pmc-btn pmc-btn--secondary" disabled={why.trim().length < 5 || Number(days) === t.days} onClick={save} data-testid="standstill-save">Change via corrigendum</button>
      </div>}
    </div>);
};

const Vote = ({ c, onDone }) => {
  const [txt, setTxt] = useState("");
  const go = (decision) => challengeApi.vote(c.id, { decision, comment: txt }).then(() => { toast.success("Vote recorded"); onDone(); }).catch(showApiError);
  return (
    <div className="flex flex-wrap gap-2" data-testid={`vote-${c.id}`}>
      <input className={inp + " flex-1 min-w-[220px]"} placeholder="Your reason (recorded)" value={txt} onChange={(e) => setTxt(e.target.value)} data-testid="vote-comment" />
      <button type="button" className="pmc-btn pmc-btn--primary" disabled={txt.trim().length < 3} onClick={() => go("uphold")} data-testid="vote-uphold">Uphold</button>
      <button type="button" className="pmc-btn pmc-btn--secondary" disabled={txt.trim().length < 3} onClick={() => go("dismiss")} data-testid="vote-dismiss">Dismiss</button>
    </div>);
};

const Meeting = ({ c, onDone }) => {
  const [at, setAt] = useState("");
  const [loc, setLoc] = useState("");
  const go = () => challengeApi.meeting(c.id, { scheduled_at: new Date(at).toISOString(), location: loc })
    .then(() => { toast.success("Meeting scheduled — invitations sent"); onDone(); }).catch(showApiError);
  return (
    <div className="flex flex-wrap gap-2" data-testid={`meeting-form-${c.id}`}>
      <input type="datetime-local" className={inp} value={at} onChange={(e) => setAt(e.target.value)} data-testid="meeting-at" title="Your local time" />
      <input className={inp + " flex-1 min-w-[220px]"} placeholder="Place or video link" value={loc} onChange={(e) => setLoc(e.target.value)} data-testid="meeting-location" />
      <button type="button" className="pmc-btn pmc-btn--primary" disabled={!at || loc.trim().length < 2} onClick={go} data-testid="meeting-save">Schedule resolution meeting</button>
    </div>);
};

const Outcome = ({ c, onDone, appeal }) => {
  const [txt, setTxt] = useState("");
  const go = (v) => (appeal ? challengeApi.appealDecision(c.id, { decision: v, reason: txt }) : challengeApi.resolve(c.id, { outcome: v, minutes: txt }))
    .then(() => { toast.success("Decision recorded"); onDone(); }).catch(showApiError);
  const [a, b] = appeal ? [["uphold", "Uphold appeal"], ["dismiss", "Dismiss (final)"]] : [["confirm_award", "Confirm award"], ["re_evaluate", "Withdraw award & re-evaluate"]];
  return (
    <div className="space-y-2" data-testid={`${appeal ? "appeal" : "resolution"}-form-${c.id}`}>
      <textarea rows={3} className={inp + " w-full"} placeholder={appeal ? "Reason for your decision" : "Meeting minutes and decision"} value={txt} onChange={(e) => setTxt(e.target.value)} data-testid={appeal ? "appeal-decision-reason" : "resolution-minutes"} />
      <div className="flex gap-2">{[a, b].map(([v, l], i) => <button key={v} type="button" className={`pmc-btn ${i ? "pmc-btn--secondary" : "pmc-btn--primary"}`}
        disabled={txt.trim().length < 10} onClick={() => go(v)} data-testid={`${appeal ? "appeal" : "resolution"}-${v}`}>{l}</button>)}</div>
    </div>);
};

const Card = ({ c, onDone, staff }) => (
  <div className="bg-white border border-brand-navy/15 p-4 space-y-2 text-sm" data-testid={`challenge-${c.id}`}>
    <div className="flex justify-between flex-wrap gap-2"><b>{c.challenge_ref} · {c.company_name || c.vendor_email}</b>
      <span className="text-xs px-2 py-0.5 bg-brand-navy/5" data-testid="challenge-status">{STATUS[c.status] || c.status}</span></div>
    <div className="text-xs text-brand-navy/60">Tender {c.notice_ref} · bid {c.bid_ref} · grounds: {c.grounds} · lodged {fmt(c.created_at)}</div>
    <p>{c.details}</p>
    <div className="text-xs" data-testid="challenge-votes">Committee votes {Object.keys(c.votes || {}).length} of {c.committee_size}
      {Object.values(c.votes || {}).map((v, i) => <div key={i}>· {v.by}: <b>{v.decision}</b> — “{v.comment}”</div>)}</div>
    {c.i_can_vote && <Vote c={c} onDone={onDone} />}
    {c.status === "upheld" && <Meeting c={c} onDone={onDone} />}
    {c.meeting && <div className="text-xs">Meeting {fmt(c.meeting.scheduled_at)} · {c.meeting.location} · {c.meeting.attendees.length} invited (committee, issuer, bidding teams)</div>}
    {!staff && c.status === "meeting_scheduled" && new Date(c.meeting.scheduled_at) <= new Date() && <Outcome c={c} onDone={onDone} />}
    {c.appeal_reason && <div className="text-xs">Appeal: “{c.appeal_reason}”{c.appeal_decision && <> → <b>{c.appeal_decision}</b> by {c.appeal_decided_by}</>}</div>}
    {c.i_can_decide_appeal && <Outcome c={c} onDone={onDone} appeal />}
    {c.resolution && <div className="text-xs">Outcome: <b>{c.resolution.outcome}</b> — {c.resolution.minutes}</div>}
  </div>);

export function ChallengesBody({ staff = false }) {
  const [d, setD] = useState(null);
  const load = useCallback(() => challengeApi.list().then(setD).catch(showApiError), []);
  useEffect(() => { load(); }, [load]);
  return (
      <div className={staff ? "space-y-6" : "p-6 space-y-6"} data-testid="challenges-page">
        <p className="text-sm text-brand-navy/70 max-w-3xl">After an award, a standstill period (10 days unless changed by corrigendum) blocks contract signing. Bidders on the tender can lodge a challenge (one open at a time); the committee votes, an upheld challenge suspends the award until a resolution meeting with the committee, issuer and bidding teams, and a dismissed one can be appealed once to a senior officer who is not on the committee.</p>
        {!d ? <div className="text-sm">Loading…</div> : <>
          <section className="space-y-3"><h2 className="font-serif text-xl text-brand-navy">Standstill on awarded tenders</h2>
            {d.tenders.map((t) => staff ? <div key={t.notice_ref} className="text-sm">{t.notice_ref}: {t.contract_block || "Contract may be signed"}</div> : <Standstill key={t.notice_ref} t={t} onDone={load} />)}
            {!d.tenders.length && <p className="text-sm text-brand-navy/60">No awarded tenders yet.</p>}</section>
          <section className="space-y-3"><h2 className="font-serif text-xl text-brand-navy">Challenges ({d.challenges.length})</h2>
            {d.challenges.map((c) => <Card key={c.id} c={c} onDone={load} staff={staff} />)}
            {!d.challenges.length && <p className="text-sm text-brand-navy/60" data-testid="challenges-empty">No challenges lodged.</p>}</section>
        </>}
      </div>
  );
}

export default function AdminChallengesE() {
  return (
    <AdminEShell active="Bid challenges" crumb={<>Procurement / <b>Bid challenges</b></>}>
      <ChallengesBody />
    </AdminEShell>
  );
}
