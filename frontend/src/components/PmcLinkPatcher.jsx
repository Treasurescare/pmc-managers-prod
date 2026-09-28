import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useUiTheme } from "@/context/UiThemeContext";

/**
 * PMC v49d — Wires the static Option-E templates' dead links (href="#")
 * to real app routes, with SPA navigation (no full reload → no S3 404).
 *
 * Matches anchors by their visible label inside any [data-pmc-e-page] tree.
 */

const PUBLIC_LINKS = {
  "tenders": "/tenders/live",
  "how it works": "/#how",
  "for suppliers": "/suppliers",
  "for buyers": "/buyers",
  "trust & security": "/trust",
  "help & faqs": "/help",
  "help & faq": "/help",
  "sign in": "/login",
  "register as supplier": "/register",
  "register": "/register",
  "about": "/about",
  "vision": "/vision",
  "contact": "/contact",
  "privacy": "/privacy",
  "terms": "/terms",
  "browse all notices": "/tenders/live",
  "explore tenders": "/tenders/live",
  "find tenders": "/tenders/live",
  "see all open notices": "/tenders/live",
};

const VENDOR_LINKS = {
  "home": "/vendor",
  "find tenders": "/vendor/tenders",
  "my bids": "/vendor/mybids",
  "emd & payments": "/vendor/emd",
  "emd": "/vendor/emd",
  "signatures": "/vendor/signatures",
  "company & kyc": "/vendor/company",
  "reviews": "/vendor/reviews",
  "account & security": "/vendor/account",
  "alerts": "/vendor/alerts",
};

const ADMIN_LINKS = {
  "dashboard": "/admin/e/dashboard",
  "audit ledger": "/admin/e/audit",
  "notices": "/admin/e/notices",
  "tender builder": "/admin/e/tender-builder",
  "create": "/admin/e/tender-builder",
  "+ create": "/admin/e/tender-builder",
  "new tender": "/admin/e/tender-builder",
  "new notice": "/admin/e/tender-builder",
  "corrigenda": "/admin/e/corrigenda",
  "work packages": "/admin/e/work-packages",
  "catalog": "/admin/e/catalog",
  "boq & contracts": "/admin/e/boq",
  "vendors": "/admin/e/vendors",
  "registrations": "/admin/e/registrations",
  "engagements": "/admin/e/engagements",
  "vendor intel": "/admin/e/vendor-intel",
  "bidding ops": "/admin/e/bidding",
  "escrow / emd": "/admin/e/escrow",
  "escrow/emd": "/admin/e/escrow",
  "billing": "/admin/e/billing",
  "evaluation": "/admin/e/evaluations",
  "l1 comparison": "/admin/e/l1-award",
  "awards": "/admin/e/awards",
  "docusign": "/admin/e/docusign",
  "permissions": "/admin/e/permissions",
  "events & alerts": "/admin/e/events",
  "programme": "/admin/e/programme",
  "programme at a glance": "/admin/e/programme",
};

function labelOf(a) {
  // Strip trailing count-badge digits ("Notices17" -> "notices")
  let t = (a.textContent || "").trim().replace(/\s+/g, " ").toLowerCase();
  t = t.replace(/\s*\d+\s*$/, "").trim();
  return t;
}

function patchScope(navigate) {
  document.querySelectorAll("[data-pmc-e-page]").forEach((root) => {
    const pageId = root.getAttribute("data-pmc-e-page") || "";
    const isVendor = pageId.startsWith("vendor-");
    const isAdmin = pageId.startsWith("admin-");
    const map = isVendor ? { ...PUBLIC_LINKS, ...VENDOR_LINKS }
              : isAdmin ? ADMIN_LINKS
              : PUBLIC_LINKS;

    // 1) Anchor tags
    root.querySelectorAll("a").forEach((a) => {
      if (a.dataset.pmcPatched) return;
      const href = a.getAttribute("href") || "";
      const label = labelOf(a);

      if (href && href !== "#" && !href.startsWith("#")) {
        a.dataset.pmcPatched = "1";
        a.addEventListener("click", (e) => {
          if (href.startsWith("/") && !href.startsWith("//")) {
            e.preventDefault();
            navigate(href);
          }
        });
        return;
      }

      if (a.classList.contains("pmc-brand") || a.querySelector(".pmc-brand__n")) {
        a.dataset.pmcPatched = "1";
        a.setAttribute("href", isVendor ? "/vendor" : isAdmin ? "/admin/e/dashboard" : "/");
        a.addEventListener("click", (e) => {
          e.preventDefault();
          navigate(isVendor ? "/vendor" : isAdmin ? "/admin/e/dashboard" : "/");
        });
        return;
      }

      if (a.hasAttribute("data-help-open")) {
        a.dataset.pmcPatched = "1";
        a.addEventListener("click", (e) => { e.preventDefault(); document.querySelector(".pmc-helpfab")?.click(); });
        return;
      }

      const target = map[label];
      if (target) {
        a.dataset.pmcPatched = "1";
        a.setAttribute("href", target);
        a.addEventListener("click", (e) => { e.preventDefault(); navigate(target); });
      } else if (href === "#") {
        a.dataset.pmcPatched = "1";
        a.addEventListener("click", (e) => e.preventDefault());
      }
    });

    // 2) Button elements — wire by label + chip pattern
    root.querySelectorAll("button").forEach((b) => {
      if (b.dataset.pmcPatched) return;
      const label = labelOf(b);
      // Chips: keep local (aria-pressed toggle) — handled per-page (filter engine)
      if (b.classList.contains("pmc-chip")) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", () => {
          // Toggle pressed state within the same chip row
          const row = b.parentElement;
          row?.querySelectorAll(".pmc-chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
          b.setAttribute("aria-pressed", "true");
        });
        return;
      }
      // Help drawer trigger
      if (b.hasAttribute("data-help-open") || /help|faqs?/.test(label)) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => { e.preventDefault(); document.querySelector(".pmc-helpfab")?.click(); });
        return;
      }
      // Known route label
      const target = map[label];
      if (target) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => { e.preventDefault(); navigate(target); });
        return;
      }
      // Common CTA fallbacks
      if (/^(find\s*tenders|explore\s*tenders|browse\s*all)/.test(label)) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => { e.preventDefault(); navigate("/tenders/live"); });
        return;
      }
      if (/^(create|new\s+(tender|notice|package))/.test(label) && isAdmin) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => { e.preventDefault(); navigate("/admin/e/tender-builder"); });
        return;
      }
      if (/(sign\s*in|log\s*in)/.test(label)) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => { e.preventDefault(); navigate("/login"); });
        return;
      }
      if (/register/.test(label) && !isVendor && !isAdmin) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => { e.preventDefault(); navigate("/register"); });
        return;
      }
      // Language switcher — no-op but stops the click bounce
      if (b.textContent.trim().length <= 3) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => e.preventDefault());
      }
    });
  });
}

export default function PmcLinkPatcher() {
  const { isE } = useUiTheme();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isE) return;
    // Patch after templates mount; re-run on every route change
    const t1 = setTimeout(() => patchScope(navigate), 50);
    const t2 = setTimeout(() => patchScope(navigate), 600);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [isE, location.pathname, navigate]);

  return null;
}
