import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { evalApi, bidApi, formatApiError } from "@/lib/api";
import RubricEditor from "./evaluation/RubricEditor";
import BidScoreList from "./evaluation/BidScoreList";
import AwardReport from "./evaluation/AwardReport";

const DEFAULT_CRITERIA = [
  { code: "experience", label: "Relevant Experience", weight: 0.30, max_score: 100 },
  { code: "methodology", label: "Methodology & Approach", weight: 0.30, max_score: 100 },
  { code: "team", label: "Team & Key Personnel", weight: 0.20, max_score: 100 },
  { code: "financial_health", label: "Financial Health", weight: 0.20, max_score: 100 },
];

export default function EvaluationPanel() {
  const [noticeRef, setNoticeRef] = useState("");
  const [rubric, setRubric] = useState({
    technical_criteria: DEFAULT_CRITERIA, commercial_weight: 0.4, minimum_technical: 60,
  });
  const [coiChoice, setCoiChoice] = useState({ has_conflict: false, details: "" });
  const [bids, setBids] = useState([]);
  const [report, setReport] = useState(null);
  const [scoreDraft, setScoreDraft] = useState({});

  const loadBids = useCallback(async () => {
    if (!noticeRef) return;
    try {
      const list = await bidApi.list({ notice_ref: noticeRef });
      setBids(list || []);
    } catch (e) { toast.error(formatApiError(e)); }
  }, [noticeRef]);
  useEffect(() => { loadBids(); }, [loadBids]);

  const saveRubric = async () => {
    if (!noticeRef) return toast.error("Enter a tender notice ref first");
    try {
      await evalApi.saveRubric({ notice_ref: noticeRef, ...rubric });
      toast.success("Rubric saved");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const declareCOI = async () => {
    if (!noticeRef) return toast.error("Enter notice ref first");
    try {
      await evalApi.declareCOI({ notice_ref: noticeRef, ...coiChoice });
      toast.success("COI recorded");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const submitTechScore = async (bid) => {
    const s = scoreDraft[bid.id] || {};
    try {
      await evalApi.score({ bid_id: bid.id, kind: "technical", scores: s });
      toast.success("Technical score saved");
    } catch (e) { toast.error(formatApiError(e)); }
  };
  const submitCommScore = async (bid) => {
    const v = scoreDraft[`${bid.id}_comm`] || 0;
    try {
      await evalApi.score({ bid_id: bid.id, kind: "commercial", scores: { commercial: Number(v) } });
      toast.success("Commercial score saved");
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const generateReport = async () => {
    if (!noticeRef) return toast.error("Enter notice ref first");
    try {
      const r = await evalApi.awardReport(noticeRef);
      setReport(r);
    } catch (e) { toast.error(formatApiError(e)); }
  };

  const lock = async (kind) => {
    try { await evalApi.lockEnvelope(noticeRef, kind); toast.success(`${kind} envelope locked`); }
    catch (e) { toast.error(formatApiError(e)); }
  };

  return (
    <div data-testid="admin-evaluation-panel" className="space-y-6">
      <div className="bg-white border border-brand-navy/10 p-4">
        <div className="flex flex-wrap gap-3 items-end">
          <label className="flex-1 min-w-[240px] text-sm">
            <span className="pmc-label">Tender notice ref</span>
            <input value={noticeRef} onChange={(e) => setNoticeRef(e.target.value)}
              placeholder="PMC-NOT-2026-0001"
              className="mt-1 w-full px-3 py-2 border border-brand-navy/20"
              data-testid="eval-notice-ref" />
          </label>
          <button onClick={() => lock("technical")} data-testid="lock-technical"
            className="px-3 py-2 text-[11px] uppercase tracking-widest border">Lock Tech</button>
          <button onClick={() => lock("commercial")} data-testid="lock-commercial"
            className="px-3 py-2 text-[11px] uppercase tracking-widest border">Lock Comm</button>
          <button onClick={generateReport} data-testid="award-report-btn"
            className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
            Generate Award Report
          </button>
        </div>
      </div>

      <RubricEditor rubric={rubric} setRubric={setRubric} onSave={saveRubric} />

      <div className="bg-white border p-4">
        <div className="pmc-label mb-2">Your Conflict-of-Interest declaration for this tender</div>
        <label className="flex items-center gap-2 text-sm">
          <input type="checkbox" checked={coiChoice.has_conflict}
            onChange={(e) => setCoiChoice({ ...coiChoice, has_conflict: e.target.checked })}
            data-testid="coi-has-conflict" />
          I have a conflict of interest with a bidder on this tender
        </label>
        {coiChoice.has_conflict && (
          <input value={coiChoice.details}
            onChange={(e) => setCoiChoice({ ...coiChoice, details: e.target.value })}
            placeholder="Describe the conflict"
            className="mt-2 w-full px-3 py-2 border" />
        )}
        <button onClick={declareCOI} data-testid="declare-coi"
          className="mt-2 px-4 py-2 text-[11px] uppercase tracking-widest border">
          Declare
        </button>
      </div>

      <BidScoreList
        bids={bids} rubric={rubric}
        scoreDraft={scoreDraft} setScoreDraft={setScoreDraft}
        onSaveTech={submitTechScore} onSaveComm={submitCommScore}
      />

      <AwardReport report={report} />
    </div>
  );
}
