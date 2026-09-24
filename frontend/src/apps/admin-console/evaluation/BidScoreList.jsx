/**
 * BidScoreList — extracted from EvaluationPanel. Per-bid score entry
 * (technical criteria + commercial %) with per-bid save buttons.
 *
 * Bug-blitz (d) — `readOnly` renders the inputs+buttons as disabled so a
 * user re-opening a locked evaluation cannot start a new scoring pass.
 */
export default function BidScoreList({ bids, rubric, scoreDraft, setScoreDraft, onSaveTech, onSaveComm, readOnly }) {
  if (!bids.length) return null;
  return (
    <div className="bg-white border p-4">
      <div className="pmc-label mb-2">Score bids ({bids.length}){readOnly && <span className="ml-2 text-[10px] text-brand-navy/50">· Locked · read-only</span>}</div>
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
                <input type="number" min="0" max="100" disabled={readOnly}
                  value={(scoreDraft[b.id] || {})[c.code] || ""}
                  onChange={(e) => setScoreDraft({
                    ...scoreDraft,
                    [b.id]: { ...(scoreDraft[b.id] || {}), [c.code]: Number(e.target.value) },
                  })}
                  className="mt-1 w-full border px-2 py-1 disabled:bg-slate-100 disabled:text-slate-400"
                  data-testid={`score-${b.bid_ref}-${c.code}`} />
              </label>
            ))}
          </div>
          <div className="mt-2 flex gap-2 items-end">
            <button onClick={() => onSaveTech(b)} disabled={readOnly} data-testid={`submit-tech-${b.bid_ref}`}
              className="text-xs bg-slate-900 text-white px-3 py-1.5 disabled:opacity-40 disabled:cursor-not-allowed">
              Save Technical
            </button>
            <label className="text-xs">
              <span>Commercial (%)</span>
              <input type="number" min="0" max="100" disabled={readOnly}
                value={scoreDraft[`${b.id}_comm`] || ""}
                onChange={(e) => setScoreDraft({ ...scoreDraft, [`${b.id}_comm`]: e.target.value })}
                className="mt-1 border px-2 py-1 w-24 disabled:bg-slate-100 disabled:text-slate-400" />
            </label>
            <button onClick={() => onSaveComm(b)} disabled={readOnly} data-testid={`submit-comm-${b.bid_ref}`}
              className="text-xs bg-slate-900 text-white px-3 py-1.5 disabled:opacity-40 disabled:cursor-not-allowed">
              Save Commercial
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}
