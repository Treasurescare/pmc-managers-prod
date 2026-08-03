/**
 * RubricEditor — extracted from EvaluationPanel. Renders the scoring rubric
 * (technical criteria weights + commercial weight + minimum cutoff).
 */
export default function RubricEditor({ rubric, setRubric, onSave }) {
  return (
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
      <button onClick={onSave} data-testid="save-rubric"
        className="mt-3 px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy-soft text-white">
        Save rubric
      </button>
    </div>
  );
}
