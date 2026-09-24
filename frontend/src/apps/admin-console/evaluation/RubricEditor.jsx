/**
 * RubricEditor — extracted from EvaluationPanel. Renders the scoring rubric
 * (technical criteria weights + commercial weight + minimum cutoff).
 *
 * Bug-blitz (c) — the rubric editor now exposes a `getErrors()` helper via
 * the `errorRef` prop so the parent's save handler can veto keyboard /
 * programmatic saves that bypass the disabled button.
 */
export default function RubricEditor({ rubric, setRubric, onSave, errorRef }) {
  // Bug #49 — client-side derivation of validity so the "Save rubric" button
  // stays disabled (and the user gets a clear inline error) when weights fall
  // outside the allowed range or don't sum to 1.0.
  const criteria = rubric.technical_criteria || [];
  const weightSum = criteria.reduce((s, c) => s + (Number(c.weight) || 0), 0);
  const weightSumOk = Math.abs(weightSum - 1) < 0.01;
  const badWeight = criteria.find((c) => (c.weight ?? 0) < 0 || (c.weight ?? 0) > 1);
  const commOk = rubric.commercial_weight >= 0 && rubric.commercial_weight <= 1;
  const minOk = rubric.minimum_technical >= 0 && rubric.minimum_technical <= 100;
  const errors = [];
  if (!weightSumOk) errors.push(`Weights must sum to 1.00 (currently ${weightSum.toFixed(2)}).`);
  if (badWeight) errors.push(`"${badWeight.label}" weight must be between 0 and 1.`);
  if (!commOk) errors.push("Commercial weight must be between 0 and 1.");
  if (!minOk) errors.push("Minimum technical cutoff must be between 0 and 100.");
  const canSave = errors.length === 0;
  // Publish the current error list to the parent (see prop docstring).
  if (errorRef) errorRef.current = errors;

  return (
    <div className="bg-white border p-4">
      <div className="pmc-label mb-2">Scoring Rubric</div>
      <table className="w-full text-sm">
        <thead className="text-xs text-brand-navy/60"><tr>
          <th className="text-left">Criterion</th><th>Weight</th><th>Max</th>
        </tr></thead>
        <tbody>
          {criteria.map((c, i) => (
            <tr key={c.code}>
              <td className="py-1">{c.label}</td>
              <td className="py-1 text-center">
                <input type="number" step="0.05" min="0" max="1" value={c.weight}
                  onChange={(e) => {
                    const arr = [...criteria];
                    arr[i] = { ...c, weight: Number(e.target.value) };
                    setRubric({ ...rubric, technical_criteria: arr });
                  }} className="w-20 border px-2 py-1" data-testid={`rubric-weight-${c.code}`} /></td>
              <td className="py-1 text-center">{c.max_score}</td>
            </tr>
          ))}
          <tr>
            <td className="py-1">Commercial weight (of combined)</td>
            <td className="py-1 text-center">
              <input type="number" step="0.05" min="0" max="1" value={rubric.commercial_weight}
                onChange={(e) => setRubric({ ...rubric, commercial_weight: Number(e.target.value) })}
                className="w-20 border px-2 py-1" data-testid="rubric-commercial-weight" /></td>
          </tr>
          <tr>
            <td className="py-1">Minimum technical cutoff (%)</td>
            <td className="py-1 text-center">
              <input type="number" min="0" max="100" value={rubric.minimum_technical}
                onChange={(e) => setRubric({ ...rubric, minimum_technical: Number(e.target.value) })}
                className="w-20 border px-2 py-1" data-testid="rubric-min-tech" /></td>
          </tr>
        </tbody>
      </table>
      {errors.length > 0 && (
        <ul className="mt-2 text-xs text-red-600 list-disc pl-5" data-testid="rubric-errors">
          {errors.map((e) => <li key={e}>{e}</li>)}
        </ul>
      )}
      <button onClick={onSave} disabled={!canSave} data-testid="save-rubric"
        className="mt-3 px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white disabled:opacity-40 disabled:cursor-not-allowed">
        Save rubric
      </button>
    </div>
  );
}
