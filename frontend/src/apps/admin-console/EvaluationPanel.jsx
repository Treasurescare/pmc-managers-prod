import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { evalApi, bidApi, formatApiError } from "@/lib/api";

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

      <div className="bg-white border p-4">
        <div className="pmc-label mb-2">Scoring Rubric</div>
        <table className="w-full text-sm">
          <thead className="text-xs text-brand-navy/60"><tr>
            <th className="text-left">Criterion</th><th>Weight</th><th>Max</th>
          </tr></thead>
          <tbody>
            {rubric.technical_criteria.map((c, i) => (
              <tr key={c.code}>
                <td className="py-1">{c.label}</td>
                <td className="py-1 text-center">
                  <input type="number" step="0.05" min="0" max="1" value={c.weight}
                    onChange={(e) => {
                      const arr = [...rubric.technical_criteria];
                      arr[i] = { ...c, weight: Number(e.target.value) };
                      setRubric({ ...rubric, technical_criteria: arr });
                    }} className="w-20 border px-2 py-1" />
                </td>
                <td className="py-1 text-center">{c.max_score}</td>
              </tr>
            ))}
            <tr>
              <td className="py-1">Commercial weight (of combined)</td>
              <td className="py-1 text-center">
                <input type="number" step="0.05" min="0" max="1" value={rubric.commercial_weight}
                  onChange={(e) => setRubric({ ...rubric, commercial_weight: Number(e.target.value) })}
                  className="w-20 border px-2 py-1" /></td>
            </tr>
            <tr>
              <td className="py-1">Minimum technical cutoff (%)</td>
              <td className="py-1 text-center">
                <input type="number" min="0" max="100" value={rubric.minimum_technical}
                  onChange={(e) => setRubric({ ...rubric, minimum_technical: Number(e.target.value) })}
                  className="w-20 border px-2 py-1" /></td>
            </tr>
          </tbody>
        </table>
        <button onClick={saveRubric} data-testid="save-rubric"
          className="mt-3 px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white">
          Save rubric
        </button>
      </div>

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

      {bids.length > 0 && (
        <div className="bg-white border p-4">
          <div className="pmc-label mb-2">Score bids ({bids.length})</div>
          {bids.map((b) => (
            <div key={b.id} className="border rounded p-3 mb-3" data-testid={`eval-bid-${b.bid_ref}`}>
              <div className="flex justify-between items-baseline">
                <div>
                  <span className="font-mono text-xs">{b.bid_ref}</span>
                  <span className="ml-2 text-sm">{b.company_name || b.vendor_email}</span>
                  <span className="ml-2 text-xs text-slate-500">
                    Price: {b.price_currency} {(b.price_amount || 0).toLocaleString()}
                  </span>
                </div>
                <span className="text-xs bg-slate-100 px-2 py-0.5 rounded">{b.status}</span>
              </div>
              <div className="mt-2 grid grid-cols-4 gap-2 text-xs">
                {rubric.technical_criteria.map((c) => (
                  <label key={c.code}>
                    <span>{c.label}</span>
                    <input type="number" min="0" max="100"
                      value={(scoreDraft[b.id] || {})[c.code] || ""}
                      onChange={(e) => setScoreDraft({
                        ...scoreDraft,
                        [b.id]: { ...(scoreDraft[b.id] || {}), [c.code]: Number(e.target.value) },
                      })}
                      className="mt-1 w-full border px-2 py-1"
                      data-testid={`score-${b.bid_ref}-${c.code}`} />
                  </label>
                ))}
              </div>
              <div className="mt-2 flex gap-2 items-end">
                <button onClick={() => submitTechScore(b)} data-testid={`submit-tech-${b.bid_ref}`}
                  className="text-xs bg-slate-900 text-white px-3 py-1.5">
                  Save Technical
                </button>
                <label className="text-xs">
                  <span>Commercial (%)</span>
                  <input type="number" min="0" max="100"
                    value={scoreDraft[`${b.id}_comm`] || ""}
                    onChange={(e) => setScoreDraft({ ...scoreDraft, [`${b.id}_comm`]: e.target.value })}
                    className="mt-1 border px-2 py-1 w-24" />
                </label>
                <button onClick={() => submitCommScore(b)} data-testid={`submit-comm-${b.bid_ref}`}
                  className="text-xs bg-slate-900 text-white px-3 py-1.5">
                  Save Commercial
                </button>
              </div>
            </div>
          ))}
        </div>
      )}

      {report && (
        <div className="bg-white border p-4" data-testid="award-report">
          <div className="text-lg font-serif mb-2">Award Recommendation Report — {report.notice_ref}</div>
          {report.recommendation ? (
            <div className="bg-emerald-50 border border-emerald-200 p-3 mb-3">
              <strong>Recommended for award:</strong> {report.recommendation.vendor} ·
              Bid {report.recommendation.bid_ref} · Combined score {report.recommendation.combined}%
              · Price {report.recommendation.price?.toLocaleString()}
            </div>
          ) : (
            <div className="bg-amber-50 border border-amber-200 p-3 mb-3">
              No bid qualifies (all below the {report.rubric.minimum_technical}% technical cutoff).
            </div>
          )}
          <table className="w-full text-sm">
            <thead className="text-xs text-brand-navy/60">
              <tr>
                <th className="text-left px-2">#</th><th className="text-left px-2">Bid</th>
                <th className="text-left px-2">Vendor</th><th className="text-right px-2">Price</th>
                <th className="text-right px-2">Tech %</th><th className="text-right px-2">Comm %</th>
                <th className="text-right px-2">Combined</th><th className="text-center px-2">Qualifies</th>
              </tr>
            </thead>
            <tbody>
              {report.ranking.map((r, i) => (
                <tr key={r.bid_id} className="border-t">
                  <td className="px-2 py-1">{i + 1}</td>
                  <td className="px-2 py-1 font-mono text-xs">{r.bid_ref}</td>
                  <td className="px-2 py-1">{r.vendor}</td>
                  <td className="px-2 py-1 text-right">{(r.price || 0).toLocaleString()}</td>
                  <td className="px-2 py-1 text-right">{r.technical_avg}</td>
                  <td className="px-2 py-1 text-right">{r.commercial_avg}</td>
                  <td className="px-2 py-1 text-right font-semibold">{r.combined}</td>
                  <td className="px-2 py-1 text-center">{r.qualifies ? "✓" : "—"}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
