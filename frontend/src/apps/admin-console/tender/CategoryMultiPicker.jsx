/**
 * v52p — Multi-select category chip picker for Tender Builder.
 *
 * Behaviour the user asked for:
 *   • AI/PDF extraction places its guess as the first chip.
 *   • Admin can pick more categories from the master dropdown.
 *   • Admin can also type a free-text category (editable + addable).
 *   • Primary category (first chip) is written back to `product_category`
 *     so every downstream flow (notice create, matching, filtering) that
 *     reads a single string keeps working.
 *   • Full list is written back to `product_categories` for anything that
 *     wants the complete tagging.
 */
import { useEffect, useMemo, useState } from "react";
import { mastersApi } from "@/lib/api";

const splitPrimary = (primary, list) => {
  const raw = Array.isArray(list) && list.length
    ? list
    : String(primary || "").split(/[,;]+/).map((s) => s.trim()).filter(Boolean);
  // Preserve order, de-duplicate case-insensitively.
  const seen = new Set();
  const out = [];
  for (const v of raw) {
    const k = v.toLowerCase();
    if (seen.has(k)) continue;
    seen.add(k); out.push(v);
  }
  return out;
};

export default function CategoryMultiPicker({ primary, list, onChange, testid = "th-prod-cat-multi" }) {
  const chips = useMemo(() => splitPrimary(primary, list), [primary, list]);
  const [master, setMaster] = useState([]);
  const [typed, setTyped] = useState("");

  useEffect(() => {
    mastersApi.listCategoriesPublic()
      .then((rows) => setMaster(
        (Array.isArray(rows) ? rows : [])
          .map((c) => String(c.name || c.title || c.code || ""))
          .filter(Boolean)
          .sort((a, b) => a.localeCompare(b))))
      .catch(() => setMaster([]));
  }, []);

  const emit = (next) => {
    onChange({
      product_category: next[0] || "",
      product_categories: next,
    });
  };

  const add = (value) => {
    const v = String(value || "").trim();
    if (!v) return;
    if (chips.some((c) => c.toLowerCase() === v.toLowerCase())) return;
    emit([...chips, v]);
    setTyped("");
  };

  const remove = (idx) => {
    const next = chips.filter((_, i) => i !== idx);
    emit(next);
  };

  const makePrimary = (idx) => {
    if (idx === 0) return;
    const next = [chips[idx], ...chips.filter((_, i) => i !== idx)];
    emit(next);
  };

  const unused = useMemo(
    () => master.filter((m) => !chips.some((c) => c.toLowerCase() === m.toLowerCase())),
    [master, chips],
  );

  return (
    <div data-testid={testid} className="space-y-2">
      {/* Chips row */}
      <div className="flex flex-wrap gap-1.5">
        {chips.length === 0 && (
          <span className="text-xs text-brand-navy/50 italic">No categories yet — pick one from the dropdown or type to add.</span>
        )}
        {chips.map((c, i) => (
          <span key={`${c}-${i}`}
            data-testid={`th-prod-cat-chip-${i}`}
            className={"inline-flex items-center gap-1 pl-2 pr-1 py-0.5 text-xs border " +
              (i === 0
                ? "bg-brand-navy text-white border-brand-navy"
                : "bg-white text-brand-navy border-brand-navy/40")}>
            {i === 0 && <span className="text-[9px] uppercase tracking-widest mr-1 opacity-70">primary</span>}
            {i !== 0 && (
              <button type="button" onClick={() => makePrimary(i)}
                title="Set as primary category"
                data-testid={`th-prod-cat-primary-${i}`}
                className="text-[9px] uppercase tracking-widest text-brand-navy/50 hover:text-brand-navy">
                ★
              </button>
            )}
            {c}
            <button type="button" onClick={() => remove(i)}
              title="Remove"
              data-testid={`th-prod-cat-remove-${i}`}
              className={"ml-1 w-4 h-4 inline-flex items-center justify-center text-[11px] " +
                (i === 0 ? "text-white/80 hover:text-white" : "text-brand-navy/60 hover:text-brand-navy")}>
              ×
            </button>
          </span>
        ))}
      </div>
      {/* Add from master OR type */}
      <div className="flex flex-wrap gap-2">
        <select value=""
          data-testid="th-prod-cat-select"
          onChange={(e) => { if (e.target.value) add(e.target.value); e.target.value = ""; }}
          className="px-2 py-1.5 border border-brand-navy/20 bg-white text-sm">
          <option value="">+ From category master…</option>
          {unused.map((m) => <option key={m} value={m}>{m}</option>)}
        </select>
        <input value={typed}
          data-testid="th-prod-cat-typed"
          onChange={(e) => setTyped(e.target.value)}
          onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(typed); } }}
          placeholder="Or type a category and press Enter"
          className="flex-1 min-w-[180px] px-2 py-1.5 border border-brand-navy/20 bg-white text-sm" />
        {typed.trim() && (
          <button type="button" onClick={() => add(typed)}
            data-testid="th-prod-cat-add-typed"
            className="px-3 py-1.5 text-[11px] uppercase tracking-widest border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white">
            Add
          </button>
        )}
      </div>
    </div>
  );
}
