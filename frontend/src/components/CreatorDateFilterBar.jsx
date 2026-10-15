/**
 * v52v — Shared "Created by + from + to" filter bar for admin list panels.
 *
 * - Native <input type="date"> with min/max guards (`from.max = to`,
 *   `to.min = from`) so an invalid range is physically unpickable.
 * - "Created by" is a free-text/email contains filter; the shape of
 *   `created_by_email` fields across panels is heterogenous so we match on
 *   substring (case-insensitive).
 * - Returns a predicate via the `onChange` callback (consumers filter their
 *   already-fetched rows client-side with a `useMemo`).
 * - Panels can also pass `creators` (list of distinct emails) and the bar
 *   turns the input into a datalist for quick picking.
 *
 * Usage:
 *   const [filters, setFilters] = useState({ createdBy: "", from: "", to: "" });
 *   const visible = useMemo(
 *     () => rows.filter(matchCreatorDate(filters)),
 *     [rows, filters]);
 *   <CreatorDateFilterBar value={filters} onChange={setFilters}
 *                         creators={distinctCreators} testid="xxx-filter" />
 */

export function matchCreatorDate({ createdBy, from, to }) {
  const needle = (createdBy || "").trim().toLowerCase();
  const fromMs = from ? new Date(`${from}T00:00:00`).getTime() : null;
  const toMs = to ? new Date(`${to}T23:59:59.999`).getTime() : null;
  return (row) => {
    if (needle) {
      const haystack = String(
        row.created_by_email || row.created_by || row.creator_email ||
        row.actor || row.actor_email || row.email || "",
      ).toLowerCase();
      if (!haystack.includes(needle)) return false;
    }
    if (fromMs || toMs) {
      const raw = row.created_at || row.createdAt || row.ts || row.timestamp;
      if (!raw) return false;
      const t = new Date(raw).getTime();
      if (Number.isNaN(t)) return false;
      if (fromMs && t < fromMs) return false;
      if (toMs && t > toMs) return false;
    }
    return true;
  };
}

export default function CreatorDateFilterBar({ value, onChange, creators, testid = "cdf-bar" }) {
  const v = value || { createdBy: "", from: "", to: "" };
  const set = (patch) => onChange({ ...v, ...patch });
  const uniqCreators = Array.from(new Set((creators || []).filter(Boolean))).slice(0, 500);
  const dlId = `${testid}-datalist`;
  return (
    <div className="flex flex-wrap items-end gap-2 mb-3" data-testid={testid}>
      <label className="flex flex-col text-[11px] uppercase tracking-widest text-brand-navy/60">
        Created by
        <input list={uniqCreators.length ? dlId : undefined}
          value={v.createdBy}
          onChange={(e) => set({ createdBy: e.target.value })}
          placeholder="email contains…"
          data-testid={`${testid}-by`}
          className="mt-1 px-2 py-1 border border-brand-navy/20 text-sm bg-white min-w-[200px]" />
      </label>
      {uniqCreators.length > 0 && (
        <datalist id={dlId}>
          {uniqCreators.map((c) => <option key={c} value={c} />)}
        </datalist>
      )}
      <label className="flex flex-col text-[11px] uppercase tracking-widest text-brand-navy/60">
        Created from
        <input type="date" value={v.from} max={v.to || undefined}
          onChange={(e) => set({ from: e.target.value })}
          data-testid={`${testid}-from`}
          className="mt-1 px-2 py-1 border border-brand-navy/20 text-sm bg-white" />
      </label>
      <label className="flex flex-col text-[11px] uppercase tracking-widest text-brand-navy/60">
        Created to
        <input type="date" value={v.to} min={v.from || undefined}
          onChange={(e) => set({ to: e.target.value })}
          data-testid={`${testid}-to`}
          className="mt-1 px-2 py-1 border border-brand-navy/20 text-sm bg-white" />
      </label>
      {(v.createdBy || v.from || v.to) && (
        <button type="button"
          onClick={() => onChange({ createdBy: "", from: "", to: "" })}
          data-testid={`${testid}-clear`}
          className="px-2 py-1 text-[10px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy hover:text-white">
          Clear
        </button>
      )}
    </div>
  );
}
