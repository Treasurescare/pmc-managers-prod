/**
 * AwardReport — extracted from EvaluationPanel. Renders the recommendation
 * banner + full ranking table for a generated report.
 */
export default function AwardReport({ report }) {
  // v52bl — guard: previously `if (!report) return null;` admitted `{}`
  // (parent passed `report || {}`), and the else-branch below crashed on
  // `report.rubric.minimum_technical` -> "Something crashed on this screen".
  if (!report || !report.notice_ref) return null;
  const minTech = report.rubric?.minimum_technical ?? 60;
  return (
    <div className="bg-white border p-4" data-testid="award-report">
      <div className="text-lg font-serif mb-2">Award Recommendation Report — {report.notice_ref}</div>
      <div className="text-xs mb-2" data-testid="award-report-method">Ranking rule for this tender: <b>{report.award_method === "weighted" ? "Weighted technical and price marks" : "Lowest price wins (L1) among qualified bids"}</b></div>
      {report.recommendation ? (
        <div className="bg-emerald-50 border border-emerald-200 p-3 mb-3">
          <strong>Recommended for award:</strong> {report.recommendation.vendor} ·
          Bid {report.recommendation.bid_ref} · Combined score {report.recommendation.combined}%
          · Price {report.recommendation.price?.toLocaleString()}
        </div>
      ) : (
        <div className="bg-amber-50 border border-amber-200 p-3 mb-3">
          No bid qualifies{report.award_method === "weighted" ? ` (all below the ${minTech}% technical cutoff)` : " (no bid passed the tender criteria and proof review)"}.
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
          {(report.ranking || []).map((r, i) => (
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
  );
}
