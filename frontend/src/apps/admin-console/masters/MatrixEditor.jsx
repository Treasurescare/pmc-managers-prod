const ROLE_LABELS = {
  admin: "Admin", reviewer: "Reviewer", escrow_agent: "Escrow Agent",
  certifier: "Certifier", legal_counsel: "Legal Counsel",
  accounting: "Accounting", committee_member: "Committee Member",
  auditor: "Auditor", support: "Support",
};

/**
 * MatrixEditor — extracted from MastersPanel. Renders the row-by-row
 * approval-matrix editor: role, action, SLA, move up/down, delete + add.
 */
export default function MatrixEditor({ matrixDraft, setMatrixDraft, matrices, onSave }) {
  return (
    <>
      <div className="bg-white border p-4 mb-4" data-testid="matrix-editor">
        <div className="flex gap-2 mb-3">
          <input value={matrixDraft.name}
            onChange={(e) => setMatrixDraft({ ...matrixDraft, name: e.target.value })}
            className="flex-1 px-3 py-2 border" placeholder="Matrix name" />
          <button onClick={onSave} data-testid="matrix-save"
            className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white">
            Save matrix
          </button>
        </div>
        <table className="w-full text-sm">
          <thead className="text-xs text-brand-navy/60">
            <tr><th className="text-left">#</th><th className="text-left">Role</th>
              <th className="text-left">Action</th><th className="text-right">SLA (h)</th>
              <th className="text-center">Move</th><th className="text-center">Del</th></tr>
          </thead>
          <tbody>
            {matrixDraft.steps.map((s, i) => (
              <tr key={`step-${s.role_code}-${s.order ?? i}`} className="border-t" data-testid={`matrix-step-${i}`}>
                <td className="py-1">{s.order}</td>
                <td className="py-1">
                  <select value={s.role_code}
                    onChange={(e) => {
                      const arr = [...matrixDraft.steps];
                      arr[i] = { ...s, role_code: e.target.value };
                      setMatrixDraft({ ...matrixDraft, steps: arr });
                    }}
                    className="border px-2 py-1 text-xs w-full"
                    data-testid={`matrix-role-${i}`}>
                    {Object.entries(ROLE_LABELS).map(([r, l]) =>
                      <option key={r} value={r}>{l}</option>)}
                  </select>
                </td>
                <td className="py-1">
                  <input value={s.action_label}
                    onChange={(e) => {
                      const arr = [...matrixDraft.steps];
                      arr[i] = { ...s, action_label: e.target.value };
                      setMatrixDraft({ ...matrixDraft, steps: arr });
                    }}
                    className="w-full border px-2 py-1 text-xs"
                    data-testid={`matrix-action-${i}`} />
                </td>
                <td className="py-1 text-right">
                  <input type="number" min="1" value={s.sla_hours}
                    onChange={(e) => {
                      const arr = [...matrixDraft.steps];
                      arr[i] = { ...s, sla_hours: Number(e.target.value) };
                      setMatrixDraft({ ...matrixDraft, steps: arr });
                    }}
                    className="w-20 border px-2 py-0.5 text-right" />
                </td>
                <td className="py-1 text-center">
                  <button type="button" disabled={i === 0}
                    onClick={() => {
                      const arr = [...matrixDraft.steps];
                      [arr[i - 1], arr[i]] = [arr[i], arr[i - 1]];
                      arr.forEach((x, idx) => { x.order = idx + 1; });
                      setMatrixDraft({ ...matrixDraft, steps: arr });
                    }}
                    className="text-xs px-1 disabled:opacity-30"
                    data-testid={`matrix-up-${i}`}>↑</button>
                  <button type="button" disabled={i === matrixDraft.steps.length - 1}
                    onClick={() => {
                      const arr = [...matrixDraft.steps];
                      [arr[i], arr[i + 1]] = [arr[i + 1], arr[i]];
                      arr.forEach((x, idx) => { x.order = idx + 1; });
                      setMatrixDraft({ ...matrixDraft, steps: arr });
                    }}
                    className="text-xs px-1 disabled:opacity-30"
                    data-testid={`matrix-down-${i}`}>↓</button>
                </td>
                <td className="py-1 text-center">
                  <button type="button"
                    onClick={() => {
                      const arr = matrixDraft.steps.filter((_, idx) => idx !== i);
                      arr.forEach((x, idx) => { x.order = idx + 1; });
                      setMatrixDraft({ ...matrixDraft, steps: arr });
                    }}
                    className="text-xs text-red-600 hover:underline"
                    data-testid={`matrix-del-${i}`}>×</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button type="button"
          onClick={() => {
            const nextOrder = matrixDraft.steps.length + 1;
            setMatrixDraft({ ...matrixDraft,
              steps: [...matrixDraft.steps, {
                order: nextOrder, role_code: "reviewer",
                action_label: "Review step", sla_hours: 24, required: true,
              }] });
          }}
          className="mt-3 px-3 py-1.5 text-xs border border-dashed border-brand-navy/30 hover:bg-slate-50"
          data-testid="matrix-add-step">+ Add step</button>
      </div>
      <div className="bg-white border">
        <div className="pmc-label p-3 border-b">Saved matrices</div>
        {matrices.map((m) => (
          <div key={m.id} className="border-b p-3 text-sm" data-testid={`matrix-row-${m.name}`}>
            <strong>{m.name}</strong> · {m.steps?.length} steps · applies to {m.applies_to}
          </div>
        ))}
        {matrices.length === 0 && <div className="p-6 text-sm text-slate-500">No matrices saved yet.</div>}
      </div>
    </>
  );
}
