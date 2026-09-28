/**
 * PMC v49b — Runtime data patching for Option E static templates.
 *
 * Rather than re-authoring each of 55 templates, this module fetches real
 * data via the existing publicApi/vendorApi and surgically patches known
 * DOM nodes inside each Option E page after mount. Cheap, safe, reversible.
 */
import { useEffect } from "react";
import { publicApi, vendorApi } from "@/lib/api";

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
  } catch {
    return `${cur || ""} ${Number(amt).toLocaleString()}`;
  }
};

const tag = (t) => (t || "TENDER").toString().toUpperCase();

export function usePublicLiveData({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await publicApi.listNotices({});
        const items = (res.items || []).filter((n) => n.is_published !== false);
        if (cancelled) return;

        const openItems = items
          .filter((n) => !n.submission_deadline || new Date(n.submission_deadline) > new Date())
          .sort((a, b) => new Date(a.submission_deadline || 0) - new Date(b.submission_deadline || 0));

        // 1) Patch "29 tenders open for bids now" chip in hero
        document.querySelectorAll('[data-pmc-e-page="home-e"] .pmc-livechip')
          .forEach((el) => {
            const dot = el.querySelector('.dot');
            const svg = el.querySelector('svg');
            el.innerHTML = "";
            if (dot) el.appendChild(dot);
            el.appendChild(document.createTextNode(` ${openItems.length} tenders open for bids now `));
            if (svg) el.appendChild(svg);
            el.setAttribute("href", "/tenders/live");
          });
        document.querySelectorAll('[data-pmc-e-page="home-e"] .pmc-hero__chip b, [data-pmc-e-page="home-e"] .pmc-live__all')
          .forEach((el) => {
            el.textContent = el.textContent.replace(/\b\d+\s+(open|tenders?)/i,
              (_m, w) => `${openItems.length} ${w}`);
          });

        // 2) Patch stats bar (open count, ledger etc.)
        const figures = document.querySelectorAll('[data-pmc-e-page="home-e"] .pmc-stats .pmc-figure');
        if (figures.length >= 1) figures[0].textContent = openItems.length;

        // 3) Patch live-board rows on Home + Vendor Home
        const liveContainers = document.querySelectorAll('.pmc-live');
        liveContainers.forEach((box) => {
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
          // If more rows than data, hide extras
          rows.forEach((r, i) => {
            if (i >= openItems.length) r.style.display = "none";
          });
          const seeAll = box.querySelector(".pmc-live__all");
          if (seeAll) {
            seeAll.setAttribute("href", "/tenders/live");
            seeAll.firstChild.textContent = `See all ${openItems.length} open notices `;
          }
        });

        // 4) Patch "Open for bids this week" grid on Home
        const grid = document.querySelector('[data-pmc-e-page="home-e"] .pmc-tender');
        if (grid) {
          const cards = grid.parentElement.querySelectorAll(".pmc-tender");
          openItems.slice(0, cards.length).forEach((n, i) => {
            const c = cards[i];
            c.querySelector(".pmc-tag").textContent = tag(n.document_type);
            c.querySelector(".pmc-ref").textContent = n.notice_ref;
            const cd = c.querySelector(".pmc-countdown");
            if (cd) cd.textContent = relTime(n.submission_deadline);
            c.querySelector(".pmc-tender__title").textContent = n.title || "";
            const dds = c.querySelectorAll(".pmc-tender__meta dd");
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

        // 5) Tenders list page
        const listRows = document.querySelectorAll('[data-pmc-e-page="tenders-list-e"] .pmc-notice');
        if (listRows.length) {
          const parent = listRows[0].parentElement;
          openItems.slice(0, listRows.length).forEach((n, i) => {
            const row = listRows[i];
            const ref = row.querySelector(".pmc-ref");
            const title = row.querySelector(".pmc-notice__title, h3");
            if (ref) ref.textContent = n.notice_ref;
            if (title) title.textContent = n.title || "";
            const cd = row.querySelector(".pmc-countdown");
            if (cd) cd.textContent = relTime(n.submission_deadline);
            row.setAttribute("data-href", `/notices/${n.notice_ref}`);
            row.addEventListener("click", () => { window.location.href = `/notices/${n.notice_ref}`; });
          });
          listRows.forEach((r, i) => { if (i >= openItems.length) r.style.display = "none"; });
          // Update summary text
          const sum = document.querySelector('[data-pmc-e-page="tenders-list-e"] .pmc-muted');
          if (sum && sum.textContent.match(/\d+\s+open/i)) {
            sum.textContent = `${openItems.length} open`;
          }
        }
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.debug("Public live data skipped:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled]);
}

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
        const bids = bidsRes.items || bidsRes || [];
        const notices = noticesRes.items || [];
        const openCount = notices.filter((n) => !n.submission_deadline || new Date(n.submission_deadline) > new Date()).length;

        // Greeting name
        document.querySelectorAll('[data-pmc-e-page="vendor-home-e"] .pmc-display em, [data-pmc-e-page="vendor-home-e"] h1 em')
          .forEach((el) => { el.textContent = (me.contact_name || me.company_name || me.email || "Vendor").split(" ")[0]; });

        // KPI cards
        const active = bids.filter((b) => !["awarded","rejected","withdrawn","closed"].includes(b.status));
        const drafts = bids.filter((b) => b.status === "draft").length;
        const kycMatched = notices.filter((n) => !n.required_licenses || n.required_licenses.length === 0).length;

        const kpis = document.querySelectorAll('[data-pmc-e-page="vendor-home-e"] .pmc-kpi .pmc-figure');
        if (kpis.length >= 4) {
          kpis[0].textContent = String(active.length).padStart(2, "0");
          kpis[1].textContent = String(bids.filter((b) => b.status === "closing_soon" || (b.submission_deadline && (new Date(b.submission_deadline) - new Date()) < 7*86400*1000)).length).padStart(2, "0");
          kpis[2].textContent = String(kycMatched).padStart(2, "0");
          kpis[3].textContent = me.kyc_status === "verified" ? "Verified" : (me.kyc_status || "Pending");
        }

        // Also patch small footer text lines under KPI values
        const kpiFoots = document.querySelectorAll('[data-pmc-e-page="vendor-home-e"] .pmc-kpi .s');
        if (kpiFoots.length >= 3) {
          kpiFoots[0].textContent = `${active.length - drafts} active · ${drafts} draft${drafts === 1 ? "" : "s"}`;
          kpiFoots[2].textContent = `of ${openCount} open notices`;
        }
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.debug("Vendor live data skipped:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled]);
}
