/** Wave 44 — UNSPSC picker.
 *
 * Small dependency-free autocomplete backed by `/api/v1/taxonomy/search`.
 * Renders as a labelled input; on selection sets both `code` and `title`
 * via the parent-supplied `onChange({code, title})` callback. */
import { useCallback, useEffect, useRef, useState } from "react";

const API = process.env.REACT_APP_BACKEND_URL;

export default function UnspscPicker({ value, title, onChange, testidPrefix = "unspsc" }) {
  const [q, setQ] = useState(title || "");
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(false);
  const [busy, setBusy] = useState(false);
  const timerRef = useRef(null);
  const rootRef = useRef(null);

  useEffect(() => {
    setQ(title || "");
  }, [title]);

  const doSearch = useCallback(async (query) => {
    if (!query || query.length < 2) { setRows([]); return; }
    setBusy(true);
    try {
      const r = await fetch(`${API}/api/v1/taxonomy/search?q=${encodeURIComponent(query)}&limit=15`);
      if (r.ok) {
        const d = await r.json();
        setRows(d.items || []);
      }
    } catch {
      setRows([]);
    } finally {
      setBusy(false);
    }
  }, []);

  const onInput = (v) => {
    setQ(v);
    setOpen(true);
    if (timerRef.current) clearTimeout(timerRef.current);
    timerRef.current = setTimeout(() => doSearch(v), 220);
  };

  // Close dropdown on outside click.
  useEffect(() => {
    const handler = (e) => {
      if (rootRef.current && !rootRef.current.contains(e.target)) setOpen(false);
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, []);

  const pick = (row) => {
    setQ(row.title);
    setOpen(false);
    onChange?.({ code: row.code, title: row.title });
  };

  const clear = () => {
    setQ("");
    setRows([]);
    onChange?.({ code: "", title: "" });
  };

  return (
    <div ref={rootRef} className="relative" data-testid={`${testidPrefix}-picker`}>
      <div className="flex gap-2">
        <input value={q}
               onChange={(e) => onInput(e.target.value)}
               onFocus={() => q.length >= 2 && setOpen(true)}
               placeholder="Search UNSPSC (e.g. 'concrete', 'medical')…"
               data-testid={`${testidPrefix}-input`}
               className="flex-1 border border-brand-navy/20 px-3 py-2 text-sm" />
        {value && (
          <button type="button" onClick={clear}
                  data-testid={`${testidPrefix}-clear`}
                  className="text-[10px] uppercase tracking-widest px-2 border border-brand-navy/20 text-brand-navy/70 hover:bg-brand-navy/5">
            Clear
          </button>
        )}
      </div>
      {value && (
        <div className="text-[10px] mt-1 text-brand-navy/60 font-mono" data-testid={`${testidPrefix}-value`}>
          UNSPSC: {value} · {title}
        </div>
      )}
      {open && rows.length > 0 && (
        <div className="absolute z-30 mt-1 left-0 right-0 bg-white border border-brand-navy/20 shadow-lg max-h-64 overflow-y-auto"
             data-testid={`${testidPrefix}-dropdown`}>
          {rows.map((r) => (
            <button type="button" key={r.code} onClick={() => pick(r)}
                    data-testid={`${testidPrefix}-option-${r.code}`}
                    className="block w-full text-left px-3 py-2 text-sm hover:bg-brand-navy/5 border-b border-brand-navy/5 last:border-0">
              <div className="flex items-baseline justify-between gap-3">
                <span className="font-mono text-[10px] text-brand-navy/60">{r.code}</span>
                <span className="text-[10px] text-brand-navy/40 uppercase tracking-widest">{r.level || ""}</span>
              </div>
              <div className="text-sm text-brand-navy">{r.title}</div>
            </button>
          ))}
        </div>
      )}
      {open && !busy && q.length >= 2 && rows.length === 0 && (
        <div className="absolute z-30 mt-1 left-0 right-0 bg-white border border-brand-navy/20 shadow-lg p-3 text-xs text-brand-navy/60">
          No UNSPSC nodes match "{q}"
        </div>
      )}
    </div>
  );
}
