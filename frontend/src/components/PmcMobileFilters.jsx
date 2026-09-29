import { useEffect, useState, useCallback } from "react";
import { useLocation } from "react-router-dom";

/**
 * PmcMobileFilters — turns the fixed sidebar filter panel on the tender list
 * page into a GeM-style bottom-sheet on mobile (≤767px) ONLY.
 *
 * CRITICAL: the DOM restructure (wrapping aside.tl-filters into a fixed
 * sheet) must never happen on desktop — when it did, the sidebar vanished
 * and the results column collapsed into the 272px grid track, breaking the
 * desktop tenders page. install() runs only while the mobile media query
 * matches; uninstall() restores the aside to its original position and
 * removes the injected FAB/scrim/sheet. A matchMedia listener re-applies on
 * viewport changes so rotating/resizing never strands the wrong layout.
 */
const MQ = "(max-width: 767px)";

export default function PmcMobileFilters() {
  const { pathname } = useLocation();
  const [, force] = useState(0);
  const rerender = useCallback(() => force((x) => x + 1), []);

  useEffect(() => {
    const mq = window.matchMedia(MQ);
    let restore = () => {};

    const uninstall = () => {
      try { restore(); } catch (_) { /* noop */ }
      restore = () => {};
      document.body.classList.remove("pmc-filters-open");
    };

    const install = () => {
      const aside = document.querySelector("aside.tl-filters");
      if (!aside || aside.dataset.pmcSheetBound === "1") return;
      const results = aside.nextElementSibling; // <section> results column
      if (!results) return;
      aside.dataset.pmcSheetBound = "1";
      const originalParent = aside.parentElement;
      const originalNext = aside.nextElementSibling;

      // 1. FAB — "Filters" pill at the top of the results list
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

      // Live count of active filters
      const countEl = fab.querySelector('[data-testid="pmc-filters-count"]');
      const updateCount = () => {
        const activeRadio = [...aside.querySelectorAll('input[type="radio"]:checked')]
          .filter((r) => r.value && !["all", "open"].includes(r.value.toLowerCase())).length;
        const activeChecks = [...aside.querySelectorAll('input[type="checkbox"]:checked')].length;
        const n = activeRadio + activeChecks;
        countEl.textContent = n > 0 ? String(n) : "Open";
        countEl.classList.toggle("is-active", n > 0);
      };
      aside.addEventListener("change", updateCount);
      updateCount();

      const open = () => document.body.classList.add("pmc-filters-open");
      const close = () => document.body.classList.remove("pmc-filters-open");
      fab.addEventListener("click", open);
      scrim.addEventListener("click", close);
      head.querySelector(".pmc-filters-close").addEventListener("click", close);
      foot.querySelector('[data-testid="pmc-filters-apply"]').addEventListener("click", close);
      const onKey = (e) => { if (e.key === "Escape") close(); };
      window.addEventListener("keydown", onKey);

      // Uninstall: put the aside back where it came from and drop the chrome
      restore = () => {
        window.removeEventListener("keydown", onKey);
        aside.classList.remove("pmc-filters-sheet-body");
        delete aside.dataset.pmcSheetBound;
        if (originalParent) {
          if (originalNext && originalNext.parentElement === originalParent) {
            originalParent.insertBefore(aside, originalNext);
          } else {
            originalParent.appendChild(aside);
          }
        }
        fab.remove();
        sheet.remove();
        scrim.remove();
      };
      rerender();
    };

    const apply = () => {
      uninstall();
      const onPage = pathname.startsWith("/tenders") || pathname.startsWith("/notices");
      if (mq.matches && onPage) install();
    };

    apply();
    // The list hydrates async — retry twice for late-rendered sidebars.
    const t1 = setTimeout(apply, 300);
    const t2 = setTimeout(apply, 1200);
    mq.addEventListener?.("change", apply);
    return () => {
      clearTimeout(t1);
      clearTimeout(t2);
      mq.removeEventListener?.("change", apply);
      uninstall();
    };
  }, [pathname, rerender]);

  return null;
}
