import { useEffect } from "react";
import { useNavigate, useLocation } from "react-router-dom";
import { toast } from "sonner";
import { useUiTheme } from "@/context/UiThemeContext";
import { api, adminApi, vendorApi, bidApi, paymentApi, docusignApi } from "@/lib/api";

/**
 * PMC v49j — Option-E interactivity via GLOBAL EVENT DELEGATION.
 *
 * Previous versions attached listeners per element after route change.
 * That broke whenever a live-data hook (pmcELiveData) rewrote the DOM
 * via innerHTML *after* patching — the listeners died and buttons looked
 * dead. Delegation resolves the action AT CLICK TIME, so DOM churn from
 * live data can never detach our behaviour.
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
  "register first": "/register",
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
  // { rx: /^pay\b/i,                               path: "/vendor/emd" },  // v49m — replaced by handlePayEmd which fires Stripe checkout
  { rx: /upload\s+bank\s+guarantee/i,            path: "/vendor/emd" },
  { rx: /^view\s+bid$/i,                         path: "/vendor/mybids" },
  { rx: /^continue\s+draft$/i,                   path: "/vendor/mybids" },
  { rx: /^view\s+contract$/i,                    path: "/vendor/signatures" },
  { rx: /^track$/i,                              path: "/vendor/mybids" },
  { rx: /^details$/i,                            path: "/vendor/mybids" },
  { rx: /^debrief$/i,                            path: "/vendor/mybids" },
  { rx: /see\s+all.*(open\s+)?notices?/i,        path: "/vendor/tenders" },
  { rx: /saved\s+searches/i,                     path: "/vendor/tenders" },
  // { rx: /review\s*&?\s*sign|sign\s+loa/i,      path: "/vendor/signatures" },  // v49n — handleReviewSign opens DocuSign
  // { rx: /send\s+me\s+the\s+docusign/i,         path: "/vendor/signatures" },  // v49n — handleReviewSign
  // { rx: /^preview$/i,                          path: "/vendor/signatures" },    // v49n — handleReviewSign
  { rx: /add\s+the\s+licence/i,                  path: "/vendor/company" },
  { rx: /^reply$/i,                              path: "/vendor/mybids" },
  { rx: /^review$/i,                             path: "/vendor/reviews" },
  { rx: /leave\s+a\s+review/i,                   path: "/vendor/reviews" },
  { rx: /raise\s+a\s+ticket/i,                   path: "/help" },
  { rx: /^manage$/i,                             path: "/vendor/account" },
  { rx: /^view$/i,                               path: "/vendor/mybids" },
  { rx: /export\s+first/i,                       path: "/vendor/account" },
  { rx: /delete\s+my\s+data/i,                   path: "/vendor/account" },
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

// v49o — Real tab switching. Maps a clicked .pmc-tab to its .dt-sec section
// by heading keyword, hides the rest. Falls back to positional matching.
const TAB_KEYWORDS = {
  overview: ["scope", "overview"],
  eligibility: ["who can bid", "eligibility"],
  documents: ["documents"],
  clarifications: ["clarifications"],
  corrigenda: ["corrigenda"],
};

function switchTabSections(tabEl, tabRow) {
  const pageRoot = tabEl.closest("[data-pmc-e-page]");
  if (!pageRoot) return;
  const secs = Array.from(pageRoot.querySelectorAll(".dt-sec"));
  if (!secs.length) return;
  const key = labelOf(tabEl).replace(/\s*\d+$/, "").trim();
  const keys = TAB_KEYWORDS[key] || [key];
  let matched = false;
  secs.forEach((s) => {
    const h = (s.querySelector("h2")?.textContent || "").trim().toLowerCase();
    const show = keys.some((k) => h.includes(k));
    if (show) matched = true;
    s.style.display = show ? "" : "none";
  });
  if (!matched) {
    const tabs = Array.from(tabRow.querySelectorAll(".pmc-tab"));
    const idx = tabs.indexOf(tabEl);
    if (idx < secs.length) {
      secs.forEach((s, i) => { s.style.display = i === idx ? "" : "none"; });
    } else {
      // v49o — e.g. a "Corrigenda" tab on a notice whose corrigenda only live
      // in the Key-dates timeline: never blank the page. Keep the first
      // (Overview) section visible and prepend a one-line note.
      secs.forEach((s, i) => { s.style.display = i === 0 ? "" : "none"; });
      const first = secs[0];
      if (first && !first.querySelector(".pmc-tab-empty-note")) {
        const note = document.createElement("div");
        note.className = "pmc-tab-empty-note pmc-muted";
        note.style.cssText = "margin-top:10px;padding:10px 14px;border:1px dashed var(--line, rgba(0,0,0,.15));border-radius:8px;font-size:13px";
        note.textContent = `No ${key} section published on this notice — check the Key dates timeline on the right.`;
        first.appendChild(note);
      }
    }
  }
  // Bring the sections back into view after switching
  tabRow.scrollIntoView({ behavior: "smooth", block: "start" });
}

function applyTabDefaults() {
  document.querySelectorAll("[data-pmc-e-page] .pmc-tabs").forEach((row) => {
    const sel = row.querySelector('.pmc-tab[aria-selected="true"]') || row.querySelector(".pmc-tab");
    if (sel) switchTabSections(sel, row);
  });
}

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

const isVendorAuthed = () => /(?:^|;\s*)csrf_token=/.test(document.cookie || "");

async function handleSignOut(navigate) {
  try { await Promise.allSettled([adminApi.logout?.(), vendorApi.logout?.()]); } catch (_) { /* ignore */ }
  toast.success("Signed out");
  navigate("/login");
}

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
      if (file.size > 2_500_000) { toast.error("Pick an image under 2.5 MB."); return; }
      const reader = new FileReader();
      reader.onload = async () => {
        try {
          await vendorApi.uploadAvatar(String(reader.result));
          // v49k — show the new photo immediately in every .pmc-avatar badge
          document.querySelectorAll(".pmc-avatar").forEach((el) => {
            el.innerHTML = "";
            const img = document.createElement("img");
            img.src = String(reader.result);
            img.alt = "avatar";
            img.style.cssText = "width:100%;height:100%;object-fit:cover;border-radius:inherit";
            el.appendChild(img);
          });
          toast.success("Avatar updated");
        } catch (err) {
          toast.error(err?.response?.data?.detail || "Couldn't upload that photo.");
        }
      };
      reader.readAsDataURL(file);
    });
    document.body.appendChild(input);
  }
  input.click();
}

// v49k — .pmc-who identity pill dropdown. The static templates never wired
// the aria-haspopup="menu" pill, so vendors had NO sign-out button and no
// avatar control. This lazily builds a real menu and positions it under the
// clicked pill; delegation in onClick keeps it working across DOM churn.
function toggleWhoMenu(pill, isVendor, navigate) {
  let menu = document.getElementById("__pmc_who_menu");
  if (menu) { menu.remove(); return; }
  menu = document.createElement("div");
  menu.id = "__pmc_who_menu";
  menu.setAttribute("data-testid", "pmc-who-menu");
  menu.style.cssText = "position:fixed;z-index:1100;min-width:220px;background:#F7F3EA;border:1px solid rgba(15,59,46,.15);border-radius:12px;box-shadow:0 16px 40px rgba(6,32,26,.28);padding:6px;font-size:14px";
  const item = (label, testid) =>
    `<button type="button" data-testid="${testid}" data-action="${testid}"
      style="display:block;width:100%;text-align:left;padding:10px 12px;border:0;border-radius:8px;background:transparent;color:#0F3B2E;font-size:14px;cursor:pointer"
      onmouseover="this.style.background='rgba(15,59,46,.07)'" onmouseout="this.style.background='transparent'">${label}</button>`;
  menu.innerHTML = isVendor
    ? item("Account & security", "who-menu-account")
      + item("Change photo", "who-menu-photo")
      + `<hr style="border:0;border-top:1px solid rgba(15,59,46,.12);margin:4px 8px" />`
      + item("Sign out", "who-menu-signout")
    : item("Sign out", "who-menu-signout");
  document.body.appendChild(menu);
  const r = pill.getBoundingClientRect();
  menu.style.top = `${r.bottom + 8}px`;
  menu.style.right = `${Math.max(8, window.innerWidth - r.right)}px`;

  const onDoc = (e) => { if (!menu.contains(e.target) && e.target !== pill) { menu.remove(); document.removeEventListener("click", onDoc, true); } };
  document.addEventListener("click", onDoc, true);

  menu.querySelectorAll("[data-action]").forEach((b) => {
    b.addEventListener("click", (e) => {
      e.preventDefault(); e.stopPropagation();
      const act = b.getAttribute("data-action");
      menu.remove();
      if (act === "who-menu-account") navigate("/vendor/account");
      else if (act === "who-menu-photo") openAvatarPicker();
      else if (act === "who-menu-signout") handleSignOut(navigate);
    });
  });
}

// v49j — In-app change-password modal (current + new + confirm) for the
// vendor Account & Security page. Regular UX, no email round-trip.
function openChangePasswordModal() {
  let ov = document.getElementById("__pmc_vcp_modal");
  if (ov) { ov.style.display = "flex"; return; }
  ov = document.createElement("div");
  ov.id = "__pmc_vcp_modal";
  ov.setAttribute("data-testid", "vendor-change-password-modal");
  ov.style.cssText = "position:fixed;inset:0;z-index:1000;display:flex;align-items:center;justify-content:center;background:rgba(6,32,26,.55);backdrop-filter:blur(3px);padding:20px";
  ov.innerHTML = `
    <div style="background:#F7F3EA;border-radius:14px;width:440px;max-width:100%;box-shadow:0 24px 60px rgba(6,32,26,.35);overflow:hidden">
      <div style="background:#06201A;padding:20px 24px">
        <div style="font-size:11px;letter-spacing:2px;text-transform:uppercase;color:#C9A24B;margin-bottom:4px">Account &amp; security</div>
        <div style="font-size:20px;font-weight:600;color:#F7F3EA">Change your password</div>
      </div>
      <form id="__pmc_vcp_form" style="padding:24px">
        <label style="display:block;font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#5B6B63;margin-bottom:6px">Current password</label>
        <input id="__pmc_vcp_cur" type="password" required autocomplete="current-password"
          style="width:100%;height:42px;padding:0 12px;border:1px solid rgba(15,59,46,.2);border-radius:8px;background:#fff;margin-bottom:14px;font-size:14px" />
        <label style="display:block;font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#5B6B63;margin-bottom:6px">New password</label>
        <input id="__pmc_vcp_new" type="password" required minlength="8" autocomplete="new-password"
          style="width:100%;height:42px;padding:0 12px;border:1px solid rgba(15,59,46,.2);border-radius:8px;background:#fff;margin-bottom:14px;font-size:14px" />
        <label style="display:block;font-size:12px;letter-spacing:1px;text-transform:uppercase;color:#5B6B63;margin-bottom:6px">Confirm new password</label>
        <input id="__pmc_vcp_cfm" type="password" required autocomplete="new-password"
          style="width:100%;height:42px;padding:0 12px;border:1px solid rgba(15,59,46,.2);border-radius:8px;background:#fff;font-size:14px" />
        <div id="__pmc_vcp_err" style="display:none;color:#B3261E;font-size:13px;margin-top:10px"></div>
        <div style="display:flex;gap:10px;margin-top:20px">
          <button type="submit" id="__pmc_vcp_submit"
            style="flex:1;height:44px;border:0;border-radius:8px;background:#0F3B2E;color:#F7F3EA;font-weight:600;font-size:14px;cursor:pointer">Update password</button>
          <button type="button" id="__pmc_vcp_cancel"
            style="height:44px;padding:0 18px;border:1px solid rgba(15,59,46,.25);border-radius:8px;background:transparent;color:#0F3B2E;font-size:14px;cursor:pointer">Cancel</button>
        </div>
      </form>
    </div>`;
  document.body.appendChild(ov);

  const close = () => { ov.style.display = "none"; };
  ov.addEventListener("click", (e) => { if (e.target === ov) close(); });
  ov.querySelector("#__pmc_vcp_cancel").addEventListener("click", close);
  document.addEventListener("keydown", function esc(e) {
    if (e.key === "Escape" && ov.style.display !== "none") close();
  });

  ov.querySelector("#__pmc_vcp_form").addEventListener("submit", async (e) => {
    e.preventDefault();
    const cur = ov.querySelector("#__pmc_vcp_cur").value;
    const nxt = ov.querySelector("#__pmc_vcp_new").value;
    const cfm = ov.querySelector("#__pmc_vcp_cfm").value;
    const err = ov.querySelector("#__pmc_vcp_err");
    const btn = ov.querySelector("#__pmc_vcp_submit");
    err.style.display = "none";
    if (nxt.length < 8) { err.textContent = "New password must be at least 8 characters."; err.style.display = "block"; return; }
    if (nxt !== cfm) { err.textContent = "New passwords don't match."; err.style.display = "block"; return; }
    if (nxt === cur) { err.textContent = "New password must differ from the current one."; err.style.display = "block"; return; }
    btn.disabled = true; btn.textContent = "Updating…";
    try {
      await vendorApi.changePassword(cur, nxt);
      toast.success("Password updated.");
      ov.querySelector("#__pmc_vcp_cur").value = "";
      ov.querySelector("#__pmc_vcp_new").value = "";
      ov.querySelector("#__pmc_vcp_cfm").value = "";
      close();
    } catch (e2) {
      err.textContent = e2?.response?.data?.detail || "Couldn't update the password. Check your current password.";
      err.style.display = "block";
    } finally {
      btn.disabled = false; btn.textContent = "Update password";
    }
  });
}

function handleChangeButton(btn, navigate) {
  const row = btn.closest("div, tr, section");
  const context = ((row && row.textContent) || "").toLowerCase();
  if (/avatar|photo|logo/.test(context)) { openAvatarPicker(); return; }
  if (/password/.test(context)) { openChangePasswordModal(); return; }
  if (/refund\s+account/.test(context)) {
    toast.info("Refund-account changes need PMC approval. Ask your desk to open a ticket.");
    return;
  }
  navigate("/vendor/account");
}

function extractNoticeRef(scopeEl) {
  if (!scopeEl) return null;
  // v49o+ fix — walk up to nearest card/row so buttons without a wrapping
  // data-notice-ref (e.g. <a>Start bid</a> inside an article) still resolve.
  const card =
    scopeEl.closest("[data-notice-ref]") ||
    scopeEl.closest("article.pmc-tender, article, .pmc-tender, .pmc-bidrow, .tl-row, tr, li") ||
    scopeEl;
  let ref = card.getAttribute && card.getAttribute("data-notice-ref");
  if (ref) return ref;
  const refEl = card.querySelector && card.querySelector(".pmc-ref");
  if (refEl) {
    const m = (refEl.textContent || "").match(/PMC-NOT-\d{4}-\d+/);
    if (m) return m[0];
  }
  const m = (card.textContent || "").match(/PMC-NOT-\d{4}-\d+/);
  if (m) return m[0];
  // Fallback: check the anchor's own href like /notices/PMC-NOT-YYYY-###
  if (scopeEl.tagName === "A") {
    const href = scopeEl.getAttribute("href") || "";
    const m2 = href.match(/PMC-NOT-\d{4}-\d+/);
    if (m2) return m2[0];
  }
  return null;
}

function handleStartBid(el, isPublic, navigate) {
  let ref = extractNoticeRef(el);
  if (!ref) {
    // On the public notice detail page the ref lives in the URL
    const m = window.location.pathname.match(/\/notices\/(PMC-NOT-\d{4}-\d+)/);
    if (m) ref = m[1];
  }
  if (isPublic) {
    if (!isVendorAuthed()) { navigate("/register"); return; }
    navigate(ref ? `/vendor/bid/new/${ref}` : "/vendor/tenders");
    return;
  }
  navigate(ref ? `/vendor/bid/new/${ref}` : "/vendor/tenders");
}

// v49v — Safari popup fix. window.open() AFTER an await is treated as
// non-user-initiated and silently blocked (Safari strictest, iOS worst).
// Open a blank tab synchronously inside the click gesture, then steer it
// to the real URL once the API responds. If even the sync open is blocked,
// fall back to same-tab navigation so the user always reaches DocuSign.
function _openSteeredTab() {
  const w = window.open("", "_blank");
  if (w) {
    try {
      w.document.write('<p style="font-family:sans-serif;padding:32px;color:#0F3B2E">Contacting DocuSign&hellip;</p>');
    } catch (_) { /* ignore */ }
  }
  return w;
}
function _steerTab(w, url, okMsg) {
  if (w) {
    try { w.location.href = url; } catch (_) { window.location.href = url; }
    if (okMsg) toast.success(okMsg);
  } else {
    window.location.href = url; // popup blocked even synchronously — same tab
  }
}
function _closeTab(w) { try { w && w.close(); } catch (_) { /* ignore */ } }

// v49n — Review & sign / Preview on the vendor Signatures page.
// Prefers the specific envelope attached to the clicked card/row via
// data-envelope-id (set by useVendorSignaturesLive); otherwise opens the
// first pending envelope. Mints a fresh recipient-view URL via
// POST /docusign/mine/{id}/sign and opens it in a new tab.
async function handleReviewSign(el, navigate) {
  const w = _openSteeredTab(); // v49v — must precede every await (Safari)
  try {
    const envId = el.closest("[data-envelope-id]")?.getAttribute("data-envelope-id");
    toast.info("Opening DocuSign…");
    if (envId) {
      const r = await docusignApi.resumeSign(envId);
      if (r?.signing_url) {
        _steerTab(w, r.signing_url, "DocuSign signing window opened in a new tab.");
        return;
      }
      _closeTab(w);
      toast.error("DocuSign didn't return a signing link. Ask PMC to resend.");
      return;
    }
    const data = await docusignApi.listMine();
    const items = data?.items || [];
    const pending = items.filter((e) => e.status === "sent" || e.status === "delivered");
    if (!pending.length) {
      _closeTab(w);
      if (items.length) toast.info("Every envelope on your account is already signed.");
      else toast.info("No documents awaiting your signature right now.");
      return;
    }
    const r = await docusignApi.resumeSign(pending[0].envelope_id);
    if (r?.signing_url) {
      _steerTab(w, r.signing_url, "DocuSign signing window opened in a new tab.");
    } else {
      _closeTab(w);
      toast.error("DocuSign didn't return a signing link. Ask PMC to resend.");
    }
  } catch (err) {
    _closeTab(w);
    const s = err?.response?.status;
    if (s === 401) { navigate("/login"); return; }
    toast.error(err?.response?.data?.detail || "Couldn't open the signing view.");
  }
}

// v49m — Pay EMD click now genuinely opens the Stripe checkout instead of
// just navigating to the deposits list. Flow:
//   1. Look at the clicked element's parent row for a bid reference
//      (`.pmc-ref` text or a `PMC-BID-YYYY-#####` regex match).
//   2. If a specific bid_ref is found → fetch /bids/mine → resolve to id.
//   3. If no ref (top-of-page "Pay EMD" button) → fetch /bids/mine and
//      collect every `emd_pending` bid. If exactly one, use that one.
//      If several, drop the user on /vendor/emd with a toast.
//   4. Call POST /payments/emd/checkout via paymentApi.checkout and
//      HARD-redirect the tab to the returned Stripe checkout_url.
async function handlePayEmd(el, navigate) {
  try {
    const row = el.closest("tr, li, article, .pmc-bidrow, .pmc-tender, [data-bid-ref]");
    let bidRef = row?.getAttribute?.("data-bid-ref") || null;
    if (!bidRef && row) {
      const refEl = row.querySelector(".pmc-ref");
      const src = (refEl?.textContent || row.textContent || "");
      const m = src.match(/PMC-BID-\d{4}-\d+/);
      if (m) bidRef = m[0];
    }

    const bids = await bidApi.mine().catch(() => []);
    const pending = (Array.isArray(bids) ? bids : []).filter((b) => b.status === "emd_pending");
    if (!pending.length) {
      toast.info("No EMD payments are pending on your account.");
      navigate("/vendor/emd");
      return;
    }

    let target = bidRef ? pending.find((b) => b.bid_ref === bidRef) : null;
    if (!target) target = pending[0]; // v49m — always pick the first pending
                                      // when the banner is clicked from a
                                      // non-row context so the user always
                                      // lands on Stripe, not the list.
    if (!target.id) {
      toast.error("Couldn't resolve that bid. Try again from My bids.");
      navigate("/vendor/mybids");
      return;
    }

    toast.info("Opening secure Stripe checkout…");
    const chk = await paymentApi.checkout(target.id, window.location.origin);
    if (chk?.checkout_url) {
      window.location.href = chk.checkout_url;
    } else {
      toast.error("Payment gateway did not return a checkout URL.");
      navigate("/vendor/emd");
    }
  } catch (err) {
    const s = err?.response?.status;
    if (s === 401) { navigate("/login"); return; }
    toast.error(err?.response?.data?.detail || "Couldn't start the EMD payment.");
    navigate("/vendor/emd");
  }
}

function handleStatementPdf(navigate) {
  toast.info("Generating your EMD statement…");
  // v49l — hit the real endpoint. Blob download so the browser saves with the
  // Content-Disposition filename regardless of same-origin quirks.
  fetch(`${window.location.origin}/api/v1/payments/emd/statement.pdf`, {
    method: "GET", credentials: "include",
  })
    .then(async (r) => {
      if (!r.ok) throw new Error(String(r.status));
      const blob = await r.blob();
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "PMC-EMD-Statement.pdf";
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
      toast.success("Statement downloaded");
    })
    .catch(() => {
      toast.error("Couldn't generate the statement. Sign in again and retry.");
      navigate("/vendor/emd");
    });
}

// v49l — Sign out this device only (self logout) vs. sign out every OTHER device.
async function handleSignOutOthers(navigate) {
  try {
    await vendorApi.revokeOtherSessions();
    toast.success("Signed out on every other device.");
  } catch (_) {
    toast.error("Couldn't revoke the other sessions. Try again.");
  }
}

// Row-level sign-out on the "Where you're signed in" table. Backend does
// not yet track individual devices, so any single-row sign-out revokes all
// non-current sessions (equivalent to sign-out-everywhere-else). Toasts a
// truthful message so users know what happened.
async function handleSignOutRow(el, navigate) {
  const tr = el.closest("tr");
  const label = (tr && tr.querySelector("td:first-child")?.textContent || "another device").trim();
  const isCurrent = tr && !!tr.querySelector(".pmc-pill--brand");
  if (isCurrent) {
    return handleSignOut(navigate);
  }
  try {
    await vendorApi.revokeOtherSessions();
    if (tr) { tr.style.opacity = "0.5"; tr.style.pointerEvents = "none"; }
    toast.success(`Signed out ${label}. Other devices will need to sign in again.`);
  } catch (_) {
    toast.error("Couldn't revoke that session.");
  }
}

function handleDownload(el, isPublic, navigate) {
  // v49r — a REAL backend file href must not fall through to the generic
  // href handler (which would push /api/... into the SPA router and show a
  // dead page). Force the attachment download right here instead.
  const raw = el.tagName === "A" ? (el.getAttribute("href") || "") : "";
  if (raw && raw !== "#" && !raw.startsWith("#") && !raw.startsWith("mailto:")) {
    if (raw.startsWith("/api/")) {
      const sep = raw.includes("?") ? "&" : "?";
      const a = document.createElement("a");
      a.href = `${raw}${sep}download=1`;
      a.download = "";
      a.rel = "noopener";
      document.body.appendChild(a);
      a.click();
      a.remove();
      toast.success("Download started");
      return true;
    }
    return false;
  }
  const row = el.closest(".pmc-docrow") || el.closest("[data-doc-url]");
  const url = (row && (row.getAttribute("data-doc-url") || row.querySelector("[data-doc-url]")?.getAttribute("data-doc-url"))) || null;
  if (url) {
    // Force a real download (backend serves ?download=1 as attachment).
    // A temp <a download> click works on mobile Safari where window.open is blocked.
    const sep = url.includes("?") ? "&" : "?";
    const a = document.createElement("a");
    a.href = `${url}${sep}download=1`;
    a.download = "";
    a.rel = "noopener";
    document.body.appendChild(a);
    a.click();
    a.remove();
    toast.success("Download started");
    return true;
  }
  if (isPublic) {
    toast.info("Sign in to download tender documents. New supplier? Register from the sign-in page.");
    navigate("/login");
    return true;
  }
  toast.info("Documents are issued to registered bidders by the tender desk.");
  return true;
}

// v49p — Signatures page document actions. Preview/View open the envelope's
// current PDF in a new tab (inline), Download saves it (attachment). The
// signing ceremony itself stays with handleReviewSign.
async function handleSigDoc(el, mode, navigate) {
  // v49v — Safari blocks window.open after an await; open the tab inside
  // the click gesture (preview mode only) and steer once the PDF is ready.
  const w = mode === "download" ? null : _openSteeredTab();
  try {
    const envId = el.closest("[data-envelope-id]")?.getAttribute("data-envelope-id");
    if (!envId) { _closeTab(w); toast.info("This document isn't linked to an envelope yet."); return; }
    toast.info(mode === "download" ? "Preparing your download…" : "Opening the document…");
    const blob = await docusignApi.downloadDocPdf(envId, mode === "download" ? "attachment" : "inline");
    const url = URL.createObjectURL(blob);
    if (mode === "download") {
      const a = document.createElement("a");
      a.href = url;
      a.download = `PMC-${envId}.pdf`;
      document.body.appendChild(a); a.click(); a.remove();
      setTimeout(() => URL.revokeObjectURL(url), 30000);
      toast.success("Document downloaded.");
    } else {
      _steerTab(w, url, null);
    }
  } catch (err) {
    _closeTab(w);
    const s = err?.response?.status;
    if (s === 401) { navigate("/login"); return; }
    toast.error(err?.response?.data?.detail || "Couldn't open that document.");
  }
}

// v49p — Alerts page "Mark all read": hits the vendor read-all endpoint and
// clears the unread styling in place.
async function handleMarkAllRead(el) {
  try {
    const { api } = await import("@/lib/api");
    await api.post("/api/v1/notifications/vendor/read-all");
    const root = el.closest('[data-pmc-e-page="vendor-alerts-e"]');
    root?.querySelectorAll(".al-r.un").forEach((r) => r.classList.remove("un"));
    const h1 = root?.querySelector("h1");
    if (h1) h1.textContent = h1.textContent.replace(/·\s*\d+\s*need action/i, "· 0 need action");
    toast.success("All alerts marked as read.");
  } catch (_) {
    toast.error("Couldn't mark alerts as read. Try again.");
  }
}

// v49p — Alerts page tab filter: All / Needs action / Tenders / Payments
// filter the .al-r alert rows in place (no page reload).
function filterAlertRows(tabEl) {
  const root = tabEl.closest('[data-pmc-e-page="vendor-alerts-e"]');
  if (!root) return;
  const key = labelOf(tabEl).replace(/\s*\d+$/, "").trim();
  root.querySelectorAll(".al-r").forEach((r) => {
    const txt = (r.textContent || "").toLowerCase();
    let show = true;
    if (key === "needs action") show = r.classList.contains("un");
    else if (key === "tenders") show = /corrigendum|tender|notice|bid/.test(txt) && !/emd|escrow|payment/.test(txt);
    else if (key === "payments") show = /emd|escrow|payment|invoice|refund/.test(txt);
    r.style.display = show ? "" : "none";
  });
}

// v49p — My bids tab filter: Active / Drafts / Closed / Withdrawn filter the
// bids table rows by their status pill text. The "Recently decided" panel is
// the historical record of CLOSED bids — it shows only on the Closed tab,
// otherwise the page always shows rows and the tabs look dead (user report).
function filterMyBidsRows(tabEl) {
  const root = tabEl.closest('[data-pmc-e-page="vendor-mybids-e"]');
  if (!root) return;
  const key = labelOf(tabEl).replace(/\s*\d+$/, "").trim();
  const panels = [...root.querySelectorAll("section.pmc-panel")];
  const main = panels[0];      // live bids table
  const decided = panels[1];   // "Recently decided"
  if (!main) return;
  let visible = 0;
  main.querySelectorAll("tbody tr").forEach((tr) => {
    const pill = (tr.querySelector(".pmc-pill")?.textContent || "").toLowerCase();
    let show = true;
    if (key === "drafts") show = pill.includes("draft");
    else if (key === "closed") show = /award|closed|decid|lost/.test(pill);
    else if (key === "withdrawn") show = pill.includes("withdraw");
    else show = !/(draft|withdraw|award|closed|lost|decid)/.test(pill); // active
    tr.style.display = show ? "" : "none";
    if (show) visible += 1;
  });
  // Hide the Recently-decided panel (and its heading) unless Closed is active
  if (decided) {
    const showDecided = key === "closed";
    decided.style.display = showDecided ? "" : "none";
    let sib = decided.previousElementSibling;
    while (sib && sib !== main) {
      sib.style.display = showDecided ? "" : "none";
      sib = sib.previousElementSibling;
    }
  }
  // Empty-state note when nothing matches
  let note = main.querySelector(".pmc-tab-empty-note");
  if (visible === 0) {
    if (!note) {
      note = document.createElement("div");
      note.className = "pmc-tab-empty-note pmc-muted";
      note.style.cssText = "padding:24px 20px;text-align:center;font-size:14px";
      main.appendChild(note);
    }
    note.textContent = `No ${key} bids right now.`;
    note.style.display = "";
  } else if (note) {
    note.style.display = "none";
  }
}

// Central click action resolver. Returns true when the click was owned.
function resolveClickAction(el, label, { isVendor, isAdmin, isPublic, pageId }, navigate) {
  if (/^sign\s*out\s+everywhere\s+else$/i.test(label)) {
    handleSignOutOthers(navigate); return true;
  }
  if (/^sign\s*out(\s+everywhere\s+else)?$/i.test(label) || /^log\s*out$/i.test(label)) {
    // Row-level sign-out lives inside a <tr>: revoke-others; standalone header
    // sign-out logs the current session out.
    if (el.closest && el.closest("tr")) { handleSignOutRow(el, navigate); return true; }
    handleSignOut(navigate); return true;
  }
  if (isVendor && /change\s+(avatar|photo|logo)|upload\s+photo/i.test(label)) { openAvatarPicker(); return true; }
  if (isVendor && /^change\s+password$/i.test(label)) { openChangePasswordModal(); return true; }
  if (isVendor && /^change$/i.test(label)) { handleChangeButton(el, navigate); return true; }
  // v49p — Signatures page: Preview/View open the document PDF, Download
  // saves it, Continue resumes the signing ceremony. These run before the
  // generic review&sign/preview rules so the labels stay page-specific.
  if (pageId === "vendor-signatures-e") {
    if (/^(preview|view)$/i.test(label)) { handleSigDoc(el, "preview", navigate); return true; }
    if (/^download$/i.test(label)) { handleSigDoc(el, "download", navigate); return true; }
    if (/^continue$/i.test(label)) { handleReviewSign(el, navigate); return true; }
  }
  // v49p — Alerts page actions
  if (pageId === "vendor-alerts-e") {
    if (/^mark all read$/i.test(label)) { handleMarkAllRead(el); return true; }
    if (/^see change$/i.test(label)) { const r = extractNoticeRef(el); navigate(r ? `/notices/${r}` : "/tenders/live"); return true; }
    if (/^see tenders$/i.test(label)) { navigate("/vendor/tenders"); return true; }
    if (/^alert settings$/i.test(label)) { navigate("/vendor/account"); return true; }
  }
  if (isVendor && /review\s*&?\s*sign|sign\s+loa/i.test(label)) { handleReviewSign(el, navigate); return true; }
  if (isVendor && /^preview$/i.test(label)) { handleReviewSign(el, navigate); return true; }
  if (isVendor && /send\s+me\s+the\s+docusign/i.test(label)) { handleReviewSign(el, navigate); return true; }
  if (isVendor && /^pay(\s+emd)?$/i.test(label)) { handlePayEmd(el, navigate); return true; }
  if (isVendor && el.hasAttribute("data-vemd-receipt-bid")) {
    const bidId = el.getAttribute("data-vemd-receipt-bid");
    const bidRef = el.getAttribute("data-vemd-receipt-ref") || "";
    paymentApi.receiptPdf(bidId, bidRef)
      .catch((err) => toast.error(err?.response?.data?.detail || "Receipt download failed."));
    return true;
  }
  if (/^start\s+bid$/i.test(label)) { handleStartBid(el, isPublic, navigate); return true; }
  if (isVendor && /statement\s*\(?pdf\)?/i.test(label)) { handleStatementPdf(navigate); return true; }
  if (/^download(\s+pack)?$/i.test(label)) { return handleDownload(el, isPublic, navigate); }
  if (/^follow$/i.test(label)) {
    if (isPublic && !isVendorAuthed()) { toast.info("Sign in to follow this notice."); navigate("/login"); }
    else toast.success("You're following this notice — updates go to your inbox.");
    return true;
  }
  if (/ask\s+a\s+question/i.test(label)) {
    if (isPublic && !isVendorAuthed()) { toast.info("Sign in to ask the tender desk a question."); navigate("/login"); }
    else toast.info("Email the tender desk at tenders@pmcmanagers.com with the notice reference.");
    return true;
  }
  return false;
}

export default function PmcLinkPatcher() {
  const { isE } = useUiTheme();
  const navigate = useNavigate();
  const location = useLocation();

  // v49o — apply default tab visibility on every route change (the live-data
  // hooks rewrite the DOM after mount, so we run twice with a delay).
  useEffect(() => {
    if (!isE) return;
    const t1 = setTimeout(applyTabDefaults, 150);
    const t2 = setTimeout(applyTabDefaults, 900);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [isE, location.pathname]);

  // v49u — live unread-count on every .pmc-bell badge. Runs on each route
  // change; vendor pages query the vendor endpoint, admin pages the admin
  // one. Badge hides itself when there is nothing unread.
  useEffect(() => {
    if (!isE) return;
    let cancelled = false;
    const refresh = async () => {
      const pageEl = document.querySelector("[data-pmc-e-page]");
      const pageId = pageEl?.getAttribute("data-pmc-e-page") || "";
      const isVendor = pageId.startsWith("vendor-");
      const isAdmin = pageId.startsWith("admin-");
      if (!isVendor && !isAdmin) return;
      try {
        const r = await api.get(isVendor ? "/api/v1/notifications/vendor/mine" : "/api/v1/notifications");
        if (cancelled) return;
        const items = Array.isArray(r.data) ? r.data : (r.data.items || []);
        const unread = items.filter((n) => !n.read && !n.read_at).length;
        document.querySelectorAll(".pmc-bell__n").forEach((el) => {
          el.textContent = String(unread);
          el.style.display = unread ? "" : "none";
        });
      } catch (_) { /* not signed in for this realm — leave badge alone */ }
    };
    refresh();
    const t = setTimeout(refresh, 800);
    return () => { cancelled = true; clearTimeout(t); };
  }, [isE, location.pathname]);

  useEffect(() => {
    if (!isE) return;

    const onClick = (e) => {
      // v49p — Help drawer scrim taps must work for BOTH the React drawer
      // (mounted at app level, outside any [data-pmc-e-page] root) and the
      // static per-page drawers. Handle before the root guard below, and
      // sync the React drawer's state by clicking its own Close button so a
      // later FAB click doesn't no-op on stale state.
      if (e.target.classList?.contains("pmc-drawer-scrim")) {
        document.querySelector('[data-testid="pmc-help-close"]')?.click();
        document.documentElement.classList.remove("pmc-help-open");
        return;
      }

      const root = e.target.closest("[data-pmc-e-page]");
      if (!root) return;
      const pageId = root.getAttribute("data-pmc-e-page") || "";
      const isVendor = pageId.startsWith("vendor-");
      const isAdmin = pageId.startsWith("admin-");
      const isPublic = !isVendor && !isAdmin;
      const ctx = { isVendor, isAdmin, isPublic, pageId };

      // KPI tiles (vendor pages)
      const kpi = e.target.closest(".pmc-kpi");
      if (kpi && isVendor) {
        const label = (kpi.querySelector(".l")?.textContent || "").trim().toLowerCase();
        const target = VENDOR_KPI_TILES[label];
        if (target) { e.preventDefault(); navigate(target); return; }
      }

      const el = e.target.closest("a, button");
      if (!el) return;

      // Never hijack real form submit buttons; the hero search form has its
      // own submit listener below. Note: a <button> with no type attribute
      // defaults to "submit", so we must check form membership, not .type.
      if (el.tagName === "BUTTON" && el.closest("form")) return;

      const label = labelOf(el);

      // v49u — Notification bell: vendor pages → /vendor/alerts,
      // admin pages → /admin/e/events. Previously the bell was completely
      // dead (no count, no click).
      if (el.classList.contains("pmc-bell") || el.closest(".pmc-bell")) {
        e.preventDefault();
        navigate(isVendor ? "/vendor/alerts" : isAdmin ? "/admin/e/events" : "/login");
        return;
      }

      // Chips + tabs — cosmetic toggles + real section switching (v49o)
      if (el.classList.contains("pmc-chip") && el.tagName === "BUTTON") {
        e.preventDefault();
        const row = el.parentElement;
        row?.querySelectorAll(".pmc-chip").forEach((c) => c.setAttribute("aria-pressed", "false"));
        el.setAttribute("aria-pressed", "true");
        return;
      }
      if (el.classList.contains("pmc-tab")) {
        e.preventDefault();
        const row = el.parentElement;
        row?.querySelectorAll(".pmc-tab").forEach((t) => t.setAttribute("aria-selected", "false"));
        el.setAttribute("aria-selected", "true");
        switchTabSections(el, row);
        // v49p — pages whose tabs filter rows instead of switching sections
        if (pageId === "vendor-alerts-e") filterAlertRows(el);
        else if (pageId === "vendor-mybids-e") filterMyBidsRows(el);
        return;
      }

      // Brand → portal home
      if (el.classList.contains("pmc-brand") || el.querySelector(".pmc-brand__n")) {
        e.preventDefault();
        navigate(isVendor ? "/vendor" : isAdmin ? "/admin/e/dashboard" : "/");
        return;
      }

      // v49x — "Open the full Help Centre" anchors carry a real /help
      // href. Navigate there instead of re-opening the drawer — the
      // /help|faqs/ label regex below was swallowing them, which is why
      // the button looked dead.
      const helpHref = el.tagName === "A" ? (el.getAttribute("href") || "") : "";
      if (!el.hasAttribute("data-help-open") && helpHref.startsWith("/help")) {
        e.preventDefault();
        document.querySelector('[data-testid="pmc-help-close"]')?.click();
        document.documentElement.classList.remove("pmc-help-open");
        navigate(helpHref);
        return;
      }

      // Help triggers
      // v49w — direct open via a custom event so the React PmcHelpDrawer
      // state (open=true) is actually set. Previous code did
      // `document.querySelector(".pmc-helpfab")?.click()` which returned
      // the FIRST matching button on the page — usually a static per-page
      // .pmc-helpfab, whose click just re-fired this handler. That is
      // why the drawer never opened on the very first page load but did
      // after navigating away and back (which re-ordered the FABs).
      if (el.hasAttribute("data-help-open") || /help|faqs?|what is emd\?/.test(label)) {
        e.preventDefault();
        window.dispatchEvent(new CustomEvent("pmc:open-help"));
        return;
      }

      // v49p — Help drawer CLOSE. Every generated page embeds its own static
      // .pmc-drawer whose Close button carries data-help-close; those buttons
      // were dead (only Esc worked) because nothing delegated the click.
      if (el.hasAttribute("data-help-close") || el.closest("[data-help-close]")) {
        e.preventDefault();
        // Sync the React drawer's state as well, otherwise the next FAB
        // click can no-op on stale open-state.
        const reactClose = document.querySelector('[data-testid="pmc-help-close"]');
        if (reactClose && reactClose !== el && !el.contains(reactClose)) reactClose.click();
        document.documentElement.classList.remove("pmc-help-open");
        return;
      }
      // Scrim tap on a static drawer also closes it (React scrim is handled
      // at the top of this listener, before the page-root guard).
      if (el.classList.contains("pmc-drawer-scrim")) {
        document.documentElement.classList.remove("pmc-help-open");
        return;
      }

      // v49n — ACTION LABELS WIN OVER REAL HREFS. The live-data hooks stamp
      // hrefs like /notices/<ref> onto buttons that must actually DO things
      // (Start bid → bid form, Pay EMD → Stripe, Review & sign → DocuSign).
      // If we honoured the href first, those buttons would just navigate.
      // v50p — fully-React pages own their clicks: never let the legacy
      // action-label map hijack them. A "Download" button on the rewritten
      // Signatures page was being swallowed by handleSigDoc's envelope
      // lookup, surfacing "This document isn't linked to an envelope yet."
      // while the component's own onClick never ran.
      const REACT_OWNED = pageId === "vendor-home-e"
        || pageId === "vendor-find-tenders-e"
        || pageId === "vendor-signatures-e"
        || pageId === "vendor-account-e"
        || pageId === "vendor-company-kyc-e"
        || pageId === "vendor-reviews-e"
        || pageId === "vendor-bid-workspace-e"
        || pageId === "vendor-mybids-e";
      // v52bm — a wired admin control (carries data-testid by project
      // mandate) owns its own onClick; the static-template action/label
      // maps below must never hijack it. The "Create notice" submit was
      // being routed to /admin/e/tender-builder even when client-side
      // validation failed — destroying the in-progress form and dumping
      // the user on the Tender builder page with just a floating toast.
      const isWiredAdminControl = isAdmin && el.hasAttribute("data-testid");
      if (!REACT_OWNED && !isWiredAdminControl && resolveClickAction(el, label, ctx, navigate)) { e.preventDefault(); return; }

      // Real href — backend file/API URLs and static downloads must NOT go
      // through the SPA router (no route matches them → dead page). Let the
      // browser open them natively; only true app paths use the router.
      const href = el.tagName === "A" ? (el.getAttribute("href") || "") : "";
      if (href && href !== "#" && !href.startsWith("#") && !href.startsWith("mailto:")) {
        if (href.startsWith("/api/") || href.startsWith("/downloads/")) return;
        if (href.startsWith("/") && !href.startsWith("//")) { e.preventDefault(); navigate(href); }
        return;
      }

      // v50v — React-owned pages fully own their click handlers; skip the
      // legacy label-map (which routed "Reply" to /vendor/mybids, "View" to
      // the bids list, etc.) so component onClick runs intact.
      // v52bm — same treatment for wired admin controls (see above).
      if (REACT_OWNED || isWiredAdminControl) {
        if (href === "#") e.preventDefault();
        return;
      }

      // Label → route maps
      const map = isVendor ? { ...PUBLIC_LINKS, ...VENDOR_LINKS } : isAdmin ? ADMIN_LINKS : PUBLIC_LINKS;
      const target = map[label] || (isVendor ? matchVendorCta(label) : null);
      if (target) { e.preventDefault(); navigate(target); return; }

      if (isAdmin && /^(create|new\s+(tender|notice|package))/.test(label)) {
        e.preventDefault(); navigate("/admin/e/tender-builder"); return;
      }
      if (isVendor && el.classList.contains("pmc-who")) {
        e.preventDefault(); toggleWhoMenu(el, true, navigate); return;
      }
      if (isAdmin && el.classList.contains("pmc-who")) {
        e.preventDefault(); toggleWhoMenu(el, false, navigate); return;
      }

      // Public live-board rows + tender cards → register/login gate
      if (isPublic && (el.classList.contains("pmc-live__row") || el.classList.contains("pmc-live__all") || el.closest("article.pmc-tender"))) {
        e.preventDefault();
        navigate(isVendorAuthed() ? "/vendor/tenders" : "/register");
        return;
      }

      // Dead links — just swallow
      if (href === "#" || el.tagName === "BUTTON") e.preventDefault();
    };

    // Tender-list rows (built by the live-data engine) → notice detail
    const onRowClick = (e) => {
      const row = e.target.closest(".tl-row");
      if (!row) return;
      if (e.target.closest("a, button")) return; // inner actions own the click
      const root = row.closest("[data-pmc-e-page]");
      if (!root) return;
      const ref = extractNoticeRef(row);
      if (ref) { e.preventDefault(); navigate(`/notices/${ref}`); }
    };

    // Whole tender card click on public pages → gate
    const onCardClick = (e) => {
      const art = e.target.closest("article.pmc-tender");
      if (!art) return;
      const root = art.closest("[data-pmc-e-page]");
      if (!root) return;
      const pageId = root.getAttribute("data-pmc-e-page") || "";
      if (pageId.startsWith("vendor-") || pageId.startsWith("admin-")) return;
      if (e.target.closest("a, button")) return;
      e.preventDefault();
      navigate(isVendorAuthed() ? "/vendor/tenders" : "/register");
    };

    // Hero search form submit → /tenders/live?country=…&q=…
    const onSubmit = (e) => {
      const f = e.target;
      if (!(f instanceof HTMLFormElement) || !f.classList.contains("pmc-hero__search")) return;
      e.preventDefault();
      const q = f.querySelector("input")?.value?.trim() || "";
      const sel = f.querySelector("select");
      const country = sel && sel.selectedIndex > 0 ? sel.options[sel.selectedIndex].text.trim() : "";
      const params = new URLSearchParams();
      if (q) params.set("q", q);
      if (country && !/^all/i.test(country)) params.set("country", country);
      navigate("/tenders/live" + (params.toString() ? `?${params.toString()}` : ""));
    };

    document.addEventListener("click", onClick);
    document.addEventListener("click", onRowClick);
    document.addEventListener("click", onCardClick);
    document.addEventListener("submit", onSubmit);
    return () => {
      document.removeEventListener("click", onClick);
      document.removeEventListener("click", onRowClick);
      document.removeEventListener("click", onCardClick);
      document.removeEventListener("submit", onSubmit);
    };
  }, [isE, navigate]);

  return null;
}
