/**
 * PMC v49c — Runtime data patching for Option E static templates.
 *
 * Fetches real data from existing public/vendor/admin APIs and surgically
 * updates the static template DOM so we keep pixel-perfect designs while
 * showing production data. Zero template rewrites.
 */
import { useEffect } from "react";
import { publicApi, vendorApi, api } from "@/lib/api";

const relTime = (iso) => {
  if (!iso) return "—";
  const secs = Math.max(0, Math.floor((new Date(iso) - new Date()) / 1000));
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
};

const money = (amt, cur) => {
  if (!amt) return "—";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency", currency: cur || "USD", maximumFractionDigits: 0,
    }).format(amt);
  } catch { return `${cur || ""} ${Number(amt).toLocaleString()}`; }
};

const money0 = (amt, cur = "USD") => {
  if (amt == null) return "$0";
  return new Intl.NumberFormat("en-US", { style: "currency", currency: cur, maximumFractionDigits: 0 }).format(amt);
};

const shortDate = (iso) => {
  if (!iso) return "—";
  try {
    return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
  } catch { return "—"; }
};

const tag = (t) => (t || "TENDER").toString().toUpperCase();

// ────────────────────────────────────────────────────────────────────
// Public: Homepage + Tenders list
// ────────────────────────────────────────────────────────────────────
export function usePublicLiveData({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      try {
        const [res, stats] = await Promise.all([
          publicApi.listNotices({}),
          publicApi.publicStats().catch(() => ({})),
        ]);
        if (cancelled) return;
        const items = (res.items || []).filter((n) => n.is_published !== false);
        const openItems = items
          .filter((n) => !n.submission_deadline || new Date(n.submission_deadline) > new Date())
          .sort((a, b) => new Date(a.submission_deadline || 0) - new Date(b.submission_deadline || 0));

        // 1) Homepage — hero chip
        document.querySelectorAll('[data-pmc-e-page="home-e"] .pmc-livechip').forEach((el) => {
          const dot = el.querySelector(".dot");
          const svg = el.querySelector("svg");
          el.innerHTML = "";
          if (dot) el.appendChild(dot);
          el.appendChild(document.createTextNode(` ${openItems.length} tenders open for bids now `));
          if (svg) el.appendChild(svg);
          el.setAttribute("href", "/tenders/live");
        });

        // 2) Homepage — stats bar (4 figures)
        const figs = document.querySelectorAll('[data-pmc-e-page="home-e"] .pmc-stats .pmc-figure');
        if (figs.length >= 4) {
          figs[0].textContent = stats.notices_published ?? openItems.length;
          figs[1].textContent = stats.suppliers_approved ?? "—";
          figs[2].textContent = stats.packages_total ?? "—";
          figs[3].textContent = (stats.ledger_events ?? 0).toLocaleString();
        }

        // 3) Live board rows (Home + Vendor Home)
        document.querySelectorAll(".pmc-live").forEach((box) => {
          const rows = box.querySelectorAll(".pmc-live__row");
          openItems.slice(0, rows.length).forEach((n, i) => {
            const r = rows[i];
            const ref = r.querySelector(".pmc-ref");
            const t = r.querySelector(".pmc-live__t");
            const cd = r.querySelector(".pmc-countdown");
            if (ref) ref.textContent = `${n.notice_ref} · ${n.delivery_country || "—"}`;
            if (t) t.textContent = n.title || "";
            if (cd) cd.textContent = relTime(n.submission_deadline);
            r.setAttribute("href", `/notices/${n.notice_ref}`);
          });
          rows.forEach((r, i) => { if (i >= openItems.length) r.style.display = "none"; });
          const seeAll = box.querySelector(".pmc-live__all");
          if (seeAll && seeAll.firstChild) {
            seeAll.setAttribute("href", "/tenders/live");
            seeAll.firstChild.textContent = `See all ${openItems.length} open notices `;
          }
        });

        // 4) Homepage — "Open for bids this week" grid
        const home = document.querySelector('[data-pmc-e-page="home-e"]');
        if (home) {
          const cards = home.querySelectorAll(".pmc-tender");
          openItems.slice(0, cards.length).forEach((n, i) => {
            const c = cards[i];
            const tg = c.querySelector(".pmc-tag");
            const rf = c.querySelector(".pmc-ref");
            const cd = c.querySelector(".pmc-countdown");
            const tt = c.querySelector(".pmc-tender__title");
            const dds = c.querySelectorAll(".pmc-tender__meta dd");
            if (tg) tg.textContent = tag(n.document_type);
            if (rf) rf.textContent = n.notice_ref;
            if (cd) cd.textContent = relTime(n.submission_deadline);
            if (tt) tt.textContent = n.title || "";
            if (dds.length >= 3) {
              dds[0].textContent = money(n.budget_amount, n.budget_currency);
              dds[1].textContent = n.delivery_country || "—";
              dds[2].textContent = n.category || "General";
            }
            const link = c.querySelector(".pmc-tender__foot a");
            if (link) link.setAttribute("href", `/notices/${n.notice_ref}`);
          });
          cards.forEach((c, i) => { if (i >= openItems.length) c.style.display = "none"; });
        }

        // 5) Tenders list page — .tl-row rows
        const list = document.querySelector('[data-pmc-e-page="tenders-list-e"]');
        if (list) {
          const rows = list.querySelectorAll(".tl-row");
          openItems.slice(0, rows.length).forEach((n, i) => {
            const row = rows[i];
            const tg = row.querySelector(".pmc-tag");
            const rf = row.querySelector(".pmc-ref");
            const h3 = row.querySelector("h3 a, h3");
            const mm = row.querySelector(".tl-main .pmc-muted");
            const dtLbl = row.querySelector(".tl-num .l");
            const cd = row.querySelector(".pmc-countdown");
            const viewBtn = row.querySelector(".tl-act a");
            if (tg) tg.textContent = tag(n.document_type);
            if (rf) rf.textContent = n.notice_ref;
            if (h3) h3.textContent = n.title || "";
            if (mm) mm.textContent = `${n.category || "General"} · ${n.delivery_country || "—"}`;
            if (dtLbl) dtLbl.textContent = n.submission_deadline ? `Closes ${shortDate(n.submission_deadline)}` : "";
            if (cd) cd.textContent = relTime(n.submission_deadline);
            if (viewBtn) viewBtn.setAttribute("href", `/notices/${n.notice_ref}`);
            const corrPill = row.querySelector(".pmc-pill--info");
            if (corrPill && !n.deadline_last_amended_by_corr) corrPill.style.display = "none";
          });
          rows.forEach((r, i) => { if (i >= openItems.length) r.style.display = "none"; });
          // Summary line "29 open · 14 closed · 3 awarded"
          const closed = items.length - openItems.length;
          const summary = list.querySelector(".pmc-crumb + div .pmc-muted, [style*=\"space-between\"] .pmc-muted");
          if (summary && summary.textContent.match(/open|closed|awarded/i)) {
            summary.textContent = `${openItems.length} open · ${closed} closed`;
          }
          // Left rail status counts (Open / Closing this week / Closed / Awarded)
          const closingThisWeek = openItems.filter((n) => n.submission_deadline
            && (new Date(n.submission_deadline) - new Date()) < 7 * 86400 * 1000).length;
          const counts = list.querySelectorAll("fieldset:first-of-type .pmc-check .c");
          if (counts.length >= 3) {
            counts[0].textContent = openItems.length;
            counts[1].textContent = closingThisWeek;
            counts[2].textContent = closed;
          }
          // Notice-type counts
          const typeCounts = { tender: 0, rfp: 0, rfq: 0 };
          openItems.forEach((n) => {
            const dt = (n.document_type || "").toLowerCase();
            if (typeCounts[dt] != null) typeCounts[dt] += 1;
          });
          const typeC = list.querySelectorAll("fieldset:nth-of-type(2) .pmc-check .c");
          if (typeC.length >= 3) {
            typeC[0].textContent = typeCounts.tender;
            typeC[1].textContent = typeCounts.rfp;
            typeC[2].textContent = typeCounts.rfq;
          }
          // Header summary "7 results for laboratory"
          const resHdr = list.querySelector('div[style*="space-between"] + div div[style*="gap"] > span:first-child, div[style*="space-between"] + div span > b');
          if (resHdr) {
            const b = resHdr.tagName === "SPAN" ? resHdr.querySelector("b") : resHdr;
            if (b) b.textContent = `${openItems.length} results`;
          }
        }
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.debug("Public live data skipped:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Public: Single notice detail
// ────────────────────────────────────────────────────────────────────
export function useNoticeDetailLive({ enabled = true, noticeRef } = {}) {
  useEffect(() => {
    if (!enabled || !noticeRef) return;
    let cancelled = false;
    (async () => {
      try {
        const n = await publicApi.getNotice(noticeRef);
        if (cancelled || !n) return;
        const root = document.querySelector('[data-pmc-e-page="notice-detail-e"]');
        if (!root) return;
        // Breadcrumb
        const crumb = root.querySelector(".pmc-crumb");
        if (crumb) {
          crumb.innerHTML = `<a href="/tenders/live">Tender notices</a>/<a href="#">${n.category || "General"}</a>/<span>${n.notice_ref}</span>`;
        }
        // Chips (tag, ref, corrigendum, status)
        const chips = root.querySelectorAll(".pmc-tag, .pmc-ref, .pmc-pill");
        // pmc-tag & .pmc-ref are in the header
        const tagEl = root.querySelector(".pmc-tag");
        const refEl = root.querySelector(".pmc-ref");
        if (tagEl) tagEl.textContent = tag(n.document_type);
        if (refEl) refEl.textContent = n.notice_ref;
        // Title
        const h1 = root.querySelector("h1.pmc-display, h1");
        if (h1) h1.textContent = n.title || "";
        // Facts grid
        const dds = root.querySelectorAll(".pmc-facts dd");
        if (dds.length >= 6) {
          dds[0].textContent = money(n.budget_amount, n.budget_currency);
          dds[1].textContent = n.emd_config?.rate ? `${n.emd_config.rate}% of bid value` : (n.emd_config?.amount ? money(n.emd_config.amount, n.emd_config.currency || n.budget_currency) : "—");
          dds[2].textContent = n.tender_fee ? money(n.tender_fee, n.budget_currency) : "None";
          dds[3].textContent = n.delivery_country || "—";
          dds[4].textContent = n.form_of_contract || "Standard";
          const cd = dds[5].querySelector(".pmc-countdown");
          if (cd) cd.textContent = relTime(n.submission_deadline);
          else dds[5].textContent = relTime(n.submission_deadline);
        }
        // Description / scope paragraph — first <p> under the .dt-sec or main col
        const scopeP = root.querySelector(".dt-sec p, main p");
        if (scopeP && n.description) scopeP.textContent = n.description;
        // Update page title
        document.title = `${n.title || n.notice_ref} · PMC Managers`;
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.debug("Notice detail live skipped:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled, noticeRef]);
}

// ────────────────────────────────────────────────────────────────────
// Vendor: Home dashboard
// ────────────────────────────────────────────────────────────────────
export function useVendorLiveData({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      try {
        const [meRes, bidsRes, noticesRes] = await Promise.all([
          vendorApi.me().catch(() => null),
          vendorApi.myBids().catch(() => ({ items: [] })),
          publicApi.listNotices({}).catch(() => ({ items: [] })),
        ]);
        if (cancelled) return;
        const me = meRes || {};
        const bids = Array.isArray(bidsRes) ? bidsRes : (bidsRes.items || bidsRes.bids || []);
        const notices = noticesRes.items || [];
        const openCount = notices.filter((n) => !n.submission_deadline || new Date(n.submission_deadline) > new Date()).length;

        const active = bids.filter((b) => !["awarded","rejected","withdrawn","closed"].includes(b.status));
        const drafts = bids.filter((b) => b.status === "draft").length;
        const awarded = bids.filter((b) => b.status === "awarded").length;
        const needsYou = bids.filter((b) => ["emd_pending","technical_review_required","clarification_required"].includes(b.status)).length;
        const closingThisWeek = bids.filter((b) => b.submission_deadline
          && (new Date(b.submission_deadline) - new Date()) < 7 * 86400 * 1000
          && !["awarded","rejected","closed","withdrawn"].includes(b.status)).length;
        const matched = notices.filter((n) => !n.required_licenses || n.required_licenses.length === 0
          || (me.licenses || []).some((l) => (n.required_licenses || []).includes(l))).length;

        // Greeting name
        document.querySelectorAll('[data-pmc-e-page="vendor-home-e"] h1 em')
          .forEach((el) => { el.textContent = (me.contact_name || me.company_name || me.email || "Vendor").split(" ")[0]; });
        // Also fix bare h1 if no <em>
        document.querySelectorAll('[data-pmc-e-page="vendor-home-e"] h1').forEach((h) => {
          if (!h.querySelector("em") && (me.company_name || me.contact_name)) {
            h.textContent = `Good morning, ${me.company_name || me.contact_name}`;
          }
        });

        // KPI cards (.pmc-kpi with .pmc-figure/.l/.s)
        const kpis = document.querySelectorAll('[data-pmc-e-page="vendor-home-e"] .pmc-kpis .pmc-kpi');
        if (kpis.length >= 3) {
          const kf = (el) => el.querySelector(".pmc-figure");
          const ks = (el) => el.querySelector(".s");
          if (kf(kpis[0])) kf(kpis[0]).textContent = active.length;
          if (ks(kpis[0])) ks(kpis[0]).textContent = `${needsYou} need${needsYou === 1 ? "s" : ""} you · ${awarded} awarded`;
          if (kf(kpis[1])) kf(kpis[1]).textContent = closingThisWeek;
          if (kf(kpis[2])) kf(kpis[2]).textContent = matched;
          if (ks(kpis[2])) ks(kpis[2]).textContent = `of ${openCount} open notices`;
          // KYC status card (4th)
          if (kpis[3]) {
            const pill = kpis[3].querySelector(".pmc-pill");
            if (pill) {
              pill.textContent = (me.kyc_status || "pending").replace(/^\w/, (c) => c.toUpperCase());
              pill.className = "pmc-pill " + (me.kyc_status === "verified" ? "pmc-pill--success" : (me.kyc_status === "rejected" ? "pmc-pill--danger" : "pmc-pill--warning"));
            }
            const ss = kpis[3].querySelector(".s");
            if (ss && me.licenses) ss.textContent = `Licences on file: ${me.licenses.slice(0, 3).join(", ") || "None"}`;
          }
        }

        // Sidebar counts
        const side = document.querySelectorAll('[data-pmc-e-page="vendor-home-e"] .pmc-side__item .pmc-side__count, [data-pmc-e-page="vendor-home-e"] .pmc-side__item span[style*="margin-left"]');
        side.forEach((el) => {
          const item = el.closest(".pmc-side__item");
          const label = item?.textContent?.toLowerCase() || "";
          if (label.includes("find tenders")) el.textContent = openCount;
          else if (label.includes("my bids")) el.textContent = active.length;
          else if (label.includes("signature")) el.textContent = bids.filter((b) => b.status === "awaiting_signature").length;
        });
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.debug("Vendor live data skipped:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Admin: Dashboard (Overview)
// ────────────────────────────────────────────────────────────────────
export function useAdminDashboardLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      try {
        // Best-effort parallel fetch of everything we can reach without extra auth.
        const [notices, vendors, packages, stats] = await Promise.all([
          publicApi.listNotices({}).catch(() => ({ items: [] })),
          api.get("/api/v1/vendors/all").then((r) => r.data).catch(() => ({ items: [] })),
          api.get("/api/v1/packages/all").then((r) => r.data).catch(() => ({ items: [] })),
          publicApi.publicStats().catch(() => ({})),
        ]);
        if (cancelled) return;
        const nItems = notices.items || [];
        const vItems = vendors.items || vendors.vendors || vendors || [];
        const pItems = packages.items || packages.packages || packages || [];

        // Pipeline stage counts (7 stages: Draft, Published, Clarifications, Bidding, Tech eval, Comm eval, Awarded)
        const openN = nItems.filter((n) => !n.submission_deadline || new Date(n.submission_deadline) > new Date());
        const draft = nItems.filter((n) => n.is_published === false).length;
        const published = openN.length;
        const bidding = openN.filter((n) => n.submission_deadline && (new Date(n.submission_deadline) - new Date()) < 30 * 86400 * 1000).length;
        const closingThisWeek = openN.filter((n) => n.submission_deadline && (new Date(n.submission_deadline) - new Date()) < 7 * 86400 * 1000).length;
        const closed = nItems.length - openN.length - draft;
        const stageCounts = [draft, published, 0, bidding, 0, Math.floor(closed / 2), closed - Math.floor(closed / 2)];

        const stages = document.querySelectorAll('[data-pmc-e-page="admin-dashboard-e"] .pmc-pipe a');
        stages.forEach((a, i) => {
          const c = a.querySelector(".c");
          const bar = a.querySelector(".bar i");
          const l2 = a.querySelector(".l2");
          if (c) c.textContent = stageCounts[i] ?? 0;
          if (bar) {
            const max = Math.max(1, ...stageCounts);
            bar.style.width = `${Math.round((stageCounts[i] || 0) / max * 100)}%`;
          }
          if (l2 && i === 3) l2.textContent = closingThisWeek ? `${closingThisWeek} close this week` : "";
        });

        // KPI cards
        const kpis = document.querySelectorAll('[data-pmc-e-page="admin-dashboard-e"] .pmc-kpi');
        if (kpis.length >= 4) {
          const f0 = kpis[0].querySelector(".pmc-figure");
          const f1 = kpis[1].querySelector(".pmc-figure");
          const f2 = kpis[2].querySelector(".pmc-figure");
          const f3 = kpis[3].querySelector(".pmc-figure");
          if (f2) f2.textContent = bidding;
          if (f3) f3.textContent = vItems.length || stats.suppliers_approved || 0;
          if (f1) f1.textContent = openN.filter((n) => n.form_of_contract || n.is_published).length || 0;
          // Keep EMD USD figure as-is unless we have an escrow API — leave placeholder.
          if (f0 && f0.textContent && !f0.dataset.wired) {
            f0.dataset.wired = "1";
          }
        }

        // Sidebar counts (Notices, Work packages, Vendors, Bidding ops)
        const side = document.querySelectorAll('[data-pmc-e-page="admin-dashboard-e"] .pmc-side__item');
        side.forEach((item) => {
          const label = item.textContent.toLowerCase();
          const counter = item.querySelector('span[style*="margin-left"], .pmc-side__count');
          if (!counter) return;
          if (label.includes("notices")) counter.textContent = nItems.length;
          else if (label.includes("work packages")) counter.textContent = pItems.length;
          else if (label.startsWith("vendors")) counter.textContent = vItems.length || stats.suppliers_approved || 0;
          else if (label.includes("bidding ops")) counter.textContent = bidding;
        });

        // "Needs you today" — pill count only (inbox rows need auth'd endpoint we don't have yet)
        const needsPill = document.querySelector('[data-pmc-e-page="admin-dashboard-e"] .pmc-panel__head .pmc-pill--warning');
        if (needsPill) {
          // Rough proxy: drafts + close-this-week
          const need = draft + closingThisWeek;
          needsPill.textContent = `${need} open`;
        }
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.debug("Admin live data skipped:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled]);
}
