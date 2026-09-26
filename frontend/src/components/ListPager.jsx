import { useMemo, useState } from "react";

/**
 * v47f — Reusable pagination widget.
 * Usage:
 *   const { paged, controls } = useListPager(items);
 *   return <>{paged.map(...)} {controls}</>;
 * Provides a "show N" chooser (10 / 20 / 30 / All) and prev/next.
 */
export function useListPager(items, { defaultSize = 20, testid = "list-pager" } = {}) {
  const [size, setSize] = useState(defaultSize);
  const [page, setPage] = useState(1);
  const total = items?.length || 0;
  const pageCount = size === "all" ? 1 : Math.max(1, Math.ceil(total / Math.max(1, size)));
  const safePage = Math.min(page, pageCount);
  const paged = useMemo(() => {
    if (size === "all") return items || [];
    const s = Math.max(1, parseInt(size, 10));
    return (items || []).slice((safePage - 1) * s, safePage * s);
  }, [items, size, safePage]);
  const controls = (
    <div className="flex flex-wrap items-center gap-2 p-2 bg-slate-50 border-t"
         data-testid={testid}>
      <span className="text-xs text-slate-600 uppercase tracking-widest">Show</span>
      {[10, 20, 30, "all"].map((n) => (
        <button key={n}
          onClick={() => { setSize(n); setPage(1); }}
          data-testid={`${testid}-size-${n}`}
          className={`px-2 py-1 text-xs border ${size === n ? "bg-slate-800 text-white" : "bg-white hover:bg-slate-100"}`}>
          {n === "all" ? "All" : n}
        </button>
      ))}
      <span className="ml-auto text-xs text-slate-600">
        {total === 0 ? "no items" : size === "all"
          ? `${total} shown`
          : `${(safePage - 1) * size + 1}–${Math.min(safePage * size, total)} of ${total}`}
      </span>
      {size !== "all" && pageCount > 1 && (
        <>
          <button onClick={() => setPage(Math.max(1, safePage - 1))}
            disabled={safePage <= 1}
            data-testid={`${testid}-prev`}
            className="px-2 py-1 text-xs border bg-white hover:bg-slate-100 disabled:opacity-40">Prev</button>
          <span className="text-xs">{safePage} / {pageCount}</span>
          <button onClick={() => setPage(Math.min(pageCount, safePage + 1))}
            disabled={safePage >= pageCount}
            data-testid={`${testid}-next`}
            className="px-2 py-1 text-xs border bg-white hover:bg-slate-100 disabled:opacity-40">Next</button>
        </>
      )}
    </div>
  );
  return { paged, controls, size, page: safePage };
}
