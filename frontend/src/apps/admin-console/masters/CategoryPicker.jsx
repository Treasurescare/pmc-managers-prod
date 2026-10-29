import { useState } from "react";

// Searchable checkbox list. `items` = [{ value, name }]; `extra` = values to flag as "new".
export const CheckPicker = ({ items, value, onChange, prefix, placeholder, extra = [] }) => {
  const [q, setQ] = useState("");
  const shown = items.filter((c) => c.name?.toLowerCase().includes(q.toLowerCase())).slice(0, 300);
  const toggle = (n) => onChange(value.includes(n) ? value.filter((x) => x !== n) : [...value, n]);
  const nameOf = (v) => items.find((c) => c.value === v)?.name || v;
  return (
    <div data-testid={`${prefix}-picker`} className="border border-brand-navy/20 bg-white">
      <div className="flex gap-2 items-center p-2 border-b border-brand-navy/10">
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={placeholder}
               data-testid={`${prefix}-search`} className="flex-1 px-2 py-1 border border-brand-navy/20 text-sm" />
        <span className="text-xs text-brand-navy/60" data-testid={`${prefix}-count`}>{value.length} selected</span>
      </div>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1 p-2 border-b border-brand-navy/10">
          {value.map((n) => (
            <button key={n} type="button" onClick={() => toggle(n)} data-testid={`${prefix}-chip-${n}`}
                    className={"text-[11px] px-2 py-0.5 text-white " + (extra.includes(n) ? "bg-amber-600" : "bg-brand-navy")}>
              {nameOf(n)}{extra.includes(n) ? " (new)" : ""} ✕</button>
          ))}
        </div>
      )}
      <div className="max-h-48 overflow-y-auto p-2 grid gap-1 md:grid-cols-2">
        {shown.map((c) => (
          <label key={c.value} className="text-sm flex items-center gap-2">
            <input type="checkbox" checked={value.includes(c.value)} onChange={() => toggle(c.value)}
                   data-testid={`${prefix}-opt-${c.value}`} /> {c.name}
          </label>
        ))}
      </div>
    </div>
  );
};

export const CategoryPicker = ({ categories, value, onChange, extra }) => (
  <CheckPicker items={categories.map((c) => ({ value: c.name, name: c.name }))} value={value} onChange={onChange}
               prefix="emd-category" placeholder="Search categories…" extra={extra} />
);
