import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, showApiError } from "@/lib/api";

const LABEL = { technical: "Technical envelopes", commercial: "Commercial envelopes" };

const Stage = ({ st, s, onApprove, busy, refKey, names }) => (
  <div className="border border-brand-navy/15 p-3 space-y-2" data-testid={`opening-${st}-${refKey}`}>
    <div className="flex items-center justify-between gap-2 flex-wrap">
      <div className="font-semibold text-sm">{LABEL[st]}</div>
      <span className={"text-[10px] uppercase tracking-widest px-2 py-0.5 " + (s.opened_at ? "bg-emerald-700 text-white" : "bg-brand-navy text-white")}
            data-testid={`opening-${st}-state-${refKey}`}>{s.opened_at ? `Opened ${s.opened_at.slice(0, 16).replace("T", " ")}` : "Sealed"}</span>
    </div>
    <div className="text-xs text-brand-navy/70">
      Approved: {s.approvals.map((a) => names[a.by_id] || a.by).join(", ") || "none yet"}
      {!s.opened_at && s.pending.length > 0 && <> · Waiting for: {s.pending.map((p) => p.name).join(", ")}</>}
    </div>
    {!s.opened_at && <>
      {s.blockers.length > 0 && <ul className="text-xs text-amber-800 list-disc pl-4">{s.blockers.map((b) => <li key={b}>{b}</li>)}</ul>}
      {s.i_can_approve && (
        <button type="button" className="pmc-btn pmc-btn--primary" style={{ whiteSpace: "normal", maxWidth: "100%" }} disabled={busy || s.blockers.length > 0}
                onClick={() => onApprove(st)} data-testid={`opening-${st}-approve-${refKey}`}>
          {busy ? "Saving…" : `Approve opening of ${LABEL[st].toLowerCase()}`}
        </button>)}
    </>}
  </div>
);

export const BidOpeningPanel = ({ noticeRef, compact = false }) => {
  const [s, setS] = useState(null);
  const [busy, setBusy] = useState(false);
  const load = () => api.get(`/api/v1/bid-opening/${encodeURIComponent(noticeRef)}`).then((r) => setS(r.data)).catch(() => setS(null));
  useEffect(() => { if (noticeRef) { load(); } }, [noticeRef]); // eslint-disable-line react-hooks/exhaustive-deps
  const approve = async (stage) => {
    setBusy(true);
    try {
      const r = (await api.post(`/api/v1/bid-opening/${encodeURIComponent(noticeRef)}/approve`, { stage })).data;
      toast.success(r.opened ? `All members approved — ${r.bids_opened} bid(s) opened` : `Approval recorded — ${r.remaining} member(s) still to approve`);
      load();
    } catch (e) { showApiError(e); } finally { setBusy(false); }
  };
  if (!s) return null;
  return (
    <section className="bg-white border p-4 space-y-3" data-testid={`bid-opening-panel-${noticeRef}`}>
      <div className="pmc-label">Committee bid opening · {noticeRef}</div>
      <div className="text-xs text-brand-navy/70">
        Opening date: {s.opening_at ? s.opening_at.slice(0, 16).replace("T", " ") + " UTC" : "not set"} ·
        {" "}{s.bids_total} bid(s), {s.bids_emd_confirmed} with deposit confirmed by escrow ·
        {" "}Every committee member must approve ({s.committee.map((m) => m.name).join(", ") || "no committee yet"}).
        Bids whose deposit is not escrow-confirmed at the moment of technical opening stay sealed and cannot be opened later.
      </div>
      <div className={compact ? "grid gap-3" : "grid gap-3 md:grid-cols-2"}>
        {["technical", "commercial"].map((st) => <Stage key={st} st={st} s={s.stages[st]} onApprove={approve} busy={busy} refKey={noticeRef}
          names={Object.fromEntries(s.committee.map((m) => [m.id, m.name]))} />)}
      </div>
    </section>
  );
};
