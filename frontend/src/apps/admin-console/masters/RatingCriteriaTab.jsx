import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { tenderProApi, showApiError } from "@/lib/api";

/**
 * v45 · Phase D — Rating Criteria master editor (sub-tab of Masters).
 * Admins compose reusable rating rubrics (15-30 criteria, per-criterion
 * weight and 1-N scale). One set can be marked default; the backend
 * enforces single-default. Country/industry scoping is optional.
 */
export default function RatingCriteriaTab() {
  const [sets, setSets]     = useState([]);
  const [busy, setBusy]     = useState(false);
  const [editing, setEditing] = useState(null); // full row being edited (null = create form)
  const [draft, setDraft]   = useState(blankDraft());

  function blankDraft() {
    return {
      name: "", country: "", industry: "",
      is_default: false, is_active: true,
      criteria: [{ code: "delivery", label: "Delivery timeliness", weight: 2, scale_min: 1, scale_max: 5 }],
    };
  }

  const load = useCallback(async () => {
    try { setSets(await tenderProApi.listCriteriaSets()); }
    catch (e) { showApiError(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const patchCriterion = (idx, p) => {
    const arr = [...draft.criteria];
    arr[idx] = { ...arr[idx], ...p };
    setDraft({ ...draft, criteria: arr });
  };
  const addCriterion = () => setDraft({
    ...draft,
    criteria: [...draft.criteria, { code: "", label: "", weight: 1, scale_min: 1, scale_max: 5 }],
  });
  const rmCriterion = (idx) => {
    if (draft.criteria.length <= 1) return toast.error("Keep at least one criterion");
    const arr = [...draft.criteria]; arr.splice(idx, 1);
    setDraft({ ...draft, criteria: arr });
  };

  const startEdit = (row) => {
    setEditing(row);
    setDraft({
      name: row.name || "", country: row.country || "", industry: row.industry || "",
      is_default: !!row.is_default, is_active: row.is_active !== false,
      criteria: (row.criteria || []).map((c) => ({ ...c })),
    });
  };
  const cancelEdit = () => { setEditing(null); setDraft(blankDraft()); };

  const save = async () => {
    if (!draft.name.trim()) return toast.error("Set name is required");
    if (draft.criteria.some((c) => !c.code.trim() || !c.label.trim())) {
      return toast.error("Every criterion needs both code and label");
    }
    if (draft.criteria.length > 30) return toast.error("Max 30 criteria per set");
    setBusy(true);
    try {
      if (editing) {
        await tenderProApi.updateCriteriaSet(editing.id, draft);
        toast.success("Criteria set updated");
      } else {
        await tenderProApi.createCriteriaSet(draft);
        toast.success("Criteria set created");
      }
      cancelEdit();
      await load();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const remove = async (row) => {
    if (!confirm(`Delete "${row.name}"?`)) return;
    try { await tenderProApi.deleteCriteriaSet(row.id); toast.success("Deleted"); await load(); }
    catch (e) { showApiError(e); }
  };

  return (
    <div data-testid="masters-rating-criteria-tab">
      {/* Editor */}
      <div className="bg-white border p-5 mb-4">
        <div className="flex items-baseline justify-between mb-3">
          <strong className="text-brand-navy">
            {editing ? `Edit · ${editing.name}` : "New rating criteria set"}
          </strong>
          {editing && (
            <button onClick={cancelEdit} className="text-xs text-brand-navy/60 hover:underline"
                    data-testid="rc-cancel-edit">Cancel edit</button>
          )}
        </div>
        <div className="grid gap-3 md:grid-cols-4 mb-3">
          <label className="col-span-2 text-xs uppercase tracking-widest text-brand-navy/60">
            Set name
            <input value={draft.name} onChange={(e) => setDraft({ ...draft, name: e.target.value })}
                   data-testid="rc-name"
                   placeholder="e.g. Public Works vendor rating"
                   className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Country (opt)
            <input value={draft.country} onChange={(e) => setDraft({ ...draft, country: e.target.value.toUpperCase() })}
                   data-testid="rc-country" maxLength={3}
                   placeholder="KZ · IN · GB…"
                   className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
          </label>
          <label className="text-xs uppercase tracking-widest text-brand-navy/60">
            Industry (opt)
            <input value={draft.industry} onChange={(e) => setDraft({ ...draft, industry: e.target.value })}
                   data-testid="rc-industry"
                   placeholder="Public Works · Software…"
                   className="mt-1 w-full px-3 py-2 border normal-case tracking-normal" />
          </label>
        </div>
        <div className="flex gap-4 mb-4 text-xs">
          <label className="flex items-center gap-2 text-brand-navy/70">
            <input type="checkbox" checked={draft.is_default}
                   onChange={(e) => setDraft({ ...draft, is_default: e.target.checked })}
                   data-testid="rc-default" />
            Make default (unsets other defaults)
          </label>
          <label className="flex items-center gap-2 text-brand-navy/70">
            <input type="checkbox" checked={draft.is_active}
                   onChange={(e) => setDraft({ ...draft, is_active: e.target.checked })}
                   data-testid="rc-active" />
            Active
          </label>
        </div>

        <div className="text-xs uppercase tracking-widest text-brand-navy/70 mb-2">
          Criteria ({draft.criteria.length}/30)
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr className="text-xs uppercase tracking-widest text-brand-navy/50 border-b">
              <th className="text-left px-2 py-1 w-32">Code</th>
              <th className="text-left px-2 py-1">Label</th>
              <th className="text-right px-2 py-1 w-24">Weight</th>
              <th className="text-right px-2 py-1 w-20">Min</th>
              <th className="text-right px-2 py-1 w-20">Max</th>
              <th className="w-10" />
            </tr>
          </thead>
          <tbody>
            {draft.criteria.map((c, i) => (
              <tr key={i} className="border-b border-brand-navy/10" data-testid={`rc-row-${i}`}>
                <td className="px-2 py-1">
                  <input value={c.code} onChange={(e) => patchCriterion(i, { code: e.target.value })}
                         data-testid={`rc-code-${i}`}
                         className="w-full px-2 py-1 border" />
                </td>
                <td className="px-2 py-1">
                  <input value={c.label} onChange={(e) => patchCriterion(i, { label: e.target.value })}
                         data-testid={`rc-label-${i}`}
                         className="w-full px-2 py-1 border" />
                </td>
                <td className="px-2 py-1">
                  <input type="number" step="0.1" value={c.weight}
                         onChange={(e) => patchCriterion(i, { weight: parseFloat(e.target.value) || 0 })}
                         data-testid={`rc-weight-${i}`}
                         className="w-full px-2 py-1 border text-right" />
                </td>
                <td className="px-2 py-1">
                  <input type="number" value={c.scale_min}
                         onChange={(e) => patchCriterion(i, { scale_min: parseInt(e.target.value, 10) || 1 })}
                         className="w-full px-2 py-1 border text-right" />
                </td>
                <td className="px-2 py-1">
                  <input type="number" value={c.scale_max}
                         onChange={(e) => patchCriterion(i, { scale_max: parseInt(e.target.value, 10) || 5 })}
                         className="w-full px-2 py-1 border text-right" />
                </td>
                <td className="px-2 py-1 text-center">
                  <button onClick={() => rmCriterion(i)}
                          data-testid={`rc-del-${i}`}
                          className="text-red-600 text-xs">×</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
        <button onClick={addCriterion} disabled={draft.criteria.length >= 30}
                data-testid="rc-add-criterion"
                className="mt-3 px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5 disabled:opacity-40">
          + Add criterion
        </button>
        <div className="mt-4 flex justify-end">
          <button onClick={save} disabled={busy}
                  data-testid="rc-save"
                  className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
            {busy ? "Saving…" : editing ? "Update set" : "Create set"}
          </button>
        </div>
      </div>

      {/* List */}
      <div className="bg-white border">
        <div className="pmc-label p-3 border-b flex justify-between">
          <span>Saved criteria sets</span>
          <span className="text-brand-navy/40 normal-case tracking-normal">{sets.length}</span>
        </div>
        {sets.map((s) => (
          <div key={s.id} className="border-b p-3 text-sm flex items-center gap-3 flex-wrap"
               data-testid={`rc-list-${s.id}`}>
            <strong className="text-brand-navy">{s.name}</strong>
            {s.is_default && <span className="text-[10px] uppercase tracking-widest bg-emerald-100 text-emerald-800 px-2 py-0.5">Default</span>}
            {s.country && <span className="text-xs text-brand-navy/60">{s.country}</span>}
            {s.industry && <span className="text-xs text-brand-navy/60">{s.industry}</span>}
            <span className="text-xs text-brand-navy/50 ml-auto">{(s.criteria || []).length} criteria</span>
            <button onClick={() => startEdit(s)}
                    data-testid={`rc-edit-${s.id}`}
                    className="text-xs px-2 py-1 border border-brand-navy/30 hover:bg-brand-navy/5">Edit</button>
            <button onClick={() => remove(s)}
                    data-testid={`rc-delete-${s.id}`}
                    className="text-xs px-2 py-1 border border-red-500 text-red-600 hover:bg-red-50">Delete</button>
          </div>
        ))}
        {sets.length === 0 && (
          <div className="p-6 text-sm text-brand-navy/50">
            No criteria sets yet — compose one above.
          </div>
        )}
      </div>
    </div>
  );
}
