import { useEffect } from "react";
import { useLocation } from "react-router-dom";

/**
 * PmcHomeFilters — makes the "All / Tender / RFP / RFQ" chips on the home
 * page (and any similar chip row that lives just above a set of
 * `.pmc-tender` cards) actually filter the cards.
 *
 * Because the 55-screen theme cards are static markup, we filter via DOM:
 *  - Chips carry the text "All", "Tender", "RFP", "RFQ" — case-insensitive
 *  - Each tender card exposes its kind via the `.pmc-tag` text inside
 *  - Clicking a chip sets aria-pressed on the row and hides cards that
 *    don't match the chosen kind.
 *
 * Works on both mobile and desktop, no per-page code changes needed.
 */
export default function PmcHomeFilters() {
  const { pathname } = useLocation();

  useEffect(() => {
    const apply = () => {
      // Find every chip row that contains an "All" chip AND at least one
      // Tender/RFP/RFQ sibling chip — these are our filter rows.
      const chipRows = [...document.querySelectorAll("div")].filter((row) => {
        const kids = row.children;
        if (!kids || kids.length < 2) return false;
        const labels = [...kids]
          .filter((k) => k.classList?.contains("pmc-chip"))
          .map((k) => (k.textContent || "").trim().toLowerCase());
        return labels.includes("all") && labels.some((l) => ["tender", "rfp", "rfq"].includes(l));
      });
      chipRows.forEach((row) => {
        if (row.dataset.pmcFiltersBound === "1") return;
        row.dataset.pmcFiltersBound = "1";
        // Find the sibling card grid — walk up to the nearest <section>
        // then look for the first grid or list of `.pmc-tender` elements.
        const section = row.closest("section") || row.parentElement;
        if (!section) return;
        const cards = () => [...section.querySelectorAll(".pmc-tender")];
        const filter = (kind) => {
          const k = (kind || "all").toLowerCase();
          cards().forEach((card) => {
            // Never reveal unpopulated template cards (empty DB / unused slots).
            // pmcELiveData marks live-filled cards with data-pmc-filled="1".
            if (card.dataset.pmcFilled !== "1") { card.style.display = "none"; return; }
            const tag = (card.querySelector(".pmc-tag")?.textContent || "").trim().toLowerCase();
            const hide = k !== "all" && tag !== k;
            card.style.display = hide ? "none" : "";
          });
        };
        row.addEventListener("click", (e) => {
          const btn = e.target.closest(".pmc-chip");
          if (!btn || !row.contains(btn)) return;
          const label = (btn.textContent || "").trim().toLowerCase();
          if (!["all", "tender", "rfp", "rfq"].includes(label)) return;
          e.preventDefault();
          [...row.querySelectorAll(".pmc-chip")].forEach((c) => c.setAttribute("aria-pressed", "false"));
          btn.setAttribute("aria-pressed", "true");
          filter(label);
        });
      });
    };
    apply();
    // The generated home page hydrates class content via pmcELiveData —
    // re-scan after a short delay so we catch newly-rendered chip rows.
    const t = setTimeout(apply, 400);
    const t2 = setTimeout(apply, 1500);
    return () => { clearTimeout(t); clearTimeout(t2); };
  }, [pathname]);

  return null;
}
