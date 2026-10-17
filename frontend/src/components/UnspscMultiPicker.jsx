/** v52co — Multi-select UNSPSC picker for business verticals.
 *
 * Debounced live search against `/api/v1/masters/unspsc/public/search`
 * (the full 158k codeset with "biogas / solar plant / CBG / STP" synonym
 * expansion). Picks accumulate as removable chips; the parent receives a
 * flat array of `{code, title}` entries via `onChange`.
 */
import { useCallback, useEffect, useRef, useState } from "react";
import { taxonomyApi } from "@/lib/api";

export default function UnspscMultiPicker({ value = [], onChange, testidPrefix = "unspsc-multi" }) {
  const [q, setQ] = useState("");
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const timerRef = useRef(null);
  const rootRef = useRef(null);

  const doSearch = useCallback(async (query) => {
    if (!query || query.length < 2) { setRows([]); return; }
    setBusy(true);
    try {
      const d = await taxonomyApi.search(query);
      setRows(d.items || []);
    } catch { setRows([]); }
    finally { setBusy(false); }
  }, []);

  const onInput = (v) => {
    // v54e — a trailing comma commits the typed text as a custom chip,
    // so comma-separated entry works the way users expect.
    if (v.endsWith(",")) { addCustom(v); return; }
    setQ(v);
    setOpen(true);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(v), 220);
  };

  useEffect(() => {
    const h = (e) => { if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => document.removeEventListener("mousedown", h);
  }, []);

  const codes = new Set((value || []).map((v) => (typeof v === "string" ? v : v.code)));

  // v54e — free-text escape hatch: typing text followed by a comma (or
  // Enter with no highlighted result) adds it as a custom category chip.
  // The backend model accepts {code,title} dicts; legacy strings stay
  // readable too.
  const addCustom = (text) => {
    const t = String(text || "").replace(/,+$/, "").trim();
    if (t.length < 2) return;
    const dupe = (value || []).some((v) =>
      (typeof v === "string" ? v : v.title)?.toLowerCase() === t.toLowerCase());
    if (dupe) { setQ(""); setOpen(false); return; }
    onChange?.([...value, { code: `CUSTOM:${t.slice(0, 40)}`, title: t }]);
    setQ(""); setRows([]); setOpen(false);
  };

  const add = (row) => {
    if (codes.has(row.code)) return;
    const next = [...value, { code: row.code, title: row.title }];
    onChange?.(next);
    setQ(""); setRows([]); setOpen(false);
  };

  const remove = (code) => onChange?.(value.filter((v) => (typeof v === "string" ? v : v.code) !== code));

  return (
    <div ref={rootRef} className="relative" data-testid={`${testidPrefix}-picker`}>
      {value.length > 0 && (
        <div className="flex flex-wrap gap-1 mb-2" data-testid={`${testidPrefix}-chips`}>
          {value.map((v) => {
            const code = typeof v === "string" ? v : v.code;
            const title = typeof v === "string" ? v : v.title;
            return (
              <button type="button" key={code} onClick={() => remove(code)}
                      data-testid={`${testidPrefix}-chip-${code}`}
                      className="text-[11px] px-2 py-1 bg-emerald-100 text-emerald-900 hover:bg-red-100 hover:text-red-700 border border-emerald-200">
                <span className="font-mono mr-1 text-[9px] opacity-70">{code}</span>
                {title} ×
              </button>
            );
          })}
        </div>
      )}
      <input value={q}
             onChange={(e) => onInput(e.target.value)}
             onFocus={() => q.length >= 2 && setOpen(true)}
             onKeyDown={(e) => {
               if (e.key === "Enter") {
                 e.preventDefault();
                 if (rows[0]) add(rows[0]); else addCustom(q);
               }
             }}
             placeholder="Search UNSPSC — or type a category and press Enter / comma to add it…"
             data-testid={`${testidPrefix}-input`}
             className="w-full border border-brand-navy/20 px-3 py-2 text-sm" />
      {open && rows.length > 0 && (
        <div className="absolute z-30 mt-1 left-0 right-0 bg-white border border-brand-navy/20 shadow-lg max-h-72 overflow-y-auto"
             data-testid={`${testidPrefix}-dropdown`}>
          {rows.map((r) => {
            const already = codes.has(r.code);
            return (
              <button type="button" key={r.code}
                      // v54e — activate on mousedown (with preventDefault so
                      // the input keeps focus) instead of click: the debounced
                      // search re-render could swap the option node between
                      // mousedown and click, silently dropping the pick.
                      // add() already no-ops on duplicates, so the onClick
                      // backup can never double-add.
                      onMouseDown={(e) => { e.preventDefault(); add(r); }}
                      onClick={() => add(r)}
                      disabled={already}
                      data-testid={`${testidPrefix}-option-${r.code}`}
                      className={`block w-full text-left px-3 py-2 text-sm border-b border-brand-navy/5 last:border-0 ${already ? "bg-emerald-50 text-emerald-800 cursor-not-allowed" : "hover:bg-brand-navy/5"}`}>
                <div className="flex items-baseline justify-between gap-3">
                  <span className="font-mono text-[10px] text-brand-navy/60">{r.code}</span>
                  <span className="text-[10px] text-brand-navy/40 uppercase tracking-widest">
                    {already ? "added" : r.level || ""}
                  </span>
                </div>
                <div className="text-sm text-brand-navy">{r.title}</div>
              </button>
            );
          })}
        </div>
      )}
      {open && !busy && q.length >= 2 && rows.length === 0 && (
        <div className="absolute z-30 mt-1 left-0 right-0 bg-white border border-brand-navy/20 shadow-lg p-3 text-xs text-brand-navy/60">
          No UNSPSC match for “{q}” — press Enter or type a trailing comma to
          add it as a custom category.
        </div>
      )}
    </div>
  );
}
