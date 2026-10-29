import { useState } from "react";

export const CategoryPicker = ({ categories, value, onChange }) => {
  const [q, setQ] = useState("");
  const shown = categories.filter((c) => c.name?.toLowerCase().includes(q.toLowerCase())).slice(0, 200);
  const toggle = (n) => onChange(value.includes(n) ? value.filter((x) => x !== n) : [...value, n]);
  return (
    <div data-testid="emd-category-picker" className="border border-brand-navy/20 bg-white">
      <div className="flex gap-2 items-center p-2 border-b border-brand-navy/10">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search categories…"
               data-testid="emd-category-search" className="flex-1 px-2 py-1 border border-brand-navy/20 text-sm" />
        <span className="text-xs text-brand-navy/60" data-testid="emd-category-count">{value.length} selected</span>
      </div>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1 p-2 border-b border-brand-navy/10">
          {value.map((n) => (
            <button key={n} type="button" onClick={() => toggle(n)} data-testid={`emd-category-chip-${n}`}
                    className="text-[11px] px-2 py-0.5 bg-brand-navy text-white">{n} ✕</button>
          ))}
        </div>
      )}
      <div className="max-h-48 overflow-y-auto p-2 grid gap-1 md:grid-cols-2">
        {shown.map((c) => (
          <label key={c.id || c.code || c.name} className="text-sm flex items-center gap-2">
            <input type="checkbox" checked={value.includes(c.name)} onChange={() => toggle(c.name)}
                   data-testid={`emd-category-opt-${c.code || c.name}`} /> {c.name}
          </label>
        ))}
      </div>
    </div>
  );
};
