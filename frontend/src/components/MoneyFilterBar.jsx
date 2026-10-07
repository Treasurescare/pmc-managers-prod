import { useEffect, useMemo, useRef, useState } from "react";

/**
 * MoneyFilterBar — reusable client-side filter for every Money & compliance
 * list panel (Reverse auctions, Awards, Billing, Evaluation, L1 comparison,
 * Escrow/EMD, DocuSign, Bidding ops). Introduced in v51ab after user feedback
 * that these panels had non-working search filters.
 *
 * Two modes:
 *
 * 1. Controlled mode — pass `onChange(filter)` and run the predicate yourself
 *    against your row array. Use this for state-driven lists (e.g. Reverse
 *    auctions) where you have the raw records in React state.
 *
 * 2. DOM-filter mode — pass `scopeSelector="selector-for-row-container"` and
 *    the component hides rows whose combined text doesn't match. Works for
 *    legacy panels that render rows directly without a React state array.
 */
export default function MoneyFilterBar({
  statusOptions = [],
  onChange,
  scopeSelector,
  rowSelector = "[data-row], tr[data-row], .pmc-row, .bo-r",
  showExpiring = true,
  showCreator = true,
  testid = "money-filter-bar",
}) {
  const [q, setQ] = useState("");
  const [creator, setCreator] = useState("");
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");
  const [expiringFrom, setExpiringFrom] = useState("");
  const [expiringTo, setExpiringTo] = useState("");
  const [status, setStatus] = useState("");

  const filter = useMemo(() => ({
    q: q.trim(), creator: creator.trim(),
    createdFrom, createdTo, expiringFrom, expiringTo, status,
  }), [q, creator, createdFrom, createdTo, expiringFrom, expiringTo, status]);

  const onChangeRef = useRef(onChange);
  useEffect(() => { onChangeRef.current = onChange; }, [onChange]);
  useEffect(() => { onChangeRef.current && onChangeRef.current(filter); }, [filter]);

  // DOM mode: hide rows that don't match. Reads optional data-attributes on
  // each row for date comparison; falls back to text match if attrs absent.
  useEffect(() => {
    if (!scopeSelector) return;
    const scope = document.querySelector(scopeSelector);
    if (!scope) return;
    const paint = () => {
      const rows = scope.querySelectorAll(rowSelector);
      const qLc = filter.q.toLowerCase();
      const crLc = filter.creator.toLowerCase();
      rows.forEach((r) => {
        const text = r.textContent.toLowerCase();
        const createdAt = r.dataset.createdAt || r.getAttribute("data-created-at") || "";
        const expiresAt = r.dataset.expiresAt || r.getAttribute("data-expires-at") || "";
        const rowStatus = (r.dataset.status || r.getAttribute("data-status") || "").toLowerCase();
        const rowCreator = (r.dataset.creator || r.getAttribute("data-creator") || "").toLowerCase();
        let ok = true;
        if (qLc && !text.includes(qLc)) ok = false;
        if (ok && crLc && !(rowCreator.includes(crLc) || text.includes(crLc))) ok = false;
        if (ok && filter.status && rowStatus && rowStatus !== filter.status.toLowerCase()) ok = false;
        if (ok && filter.createdFrom && createdAt && createdAt.slice(0, 10) < filter.createdFrom) ok = false;
        if (ok && filter.createdTo   && createdAt && createdAt.slice(0, 10) > filter.createdTo)   ok = false;
        if (ok && filter.expiringFrom && expiresAt && expiresAt.slice(0, 10) < filter.expiringFrom) ok = false;
        if (ok && filter.expiringTo   && expiresAt && expiresAt.slice(0, 10) > filter.expiringTo)   ok = false;
        r.style.display = ok ? "" : "none";
      });
    };
    paint();
    const mo = new MutationObserver(paint);
    mo.observe(scope, { childList: true, subtree: true });
    return () => mo.disconnect();
  }, [scopeSelector, rowSelector, filter]);

  const clearAll = () => {
    setQ(""); setCreator("");
    setCreatedFrom(""); setCreatedTo("");
    setExpiringFrom(""); setExpiringTo(""); setStatus("");
  };

  return (
    <div className="bg-white border border-brand-navy/15 rounded px-3 py-3 mb-4 flex flex-wrap items-end gap-3"
         data-testid={testid}>
      <label className="flex flex-col min-w-[200px] flex-1">
        <span className="pmc-label text-[10px]">Search tender / title</span>
        <input value={q} onChange={(e) => setQ(e.target.value)}
               placeholder="PMC-NOT-… or title"
               data-testid={`${testid}-q`}
               className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
      </label>
      {showCreator && (
        <label className="flex flex-col min-w-[180px]">
          <span className="pmc-label text-[10px]">Created by</span>
          <input value={creator} onChange={(e) => setCreator(e.target.value)}
                 placeholder="email@…"
                 data-testid={`${testid}-creator`}
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
        </label>
      )}
      <label className="flex flex-col">
        <span className="pmc-label text-[10px]">Created from</span>
        <input type="date" value={createdFrom}
               onChange={(e) => setCreatedFrom(e.target.value)}
               data-testid={`${testid}-cfrom`}
               className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
      </label>
      <label className="flex flex-col">
        <span className="pmc-label text-[10px]">Created to</span>
        <input type="date" value={createdTo}
               onChange={(e) => setCreatedTo(e.target.value)}
               data-testid={`${testid}-cto`}
               className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
      </label>
      {showExpiring && (<>
        <label className="flex flex-col">
          <span className="pmc-label text-[10px]">Expires from</span>
          <input type="date" value={expiringFrom}
                 onChange={(e) => setExpiringFrom(e.target.value)}
                 data-testid={`${testid}-efrom`}
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
        </label>
        <label className="flex flex-col">
          <span className="pmc-label text-[10px]">Expires to</span>
          <input type="date" value={expiringTo}
                 onChange={(e) => setExpiringTo(e.target.value)}
                 data-testid={`${testid}-eto`}
                 className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm"/>
        </label>
      </>)}
      {statusOptions.length > 0 && (
        <label className="flex flex-col min-w-[140px]">
          <span className="pmc-label text-[10px]">Status</span>
          <select value={status} onChange={(e) => setStatus(e.target.value)}
                  data-testid={`${testid}-status`}
                  className="mt-1 px-2 py-1.5 border border-brand-navy/15 text-sm bg-white">
            <option value="">All</option>
            {statusOptions.map((o) => (
              <option key={o.value ?? o} value={o.value ?? o}>{o.label ?? o}</option>
            ))}
          </select>
        </label>
      )}
      <button type="button" onClick={clearAll}
              data-testid={`${testid}-clear`}
              className="px-3 py-2 text-[10px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy/70 hover:bg-brand-navy/5">
        Clear
      </button>
    </div>
  );
}

/** Predicate helper for controlled mode — tests one row object against a
 *  filter emitted by the bar. Row object should expose at least:
 *  {text, created_at, expires_at, created_by, status}. Missing fields are
 *  considered "no constraint". */
export function matchesMoneyFilter(row, f) {
  if (!f) return true;
  const qLc = (f.q || "").toLowerCase();
  const crLc = (f.creator || "").toLowerCase();
  const text = (row.text || "").toLowerCase();
  if (qLc && !text.includes(qLc)) return false;
  if (crLc) {
    const owner = (row.created_by || row.creator || "").toLowerCase();
    if (!owner.includes(crLc) && !text.includes(crLc)) return false;
  }
  if (f.status && row.status && row.status.toLowerCase() !== f.status.toLowerCase()) return false;
  if (f.createdFrom && row.created_at && row.created_at.slice(0, 10) < f.createdFrom) return false;
  if (f.createdTo   && row.created_at && row.created_at.slice(0, 10) > f.createdTo)   return false;
  if (f.expiringFrom && row.expires_at && row.expires_at.slice(0, 10) < f.expiringFrom) return false;
  if (f.expiringTo   && row.expires_at && row.expires_at.slice(0, 10) > f.expiringTo)   return false;
  return true;
}
