import { useEffect } from "react";
import MoneyFilterBar from "@/components/MoneyFilterBar";

/**
 * MoneyPanelWithFilter — v51ab wrapper that drops a MoneyFilterBar above a
 * legacy money/compliance panel and tags its rendered rows so the filter
 * bar can filter them. For panels we can't easily refactor to use React
 * state (Awards, Billing, Evaluation, L1 comparison, Escrow/EMD, DocuSign).
 *
 * `scope` is a CSS selector picking the <section> or <div> that wraps the
 * table rows. The filter bar then watches that scope and shows/hides rows
 * whose textContent / data-attrs don't match.
 */
export default function MoneyPanelWithFilter({
  scope, children, statusOptions = [], showExpiring = true,
  testid = "money-filter", presetScope,
}) {
  // v51ab — after the panel mounts, decorate every row that has recognisable
  // tender/created/status text with data-attrs so MoneyFilterBar can filter
  // reliably even for panels that don't natively expose those attrs.
  useEffect(() => {
    const paint = () => {
      const root = document.querySelector(scope);
      if (!root) return;
      // v51ag — widened selector so plain-div rows (Escrow transactions,
      // Escrow accounts, DocuSign envelopes) are also tagged for filtering.
      root.querySelectorAll(
        'tr, [data-row], .pmc-row, .bo-r, [data-testid^="escrow-tx-row-"], [data-testid^="escrow-acc-row-"], [data-testid^="docu-env-row-"]'
      ).forEach((r) => {
        if (r.dataset.rowTagged) return;
        r.dataset.rowTagged = "1";
        // Mark as a row we care about
        if (!r.dataset.row) r.dataset.row = "1";
        // Status detection — grab the first pill-like span class
        const pill = r.querySelector(".pmc-pill, .pmc-badge, [data-status-label]");
        if (pill && !r.dataset.status) {
          r.dataset.status = pill.textContent.trim().toLowerCase();
        }
        // Created-at — look for a date like 2026-01-01 anywhere in the row
        if (!r.dataset.createdAt) {
          const m = r.textContent.match(/20\d{2}-\d{2}-\d{2}/);
          if (m) r.dataset.createdAt = m[0];
        }
      });
    };
    paint();
    const mo = new MutationObserver(paint);
    const host = document.querySelector(scope);
    if (host) mo.observe(host, { childList: true, subtree: true });
    return () => mo.disconnect();
  }, [scope]);

  return (
    <>
      <MoneyFilterBar
        testid={testid}
        scopeSelector={scope}
        statusOptions={statusOptions}
        showExpiring={showExpiring}
        presetScope={presetScope}
      />
      {children}
    </>
  );
}
