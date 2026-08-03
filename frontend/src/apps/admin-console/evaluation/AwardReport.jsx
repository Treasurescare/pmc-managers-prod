/**
 * AwardReport — extracted from EvaluationPanel. Renders the recommendation
 * banner + full ranking table for a generated report.
 */
export default function AwardReport({ report }) {
  if (!report) return null;
  return (
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
  );
}
