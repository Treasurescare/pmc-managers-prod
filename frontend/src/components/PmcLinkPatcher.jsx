import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { useUiTheme } from "@/context/UiThemeContext";

/**
 * PMC v49f — Wires the static Option-E templates' dead links (href="#")
 * to real app routes with SPA navigation (no full reload → no S3 404).
 *
 * Matches anchors/buttons by their visible label inside any [data-pmc-e-page]
 * tree. On vendor pages the in-page CTAs (Pay EMD, View bid, Track, Start bid,
 * Continue draft, View contract, Upload bank guarantee, Review & sign, See all
 * open notices, Saved searches, Sign LOA, DocuSign link, Details, Debrief,
 * Add the licence / Change) are all routed to the correct portal page. KPI
 * tiles + Active/Closed tabs are also clickable.
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

// v49f — In-page CTAs on the vendor portal. Regex-matched (not exact-label)
// because labels frequently embed counts / currency ("See all 29 open notices",
// "Pay EMD  USD 61,380", etc.). First match wins.
const VENDOR_CTA_MATCHERS = [
  { rx: /^pay(\s+emd)?$/i,                         path: "/vendor/emd" },
  { rx: /upload\s+bank\s+guarantee/i,              path: "/vendor/emd" },
  { rx: /pay\s+with\s+card/i,                      path: "/vendor/emd" },
  { rx: /^view\s+bid$/i,                           path: "/vendor/mybids" },
  { rx: /^continue\s+draft$/i,                     path: "/vendor/mybids" },
  { rx: /^view\s+contract$/i,                      path: "/vendor/signatures" },
  { rx: /^start\s+bid$/i,                          path: "/vendor/tenders" },
  { rx: /^track$/i,                                path: "/vendor/mybids" },
  { rx: /^details$/i,                              path: "/vendor/mybids" },
  { rx: /^debrief$/i,                              path: "/vendor/mybids" },
  { rx: /see\s+all.*(open\s+)?notices?/i,          path: "/vendor/tenders" },
  { rx: /saved\s+searches/i,                       path: "/vendor/tenders" },
  { rx: /review\s*&?\s*sign|sign\s+loa/i,          path: "/vendor/signatures" },
  { rx: /send\s+me\s+the\s+docusign/i,             path: "/vendor/signatures" },
  { rx: /add\s+the\s+licence/i,                    path: "/vendor/company" },
  { rx: /^change$/i,                               path: "/vendor/company" },
  { rx: /^reply$/i,                                path: "/vendor/mybids" },
  { rx: /^preview$/i,                              path: "/vendor/mybids" },
  { rx: /^review$/i,                               path: "/vendor/reviews" },
  { rx: /leave\s+a\s+review/i,                     path: "/vendor/reviews" },
  { rx: /raise\s+a\s+ticket/i,                     path: "/help" },
];

// KPI tile → route (matched by the tile's <div class="l">Label</div>).
const VENDOR_KPI_TILES = {
  "active bids": "/vendor/mybids",
  "closing this week": "/vendor/tenders",
  "matched to your kyc": "/vendor/tenders",
  "kyc status": "/vendor/company",
  "escrow balance": "/vendor/emd",
  "pending emd": "/vendor/emd",
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

function labelOf(el) {
  let t = (el.textContent || "").trim().replace(/\s+/g, " ").toLowerCase();
  t = t.replace(/\s*\d+\s*$/, "").trim();
  return t;
}

function matchVendorCta(label) {
  for (const { rx, path } of VENDOR_CTA_MATCHERS) {
    if (rx.test(label)) return path;
  }
  return null;
}

function wireKpiTiles(root, navigate) {
  root.querySelectorAll(".pmc-kpi").forEach((tile) => {
    if (tile.dataset.pmcPatched) return;
    const label = (tile.querySelector(".l")?.textContent || "").trim().toLowerCase();
    const target = VENDOR_KPI_TILES[label];
    if (!target) return;
    tile.dataset.pmcPatched = "1";
    tile.style.cursor = "pointer";
    tile.setAttribute("role", "link");
    tile.setAttribute("tabindex", "0");
    const go = () => navigate(target);
    tile.addEventListener("click", go);
    tile.addEventListener("keydown", (e) => {
      if (e.key === "Enter" || e.key === " ") { e.preventDefault(); go(); }
    });
  });
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

      if (href && href !== "#" && !href.startsWith("#") && !href.startsWith("mailto:")) {
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

      const direct = map[label];
      const vendorCta = isVendor ? matchVendorCta(label) : null;
      const target = direct || vendorCta;
      if (target) {
        a.dataset.pmcPatched = "1";
        a.setAttribute("href", target);
        a.addEventListener("click", (e) => { e.preventDefault(); navigate(target); });
      } else if (href === "#") {
        a.dataset.pmcPatched = "1";
        a.addEventListener("click", (e) => e.preventDefault());
      }
    });

    // 2) Button elements
    root.querySelectorAll("button").forEach((b) => {
      if (b.dataset.pmcPatched) return;
      const label = labelOf(b);

      // Chip filter (single-select within row)
      if (b.classList.contains("pmc-chip")) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", () => {
          const row = b.parentElement;
          row?.querySelectorAll(".pmc-chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
          b.setAttribute("aria-pressed", "true");
        });
        return;
      }
      // Tab (single-select within row) — used by Active/Closed on vendor home
      if (b.classList.contains("pmc-tab")) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", () => {
          const row = b.parentElement;
          row?.querySelectorAll(".pmc-tab").forEach((t) => t.setAttribute("aria-selected", "false"));
          b.setAttribute("aria-selected", "true");
        });
        return;
      }

      if (b.hasAttribute("data-help-open") || /help|faqs?|what is emd\?/.test(label)) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => { e.preventDefault(); document.querySelector(".pmc-helpfab")?.click(); });
        return;
      }

      const direct = map[label];
      const vendorCta = isVendor ? matchVendorCta(label) : null;
      const target = direct || vendorCta;
      if (target) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => { e.preventDefault(); navigate(target); });
        return;
      }
      if (/^(find\s*tenders|explore\s*tenders|browse\s*all)/.test(label)) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => { e.preventDefault(); navigate(isVendor ? "/vendor/tenders" : "/tenders/live"); });
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
      if (b.textContent.trim().length <= 3) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => e.preventDefault());
      }
    });

    // 3) KPI tiles (vendor pages only)
    if (isVendor) wireKpiTiles(root, navigate);
  });
}

export default function PmcLinkPatcher() {
  const { isE } = useUiTheme();
  const navigate = useNavigate();
  const location = useLocation();

  useEffect(() => {
    if (!isE) return;
    const t1 = setTimeout(() => patchScope(navigate), 50);
    const t2 = setTimeout(() => patchScope(navigate), 600);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [isE, location.pathname, navigate]);

  return null;
}
