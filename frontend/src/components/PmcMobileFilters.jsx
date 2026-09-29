import { useEffect, useState, useCallback } from "react";
import { useLocation } from "react-router-dom";

/**
 * PmcMobileFilters — turns the fixed sidebar filter panel on the tender list
 * page into a GeM-style bottom-sheet on mobile (≤767px). Desktop is
 * untouched; the sidebar shows inline as before.
 *
 * Approach: mount globally, on route change scan for a `.tl-filters` aside;
 * if found, inject a `.pmc-filters-fab` pill button and a `.pmc-filters-sheet`
 * wrapper around the existing aside. A body class `pmc-filters-open`
 * animates the sheet in from the bottom. The scrim and the close button
 * dismiss the sheet.
 */
export default function PmcMobileFilters() {
  const { pathname } = useLocation();
  const [_, force] = useState(0);
  const rerender = useCallback(() => force((x) => x + 1), []);

  useEffect(() => {
    if (!pathname.startsWith("/tenders") && !pathname.startsWith("/notices")) return;
    let cleanup = () => {};
    const install = () => {
      const aside = document.querySelector("aside.tl-filters");
      if (!aside || aside.dataset.pmcSheetBound === "1") return;
      aside.dataset.pmcSheetBound = "1";

      // 1. FAB — floating "Filters" button at the top of the results list
      const results = aside.nextElementSibling; // <section>
      if (!results) return;
      const fab = document.createElement("button");
      fab.type = "button";
      fab.className = "pmc-filters-fab";
      fab.setAttribute("data-testid", "pmc-filters-fab");
      fab.innerHTML =
        '<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true">' +
        '<path d="M3 6h18M6 12h12M10 18h4" stroke="currentColor" stroke-width="2" stroke-linecap="round" fill="none"/></svg>' +
        '<span>Filters</span>' +
        '<span class="pmc-filters-count" data-testid="pmc-filters-count">Open</span>';
      results.insertBefore(fab, results.firstChild);

      // 2. Wrap aside in sheet chrome
      aside.classList.add("pmc-filters-sheet-body");
      const sheet = document.createElement("div");
      sheet.className = "pmc-filters-sheet";
      sheet.setAttribute("role", "dialog");
      sheet.setAttribute("aria-modal", "true");
      sheet.setAttribute("aria-label", "Filters");
      sheet.setAttribute("data-testid", "pmc-filters-sheet");
      const scrim = document.createElement("div");
      scrim.className = "pmc-filters-scrim";
      scrim.setAttribute("data-testid", "pmc-filters-scrim");
      const head = document.createElement("div");
      head.className = "pmc-filters-sheet-head";
      head.innerHTML =
        '<div class="grabber"></div>' +
        '<div class="ttl">Filters</div>' +
        '<button type="button" class="pmc-filters-close" aria-label="Close" data-testid="pmc-filters-close">&times;</button>';
      aside.parentElement.insertBefore(sheet, aside);
      aside.parentElement.insertBefore(scrim, sheet);
      sheet.appendChild(head);
      sheet.appendChild(aside);
      // Sticky footer "Show results" button that closes the sheet
      const foot = document.createElement("div");
      foot.className = "pmc-filters-sheet-foot";
      foot.innerHTML =
        '<button type="button" class="pmc-btn pmc-btn--primary" data-testid="pmc-filters-apply" style="width:100%;min-height:46px">Show results</button>';
      sheet.appendChild(foot);

      const open = () => document.body.classList.add("pmc-filters-open");
      const close = () => document.body.classList.remove("pmc-filters-open");
      fab.addEventListener("click", open);
      scrim.addEventListener("click", close);
      head.querySelector(".pmc-filters-close").addEventListener("click", close);
      foot.querySelector('[data-testid="pmc-filters-apply"]').addEventListener("click", close);
      const onKey = (e) => { if (e.key === "Escape") close(); };
      window.addEventListener("keydown", onKey);
      cleanup = () => {
        window.removeEventListener("keydown", onKey);
        document.body.classList.remove("pmc-filters-open");
      };
      rerender();
    };
    install();
    const t = setTimeout(install, 300);
    const t2 = setTimeout(install, 1200);
    return () => { clearTimeout(t); clearTimeout(t2); cleanup(); };
  }, [pathname, rerender]);

  return null;
}
