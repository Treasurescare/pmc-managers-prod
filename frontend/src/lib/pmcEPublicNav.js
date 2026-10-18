import { useEffect } from "react";
import { useNavigate } from "react-router-dom";

// Maps the public-site chrome anchors (which ship as href="#") to real routes.
const LINK_MAP = {
  "tenders": "/tenders/live",
  "tender notices": "/tenders/live",
  "open notices": "/tenders/live",
  "browse open tenders": "/tenders/live",
  "browse all notices": "/tenders/live",
  "see programme tenders": "/tenders/live",
  "completed": "/tenders/completed",
  "completed & awarded": "/tenders/completed",
  "corrigenda": "/tenders/live",
  "programme": "/tenders/live",
  "how it works": "/",
  "see how it works": "/",
  "home": "/",
  "for suppliers": "/suppliers",
  "for buyers": "/buyers",
  "for buyers & pmc teams": "/buyers",
  "trust & security": "/trust",
  "verify on ledger": "/trust",
  "sign in": "/vendor/login",
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
      if (el.tagName === "A") el.setAttribute("href", path.split("?")[0]);
      el.style.cursor = "pointer";
      el.addEventListener("click", (e) => navTo(path, e));
    };

    // Brand logo -> home
    root.querySelectorAll("a.pmc-brand").forEach((a) => wire(a, "/"));
    // "Open for bids now" live chip -> tenders list
    root.querySelectorAll("a.pmc-livechip").forEach((a) => wire(a, "/tenders/live"));

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
          navTo(`/tenders/live${params.toString() ? "?" + params.toString() : ""}`);
        });
      }
      // Popular chips -> prefiltered search
      const chipQ = {
        "closing this week": "",
        "civil works & mep": "Civil Works",
        "medical equipment": "Medical",
        "it & digital health": "IT",
      };
      root.querySelectorAll(".pmc-hero__in a.pmc-chip, a.pmc-chip").forEach((chip) => {
        if (chip.dataset.navWired) return;
        const t = chip.textContent.replace("×", "").replace(/\s+/g, " ").trim().toLowerCase();
        if (!(t in chipQ)) return;
        const q = chipQ[t];
        wire(chip, `/tenders/live${q ? "?q=" + encodeURIComponent(q) : ""}`);
      });
      // Stat cards -> relevant destinations
      const statDest = ["/tenders/live", "/register", "/tenders/live", "/trust"];
      root.querySelectorAll(".pmc-stats > div").forEach((d, i) => {
        if (d.dataset.navWired) return;
        wire(d, statDest[i] || "/tenders/live");
      });
    }

    if (page === "trust-security-e") {
      const verifyBtn = Array.from(root.querySelectorAll("button.pmc-btn"))
        .find((b) => /^verify$/i.test(b.textContent.trim()));
      if (verifyBtn && !verifyBtn.dataset.navWired) {
        verifyBtn.dataset.navWired = "1";
        verifyBtn.style.cursor = "pointer";
        verifyBtn.addEventListener("click", (e) => navTo("/contact", e));
      }
    }

    if (page === "contact-e") {
      const form = root.querySelector("form.pmc-card");
      if (form && !form.dataset.navWired) {
        form.dataset.navWired = "1";
        form.addEventListener("submit", (e) => {
          e.preventDefault();
          const btn = form.querySelector("button");
          if (btn) { btn.textContent = "Message sent \u2713"; btn.disabled = true; }
        });
      }
    }

    // Generic chrome anchors still pointing at "#"
    root.querySelectorAll('a[href="#"]:not([data-help-open])').forEach((a) => {
      if (a.dataset.navWired) return;
      const t = a.textContent.replace(/\s+/g, " ").trim().toLowerCase();
      let path = LINK_MAP[t];
      if (!path && /^see all/.test(t)) path = "/tenders/live";
      if (path) wire(a, path);
    });
  }, [enabled, navigate]);
}
