import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

// Maps the public-site chrome anchors (which ship as href="#") to real routes.
// All tender-listing destinations point at /tenders/all — the live, filterable
// board (legacy TendersList rendered in the E theme). /tenders/live is a static
// design shell and must NOT be linked to for real browsing.
const LINK_MAP = {
  "tenders": "/tenders/all",
  "tender notices": "/tenders/all",
  "open notices": "/tenders/all",
  "browse open tenders": "/tenders/all",
  "browse all notices": "/tenders/all",
  "see programme tenders": "/tenders/all",
  "completed": "/tenders/completed",
  "completed & awarded": "/tenders/completed",
  "corrigenda": "/tenders/all",
  "programme": "/tenders/all",
  "how it works": "/",
  "see how it works": "/",
  "home": "/",
  "for suppliers": "/suppliers",
  "for buyers": "/buyers",
  "for buyers & pmc teams": "/buyers",
  "trust & security": "/trust",
  "verify on ledger": "/trust",
  "sign in": "/login",
  "register as supplier": "/register",
  "register": "/register",
  "kyc guide": "/help",
  "read the kyc guide": "/help",
  "download the brief": "/help",
  "emd & escrow": "/help",
  "help centre": "/help",
  "faqs": "/help",
  "about us": "/about",
  "vision": "/vision",
  "contact": "/contact",
  "contact pmc": "/contact",
  "raise a ticket": "/contact",
  "report a concern": "/contact",
  "privacy": "/privacy",
  "privacy notice": "/privacy",
  "terms of use": "/terms",
  "award notice": "/tenders/completed",
};

export function usePublicNav(enabled = true) {
  const navigate = useNavigate();
  useEffect(() => {
    if (!enabled) return;
    const root = document.querySelector("[data-pmc-e-page]");
    if (!root) return;

    const navTo = (path, e) => {
      if (e && (e.metaKey || e.ctrlKey || e.shiftKey || e.button === 1)) return; // allow new tab
      if (e) e.preventDefault();
      if (path.startsWith("mailto:")) { window.location.href = path; return; }
      navigate(path);
      window.scrollTo(0, 0);
    };
    const wire = (el, path) => {
      if (!el || el.dataset.navWired) return;
      el.dataset.navWired = "1";
      if (el.tagName === "A") el.setAttribute("href", path);
      el.style.cursor = "pointer";
      el.addEventListener("click", (e) => { e.stopPropagation(); navTo(path, e); });
    };

    // Brand logo -> home
    root.querySelectorAll("a.pmc-brand").forEach((a) => wire(a, "/"));
    // "Open for bids now" live chip -> tenders list
    root.querySelectorAll("a.pmc-livechip").forEach((a) => wire(a, "/tenders/all"));

    const page = root.getAttribute("data-pmc-e-page");

    if (page === "home-e") {
      // Hero search + country -> filtered tenders list
      const form = root.querySelector(".pmc-hero__search");
      if (form && !form.dataset.navWired) {
        form.dataset.navWired = "1";
        form.addEventListener("submit", (e) => {
          e.preventDefault();
          const q = (form.querySelector("input")?.value || "").trim();
          const sel = form.querySelector("select");
          const country = sel && sel.value && !/all countries/i.test(sel.value) ? sel.value : "";
          const params = new URLSearchParams();
          if (q) params.set("q", q);
          if (country) params.set("country", country);
          navTo(`/tenders/all${params.toString() ? "?" + params.toString() : ""}`);
        });
      }
      // Popular chips -> prefiltered search / status filter
      const chipPath = {
        "closing this week": "/tenders/all?status=closing",
        "civil works & mep": "/tenders/all?q=" + encodeURIComponent("Civil Works"),
        "medical equipment": "/tenders/all?q=Medical",
        "it & digital health": "/tenders/all?q=IT",
      };
      root.querySelectorAll(".pmc-hero__in a.pmc-chip, a.pmc-chip").forEach((chip) => {
        if (chip.dataset.navWired) return;
        const t = chip.textContent.replace("×", "").replace(/\s+/g, " ").trim().toLowerCase();
        if (!(t in chipPath)) return;
        wire(chip, chipPath[t]);
      });
      // Stat cards -> relevant destinations
      const statDest = ["/tenders/all", "/register", "/tenders/all", "/trust"];
      root.querySelectorAll(".pmc-stats > div").forEach((d, i) => {
        if (d.dataset.navWired) return;
        wire(d, statDest[i] || "/tenders/all");
      });
      // Programme spotlight category cards -> tenders list
      root.querySelectorAll(".pmc-cats a.pmc-cat").forEach((a) => wire(a, "/tenders/all"));
      // Help & FAQs contact tiles
      root.querySelectorAll(".pmc-contact a").forEach((a) => {
        if (a.dataset.navWired) return;
        if ((a.getAttribute("href") || "").startsWith("mailto:")) return;
        const b = (a.querySelector("b")?.textContent || "").trim().toLowerCase();
        if (b.includes("help centre")) wire(a, "/help");
        else if (b.includes("raise a ticket")) wire(a, "/contact");
      });
    }

    if (page === "awards-public-e") {
      // "Awarded in 2026" KPI tile -> awarded filter on the tenders list
      const kpi = root.querySelector(".pmc-kpi.pmc-panel");
      if (kpi && !kpi.dataset.navWired) wire(kpi, "/tenders/all?status=awarded");
    }

    // Generic chrome anchors still pointing at "#"
    root.querySelectorAll('a[href="#"]:not([data-help-open])').forEach((a) => {
      if (a.dataset.navWired) return;
      const t = a.textContent.replace(/\s+/g, " ").trim().toLowerCase();
      let path = LINK_MAP[t];
      if (!path && /^see all/.test(t)) path = "/tenders/all";
      if (path) wire(a, path);
    });
  }, [enabled, navigate]);
}
