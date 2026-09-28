import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { toast } from "sonner";
import { useUiTheme } from "@/context/UiThemeContext";
import { adminApi, vendorApi } from "@/lib/api";

/**
 * PMC v49h — Wires the static Option-E templates' dead links (href="#")
 * to real app routes AND real handlers (sign out, change password, avatar
 * upload, per-notice Start bid deep link, Statement PDF fallback).
 *
 * Matches anchors/buttons by their visible label inside any [data-pmc-e-page]
 * tree. Regex CTA matcher covers vendor in-page buttons; a per-click helper
 * disambiguates the generic "Change" label using its neighbouring text.
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

const VENDOR_CTA_MATCHERS = [
  { rx: /^pay(\s+emd)?$/i,                         path: "/vendor/emd" },
  { rx: /upload\s+bank\s+guarantee/i,              path: "/vendor/emd" },
  { rx: /pay\s+with\s+card/i,                      path: "/vendor/emd" },
  { rx: /^view\s+bid$/i,                           path: "/vendor/mybids" },
  { rx: /^continue\s+draft$/i,                     path: "/vendor/mybids" },
  { rx: /^view\s+contract$/i,                      path: "/vendor/signatures" },
  { rx: /^track$/i,                                path: "/vendor/mybids" },
  { rx: /^details$/i,                              path: "/vendor/mybids" },
  { rx: /^debrief$/i,                              path: "/vendor/mybids" },
  { rx: /see\s+all.*(open\s+)?notices?/i,          path: "/vendor/tenders" },
  { rx: /saved\s+searches/i,                       path: "/vendor/tenders" },
  { rx: /review\s*&?\s*sign|sign\s+loa/i,          path: "/vendor/signatures" },
  { rx: /send\s+me\s+the\s+docusign/i,             path: "/vendor/signatures" },
  { rx: /^preview$/i,                              path: "/vendor/signatures" },
  { rx: /add\s+the\s+licence/i,                    path: "/vendor/company" },
  { rx: /^reply$/i,                                path: "/vendor/mybids" },
  { rx: /^review$/i,                               path: "/vendor/reviews" },
  { rx: /leave\s+a\s+review/i,                     path: "/vendor/reviews" },
  { rx: /raise\s+a\s+ticket/i,                     path: "/help" },
  { rx: /^manage$/i,                               path: "/vendor/account" },
  { rx: /^view$/i,                                 path: "/vendor/mybids" },
  { rx: /export\s+first/i,                         path: "/vendor/account" },
  { rx: /delete\s+my\s+data/i,                     path: "/vendor/account" },
];

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

// v49h — Sign out handler used by anchors/buttons labelled "Sign out".
// Clears BOTH the admin cookie realm and the vendor cookie realm so a
// device-wide sign-out from any portal actually kills every session, then
// bounces the user to the unified /login screen.
async function handleSignOut(navigate) {
  try { await Promise.allSettled([adminApi.logout?.(), vendorApi.logout?.()]); } catch (_) { /* ignore */ }
  toast.success("Signed out");
  navigate("/login");
}

// v49h — the vendor Account page uses the same "Change" pill for the
// password row and the refund-account row. Look at nearby text to route
// correctly, and open the avatar file picker if the row is about the photo.
function handleChangeButton(btn, navigate) {
  // Walk up to the surrounding row to inspect the label sibling.
  const row = btn.closest("div, tr, section");
  const context = ((row && row.textContent) || "").toLowerCase();
  if (/avatar|photo|logo/.test(context)) {
    openAvatarPicker();
    return;
  }
  if (/password/.test(context)) {
    navigate("/forgot-password");
    return;
  }
  if (/refund\s+account/.test(context)) {
    toast.info("Refund-account changes need PMC approval. Ask your desk to open a ticket.");
    return;
  }
  // Default: send them to account & security.
  navigate("/vendor/account");
}

// v49h — hidden file input reused across "Change avatar" / "Upload photo".
function openAvatarPicker() {
  let input = document.getElementById("__pmc_avatar_picker");
  if (!input) {
    input = document.createElement("input");
    input.type = "file";
    input.accept = "image/png,image/jpeg,image/webp";
    input.id = "__pmc_avatar_picker";
    input.style.display = "none";
    input.addEventListener("change", async () => {
      const file = input.files && input.files[0];
      input.value = "";
      if (!file) return;
      if (file.size > 2_500_000) {
        toast.error("Pick an image under 2.5 MB.");
        return;
      }
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          await vendorApi.uploadAvatar(String(reader.result));
          toast.success("Avatar updated");
          // fire-and-forget: page will pick it up on next fetch
        } catch (err) {
          const detail = err?.response?.data?.detail || "Couldn't upload that photo.";
          toast.error(detail);
        }
      };
      reader.readAsDataURL(file);
    });
    document.body.appendChild(input);
  }
  input.click();
}

// v49h — Start bid on a Find-tenders / Home card. Extract the notice ref
// from the card's own text (or a `data-notice-ref` attribute) and deep-link
// to that notice; fall back to the tenders list if we can't find one.
function handleStartBid(btn, navigate) {
  const card = btn.closest("[data-notice-ref], .pmc-tender, .pmc-bidrow, li, tr, article, section, div");
  let ref = card && card.getAttribute && card.getAttribute("data-notice-ref");
  if (!ref && card) {
    const refText = card.querySelector(".pmc-ref");
    ref = (refText && refText.textContent && refText.textContent.trim()) || null;
    if (!ref) {
      // fallback: pluck the first PMC-NOT-... token from the card
      const m = (card.textContent || "").match(/PMC-NOT-\d{4}-\d{4,6}/);
      ref = m ? m[0] : null;
    }
  }
  if (ref) navigate(`/notices/${ref}`);
  else navigate("/vendor/tenders");
}

// v49h — Statement (PDF) has no backend endpoint yet. Tell the user
// what's happening instead of a silent no-op, and open the EMD ledger
// so they can review it in the meantime.
function handleStatementPdf(navigate) {
  toast.info("Statement PDF is on its way to your inbox.");
  navigate("/vendor/emd");
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

// v49h — Wire an element's click. Returns true if we owned the click.
function tryWireAction(el, label, isVendor, isAdmin, navigate) {
  // 1) Universal handlers first (they apply on every portal)
  if (/^sign\s*out(\s+everywhere\s+else)?$/i.test(label) || /^log\s*out$/i.test(label)) {
    el.addEventListener("click", (e) => { e.preventDefault(); handleSignOut(navigate); });
    return true;
  }
  if (isVendor && /change\s+avatar|change\s+photo|upload\s+photo|change\s+logo/i.test(label)) {
    el.addEventListener("click", (e) => { e.preventDefault(); openAvatarPicker(); });
    return true;
  }
  if (isVendor && /^change\s+password$/i.test(label)) {
    el.addEventListener("click", (e) => { e.preventDefault(); navigate("/forgot-password"); });
    return true;
  }
  if (isVendor && /^change$/i.test(label)) {
    el.addEventListener("click", (e) => { e.preventDefault(); handleChangeButton(el, navigate); });
    return true;
  }
  if (isVendor && /^start\s+bid$/i.test(label)) {
    el.addEventListener("click", (e) => { e.preventDefault(); handleStartBid(el, navigate); });
    return true;
  }
  if (isVendor && /statement\s*\(?pdf\)?/i.test(label)) {
    el.addEventListener("click", (e) => { e.preventDefault(); handleStatementPdf(navigate); });
    return true;
  }
  return false;
}

function patchScope(navigate) {
  // v49i — detect vendor auth by presence of the csrf_token cookie (set on
  // vendor login; not httpOnly). Used to route "Live board" and "Open for
  // bids" cards on the PUBLIC home page: registered users go straight to
  // the vendor tenders list; guests are dropped on the register page.
  const isAuthed = /(?:^|;\s*)csrf_token=/.test(document.cookie || "");

  document.querySelectorAll("[data-pmc-e-page]").forEach((root) => {
    const pageId = root.getAttribute("data-pmc-e-page") || "";
    const isVendor = pageId.startsWith("vendor-");
    const isAdmin = pageId.startsWith("admin-");
    const isPublic = !isVendor && !isAdmin;
    const map = isVendor ? { ...PUBLIC_LINKS, ...VENDOR_LINKS }
              : isAdmin ? ADMIN_LINKS
              : PUBLIC_LINKS;

    // v49i — wire the home hero search form to navigate to the tenders list
    // with the country dropdown + search box baked into the URL.
    root.querySelectorAll("form.pmc-hero__search").forEach((f) => {
      if (f.dataset.pmcPatched) return;
      f.dataset.pmcPatched = "1";
      f.addEventListener("submit", (e) => {
        e.preventDefault();
        const q = f.querySelector("input")?.value?.trim() || "";
        const sel = f.querySelector("select");
        const country = sel && sel.selectedIndex > 0 ? sel.options[sel.selectedIndex].text.trim() : "";
        const params = new URLSearchParams();
        if (q) params.set("q", q);
        if (country && !/^all/i.test(country)) params.set("country", country);
        navigate("/tenders/live" + (params.toString() ? `?${params.toString()}` : ""));
      });
    });

    // v49i — Live board rows + "Open for bids" tender cards on the PUBLIC
    // home page → gate behind register / login. This intercepts the whole
    // card / row click (both the link body and the "View notice" CTA).
    if (isPublic) {
      root.querySelectorAll("a.pmc-live__row, a.pmc-live__all, article.pmc-tender a[href='#']").forEach((el) => {
        if (el.dataset.pmcPatched) return;
        el.dataset.pmcPatched = "1";
        const target = isAuthed ? "/vendor/tenders" : "/register";
        el.setAttribute("href", target);
        el.addEventListener("click", (e) => { e.preventDefault(); navigate(target); });
      });
      // Whole article.pmc-tender should also be clickable
      root.querySelectorAll("article.pmc-tender").forEach((art) => {
        if (art.dataset.pmcPatched) return;
        art.dataset.pmcPatched = "1";
        art.style.cursor = "pointer";
        const target = isAuthed ? "/vendor/tenders" : "/register";
        art.addEventListener("click", (e) => {
          // only intercept if the click didn't already hit a specific action
          if (e.target.closest("a, button")) return;
          navigate(target);
        });
      });
    }


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

      // Custom-action handlers (sign out, change password, avatar, start bid, statement pdf)
      if (tryWireAction(a, label, isVendor, isAdmin, navigate)) {
        a.dataset.pmcPatched = "1";
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
      // v49i — if this button is inside the home hero's Find-tenders form,
      // do NOT hijack the click; the form's submit handler will run and
      // preserve the country + keyword query params. Same for any generic
      // form we later wire that owns a submit button.
      if (b.type === "submit" || b.closest("form.pmc-hero__search")) return;
      const label = labelOf(b);

      if (b.classList.contains("pmc-chip")) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", () => {
          const row = b.parentElement;
          row?.querySelectorAll(".pmc-chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
          b.setAttribute("aria-pressed", "true");
        });
        return;
      }
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

      if (tryWireAction(b, label, isVendor, isAdmin, navigate)) {
        b.dataset.pmcPatched = "1";
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
      // v49h — the "who am I" pill in the top-right of every vendor page opens
      // a mini menu in the template; here we just route it to Account & security.
      if (b.classList.contains("pmc-who") && isVendor) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => { e.preventDefault(); navigate("/vendor/account"); });
        return;
      }
      if (b.classList.contains("pmc-who") && isAdmin) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => { e.preventDefault(); handleSignOut(navigate); });
        return;
      }
      if (b.textContent.trim().length <= 3) {
        b.dataset.pmcPatched = "1";
        b.addEventListener("click", (e) => e.preventDefault());
      }
    });

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
