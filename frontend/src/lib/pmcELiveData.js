/**
 * PMC v49c — Runtime data patching for Option E static templates.
 *
 * Fetches real data from existing public/vendor/admin APIs and surgically
 * updates the static template DOM so we keep pixel-perfect designs while
 * showing production data. Zero template rewrites.
 */
import { useEffect } from "react";
import { publicApi, vendorApi, bidApi, api, docusignApi } from "@/lib/api";

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
// Tenders list — interactive filter engine (status/type/country/category/
// budget/search/sort) over the real notices dataset.
// ────────────────────────────────────────────────────────────────────
const FX_TO_USD = { USD: 1, INR: 0.012, KZT: 0.0021, EUR: 1.08, GBP: 1.27 };
const COUNTRY_NAMES = { KZ: "Kazakhstan", IN: "India", AE: "UAE", UAE: "UAE", GB: "UK", UK: "UK", US: "USA" };
const countryLabel = (c) => COUNTRY_NAMES[(c || "").toUpperCase()] || c || "—";
const usdEquiv = (n) => (n.budget_amount || 0) * (FX_TO_USD[(n.budget_currency || "USD").toUpperCase()] ?? 1);

function initTenderFilters(list, allItems) {
  const now = Date.now();
  const WEEK = 7 * 86400 * 1000;
  const isOpen = (n) => !n.submission_deadline || new Date(n.submission_deadline).getTime() > now;
  const isClosing = (n) => isOpen(n) && !!n.submission_deadline && (new Date(n.submission_deadline).getTime() - now) < WEEK;
  const isClosed = (n) => !isOpen(n);
  const isAwarded = (n) => !!(n.award_ref || n.awarded_to || n.award);

  // v49i — read URL query so the home hero's Find-tenders form can prefill.
  const urlParams = new URLSearchParams(window.location.search || "");
  const urlCountry = (urlParams.get("country") || "").toLowerCase();
  const urlQ = urlParams.get("q") || "";

  const panel = list.querySelector(".pmc-panel:has(.tl-row)") || list.querySelector(".tl-row")?.parentElement;
  if (!panel) return;
  const template = panel.querySelector(".tl-row").cloneNode(true);

  const fieldsets = list.querySelectorAll("fieldset");
  const statusFs = fieldsets[0], typeFs = fieldsets[1], countryFs = fieldsets[2], catFs = fieldsets[3], budgetFs = fieldsets[4];

  const openC = allItems.filter(isOpen).length;
  const closingC = allItems.filter(isClosing).length;
  const closedC = allItems.filter(isClosed).length;
  const awardedC = allItems.filter(isAwarded).length;
  if (statusFs) {
    const vals = [openC, closingC, closedC, awardedC];
    statusFs.querySelectorAll(".pmc-check .c").forEach((el, i) => { el.textContent = vals[i] ?? 0; });
  }
  if (typeFs) {
    const tCounts = { tender: 0, rfp: 0, rfq: 0 };
    allItems.forEach((n) => { const d = (n.document_type || "").toLowerCase(); if (d in tCounts) tCounts[d] += 1; });
    typeFs.querySelectorAll(".pmc-check .c").forEach((el, i) => { el.textContent = Object.values(tCounts)[i] ?? 0; });
  }

  // Rebuild country + category facets from real distinct values
  const rebuildFacet = (fs, pairs) => {
    if (!fs || !pairs.length) return;
    const legend = fs.querySelector("legend");
    fs.innerHTML = "";
    if (legend) fs.appendChild(legend);
    pairs.forEach(([labelText, count]) => {
      const lab = document.createElement("label");
      lab.className = "pmc-check";
      lab.innerHTML = `<input type="checkbox" />${labelText}<span class="c">${count}</span>`;
      lab.querySelector("input").addEventListener("change", apply);
      fs.appendChild(lab);
    });
  };
  const countryMap = {};
  allItems.forEach((n) => { const c = countryLabel(n.delivery_country); countryMap[c] = (countryMap[c] || 0) + 1; });
  rebuildFacet(countryFs, Object.entries(countryMap).sort((a, b) => b[1] - a[1]));
  // v49i — apply URL ?country=xx by ticking the matching checkbox
  if (urlCountry && countryFs) {
    countryFs.querySelectorAll("label.pmc-check").forEach((lab) => {
      const name = lab.textContent.replace(/[\d\s]+$/, "").trim().toLowerCase();
      if (name === urlCountry || name.startsWith(urlCountry) || urlCountry.startsWith(name.slice(0, 2))) {
        const cb = lab.querySelector("input");
        if (cb) cb.checked = true;
      }
    });
  }
  const catMap = {};
  allItems.forEach((n) => { const c = (n.category || "General").trim(); catMap[c] = (catMap[c] || 0) + 1; });
  rebuildFacet(catFs, Object.entries(catMap).sort((a, b) => b[1] - a[1]).slice(0, 8));

  const searchForm = list.querySelector("form");
  const searchInput = searchForm ? searchForm.querySelector("input") : null;
  // v49i — prefill search box from ?q=…
  if (urlQ && searchInput) searchInput.value = urlQ;
  const sortSel = Array.from(list.querySelectorAll("select.pmc-input"))
    .find((s) => /closing first/i.test(s.textContent));
  const budgetInputs = budgetFs ? Array.from(budgetFs.querySelectorAll("input")) : [];

  const facetValues = (fs) => fs
    ? Array.from(fs.querySelectorAll("input:checked")).map((i) =>
        i.parentElement.textContent.replace(/[\d\s]+$/, "").trim().toLowerCase())
    : [];

  function currentFilters() {
    let status = "open";
    if (statusFs) {
      const order = ["open", "closing", "closed", "awarded"];
      statusFs.querySelectorAll("input[type=radio]").forEach((r, i) => { if (r.checked) status = order[i] || "open"; });
    }
    return {
      status,
      types: facetValues(typeFs),
      countries: facetValues(countryFs),
      cats: facetValues(catFs),
      min: parseFloat(budgetInputs[0]?.value) || null,
      max: parseFloat(budgetInputs[1]?.value) || null,
      q: (searchInput?.value || "").trim().toLowerCase(),
      sort: sortSel ? sortSel.value : "Closing first",
    };
  }

  function patchRow(row, n) {
    const tg = row.querySelector(".pmc-tag");
    const rf = row.querySelector(".pmc-ref");
    const h3a = row.querySelector("h3 a, h3");
    const mm = row.querySelector(".tl-main .pmc-muted");
    const nums = row.querySelectorAll(".tl-num");
    const cd = row.querySelector(".pmc-countdown");
    const viewBtn = row.querySelector(".tl-act a");
    if (tg) tg.textContent = tag(n.document_type);
    if (rf) rf.textContent = n.notice_ref;
    if (h3a) {
      h3a.textContent = n.title || "";
      if (h3a.tagName === "A") h3a.setAttribute("href", `/notices/${n.notice_ref}`);
    }
    if (mm) mm.textContent = `${(n.category || "General").trim()} · ${countryLabel(n.delivery_country)}`;
    if (nums[0]) {
      const v = nums[0].querySelector(".v");
      if (v) v.textContent = money(n.budget_amount, n.budget_currency);
    }
    if (nums[1]) {
      const l = nums[1].querySelector(".l");
      if (l) l.textContent = n.submission_deadline ? `Closes ${shortDate(n.submission_deadline)}` : "No deadline";
    }
    if (cd) cd.textContent = isOpen(n) ? relTime(n.submission_deadline) : "Closed";
    if (viewBtn) viewBtn.setAttribute("href", `/notices/${n.notice_ref}`);
    const corr = row.querySelector(".pmc-pill--info");
    if (corr) corr.style.display = n.deadline_last_amended_by_corr ? "" : "none";
    const newPill = Array.from(row.querySelectorAll(".pmc-pill")).find((p) => /new/i.test(p.textContent));
    if (newPill) {
      const isNew = n.published_at && (now - new Date(n.published_at).getTime()) < WEEK;
      newPill.style.display = isNew ? "" : "none";
    }
    return row;
  }

  function renderRows(items, f) {
    panel.innerHTML = "";
    const PAGE_SIZE = 10;
    const total = items.length;
    // Reset to page 1 whenever the filter/query changes
    const filterKey = JSON.stringify({ q: f.q, s: f.status, t: f.types, c: f.country });
    if (panel.dataset.pmcFilterKey !== filterKey) {
      panel.dataset.pmcFilterKey = filterKey;
      panel.dataset.pmcPage = "1";
    }
    const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE));
    let page = Math.min(Math.max(1, parseInt(panel.dataset.pmcPage || "1", 10) || 1), totalPages);
    panel.dataset.pmcPage = String(page);
    const start = (page - 1) * PAGE_SIZE;
    const end = Math.min(start + PAGE_SIZE, total);
    items.slice(start, end).forEach((n) => panel.appendChild(patchRow(template.cloneNode(true), n)));
    if (!total) {
      const empty = document.createElement("div");
      empty.className = "pmc-muted";
      empty.style.cssText = "padding:48px 24px;text-align:center";
      empty.textContent = "No notices match these filters. Try Clear all.";
      panel.appendChild(empty);
    }
    // Results header "N results for “q” in Status"
    const resSpan = Array.from(list.querySelectorAll("span"))
      .find((s) => s.querySelector("b") && /results/i.test(s.textContent));
    if (resSpan) {
      const names = { open: "Open", closing: "Closing this week", closed: "Closed", awarded: "Awarded" };
      resSpan.innerHTML = `<b>${total} results</b>${f.q ? ` for \u201C${f.q}\u201D` : ""} in ${names[f.status] || "Open"}`;
    }
    // v49p — wire the hardcoded pagination footer: update the "Showing X–Y of Z"
    // text, render numbered page buttons, and enable Prev/Next handlers.
    const footer = panel.parentElement?.querySelector(':scope > div[style*="justify-content: space-between"]:last-child')
                || Array.from(list.querySelectorAll("div"))
                        .find((d) => /showing\s+\d+/i.test((d.textContent || "")));
    if (footer) {
      const label = footer.querySelector("span.pmc-muted");
      if (label) label.textContent = total ? `Showing ${start + 1}–${end} of ${total}` : "No results";
      const btnRow = footer.querySelector('div[style*="gap: 6px"]') || footer.querySelector("div:last-child");
      if (btnRow) {
        btnRow.innerHTML = "";
        const mk = (txt, cls, disabled, onClick) => {
          const b = document.createElement("button");
          b.type = "button";
          b.className = `pmc-btn pmc-btn--sm ${cls}`;
          b.textContent = txt;
          if (disabled) b.disabled = true;
          else b.addEventListener("click", (e) => { e.preventDefault(); onClick(); });
          return b;
        };
        btnRow.appendChild(mk("Previous", "pmc-btn--secondary", page <= 1, () => {
          panel.dataset.pmcPage = String(page - 1);
          renderRows(items, f);
        }));
        // Numbered page buttons — up to 7 windowed around the current page
        const windowStart = Math.max(1, Math.min(page - 3, totalPages - 6));
        const windowEnd = Math.min(totalPages, windowStart + 6);
        for (let p = windowStart; p <= windowEnd; p += 1) {
          btnRow.appendChild(mk(String(p),
            p === page ? "pmc-btn--primary" : "pmc-btn--secondary",
            false,
            () => { panel.dataset.pmcPage = String(p); renderRows(items, f); }));
        }
        btnRow.appendChild(mk("Next", "pmc-btn--secondary", page >= totalPages, () => {
          panel.dataset.pmcPage = String(page + 1);
          renderRows(items, f);
        }));
      }
    }
    // Type chips reflect checkbox state; clicking re-enables
    list.querySelectorAll(".pmc-chip").forEach((chip) => {
      const label = chip.textContent.replace("×", "").trim().toLowerCase();
      chip.style.display = f.types.length && !f.types.includes(label) ? "none" : "";
      if (!chip.dataset.wired) {
        chip.dataset.wired = "1";
        chip.style.cursor = "pointer";
        chip.addEventListener("click", () => {
          if (typeFs) typeFs.querySelectorAll("label.pmc-check").forEach((lab) => {
            if (lab.textContent.replace(/[\d\s]+$/, "").trim().toLowerCase() === label) {
              lab.querySelector("input").checked = true;
            }
          });
          apply();
        });
      }
    });
  }

  function apply() {
    const f = currentFilters();
    let out = allItems.filter((n) => {
      if (f.status === "open" && !isOpen(n)) return false;
      if (f.status === "closing" && !isClosing(n)) return false;
      if (f.status === "closed" && !isClosed(n)) return false;
      if (f.status === "awarded" && !isAwarded(n)) return false;
      if (f.types.length && !f.types.includes((n.document_type || "tender").toLowerCase())) return false;
      if (f.countries.length && !f.countries.includes(countryLabel(n.delivery_country).toLowerCase())) return false;
      if (f.cats.length && !f.cats.includes((n.category || "General").trim().toLowerCase())) return false;
      const usd = usdEquiv(n);
      if (f.min != null && usd < f.min) return false;
      if (f.max != null && usd > f.max) return false;
      if (f.q) {
        const hay = `${n.title || ""} ${n.notice_ref || ""} ${n.category || ""} ${countryLabel(n.delivery_country)}`.toLowerCase();
        if (!hay.includes(f.q)) return false;
      }
      return true;
    });
    if (f.sort === "Newest") out.sort((a, b) => new Date(b.published_at || 0) - new Date(a.published_at || 0));
    else if (f.sort === "Highest budget") out.sort((a, b) => usdEquiv(b) - usdEquiv(a));
    else out.sort((a, b) => new Date(a.submission_deadline || 9e15) - new Date(b.submission_deadline || 9e15));
    renderRows(out, f);
  }

  // Wire events
  list.querySelectorAll("fieldset input").forEach((i) => i.addEventListener("change", apply));
  budgetInputs.forEach((i) => i.addEventListener("input", apply));
  if (sortSel) sortSel.addEventListener("change", apply);
  if (searchInput) searchInput.addEventListener("input", apply);
  if (searchForm) searchForm.addEventListener("submit", (e) => { e.preventDefault(); apply(); });

  const clearAll = Array.from(list.querySelectorAll("a")).find((a) => a.textContent.trim() === "Clear all");
  if (clearAll) clearAll.addEventListener("click", (e) => {
    e.preventDefault();
    if (statusFs) { const r = statusFs.querySelectorAll("input[type=radio]"); if (r[0]) r[0].checked = true; }
    if (typeFs) typeFs.querySelectorAll("input").forEach((i) => { i.checked = true; });
    [countryFs, catFs].forEach((fs) => fs && fs.querySelectorAll("input").forEach((i) => { i.checked = false; }));
    budgetInputs.forEach((i) => { i.value = ""; });
    if (searchInput) searchInput.value = "";
    if (sortSel) sortSel.value = "Closing first";
    apply();
  });

  // Top-right summary line next to the H1
  const summary = list.querySelector("h1.pmc-display")?.parentElement?.querySelector(".pmc-muted");
  if (summary) summary.textContent = `${openC} open · ${closedC} closed${awardedC ? ` · ${awardedC} awarded` : ""}`;

  apply();
}

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

        // 5) Tenders list page — full client-side filter engine
        const list = document.querySelector('[data-pmc-e-page="tenders-list-e"]');
        if (list) initTenderFilters(list, items);
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
        // v49j — wire Download buttons on the document rows to the notice's
        // real attachments (primary doc first). The delegated click handler
        // in PmcLinkPatcher opens data-doc-url links; rows without one get
        // the register gate / tender-desk toast instead.
        const atts = [];
        if (n.primary_document && n.primary_document.url) atts.push(n.primary_document);
        (n.attachments || []).forEach((a) => { if (a && a.url) atts.push(a); });
        root.querySelectorAll(".pmc-docrow").forEach((rowEl, i) => {
          const a = atts[i];
          if (!a) return;
          rowEl.setAttribute("data-doc-url", a.url);
          const dl = rowEl.querySelector("a.pmc-btn");
          if (dl) dl.setAttribute("data-doc-url", a.url);
          const nm = rowEl.querySelector("b");
          if (nm && a.file_name) nm.textContent = a.file_name;
        });
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
          bidApi.mine().catch(() => []),
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
// Vendor: My bids page
// ────────────────────────────────────────────────────────────────────
export function useVendorMyBidsLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      try {
        const bids = await bidApi.mine();
        if (cancelled) return;
        const root = document.querySelector('[data-pmc-e-page="vendor-mybids-e"]');
        if (!root) return;
        const active = bids.filter((b) => !["awarded","rejected","withdrawn","closed"].includes(b.status));
        const drafts = bids.filter((b) => b.status === "draft");
        const closed = bids.filter((b) => ["closed","rejected"].includes(b.status));
        const withdrawn = bids.filter((b) => b.status === "withdrawn");
        const awarded = bids.filter((b) => b.status === "awarded");
        // KPI figures
        const kpis = root.querySelectorAll(".pmc-kpi .pmc-figure, .pmc-kpi .pmc-figure b, .pmc-kpi h3");
        // Tab counts: "Active 4 / Drafts 3 / Closed 7 / Withdrawn 0"
        const tabs = root.querySelectorAll(".tabs a, .pmc-tabs a, .pmc-tab, [role='tab']");
        tabs.forEach((t) => {
          const label = t.textContent.trim().toLowerCase();
          if (label.startsWith("active")) t.textContent = `Active ${active.length}`;
          else if (label.startsWith("draft")) t.textContent = `Drafts ${drafts.length}`;
          else if (label.startsWith("closed")) t.textContent = `Closed ${closed.length}`;
          else if (label.startsWith("withdrawn")) t.textContent = `Withdrawn ${withdrawn.length}`;
        });
        // Rows in the main bids table
        const table = root.querySelector("table, .pmc-bids, .pmc-panel");
        if (table) {
          const rows = table.querySelectorAll("tbody tr, .pmc-bid-row");
          active.slice(0, rows.length).forEach((b, i) => {
            const r = rows[i];
            const ref = r.querySelector(".pmc-ref");
            if (ref) ref.textContent = b.bid_ref;
            const priceCell = r.querySelectorAll("td, .cell");
            if (priceCell[1]) priceCell[1].textContent = money(b.price_amount, b.price_currency);
          });
        }
        // Subtitles
        const subs = root.querySelectorAll(".pmc-kpi .s");
        if (kpis[0]) kpis[0].textContent = active.length;
        if (kpis[1]) kpis[1].textContent = awarded.length ? Math.round(awarded.length / (bids.length || 1) * 100) + "%" : "0%";
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.debug("Vendor mybids live skipped:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Vendor: Company & KYC page
// ────────────────────────────────────────────────────────────────────
export function useVendorCompanyLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      try {
        const me = await vendorApi.me();
        if (cancelled || !me) return;
        const root = document.querySelector('[data-pmc-e-page="vendor-company-kyc-e"]');
        if (!root) return;
        // Company name in header
        const h1 = root.querySelector("h1");
        if (h1) h1.textContent = me.company_name || "Your company";
        // Simple field patching: look for dt/dd or label/value pairs
        const dds = root.querySelectorAll("dd, .pmc-facts dd");
        const values = [me.company_name, me.vendor_ref, me.email, me.kyc_status || "pending"];
        dds.forEach((dd, i) => { if (values[i]) dd.textContent = values[i]; });
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.debug("Vendor company live skipped:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Admin: Notices page
// ────────────────────────────────────────────────────────────────────
export function useAdminNoticesLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await publicApi.listNotices({});
        if (cancelled) return;
        const items = res.items || [];
        const root = document.querySelector('[data-pmc-e-page="admin-notices-e"]');
        if (!root) return;
        // Populate table rows
        const rows = root.querySelectorAll("tbody tr, .pmc-notice-row, .tl-row");
        items.slice(0, rows.length).forEach((n, i) => {
          const r = rows[i];
          const ref = r.querySelector(".pmc-ref");
          const h3 = r.querySelector("h3 a, h3, td:nth-child(2)");
          const cd = r.querySelector(".pmc-countdown");
          if (ref) ref.textContent = n.notice_ref;
          if (h3) {
            h3.textContent = n.title || "";
            if (h3.tagName === "A") h3.setAttribute("href", `/notices/${n.notice_ref}`);
          }
          if (cd) cd.textContent = n.submission_deadline ? shortDate(n.submission_deadline) : "—";
        });
        rows.forEach((r, i) => { if (i >= items.length) r.style.display = "none"; });
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.debug("Admin notices live skipped:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Admin: Vendors list page
// ────────────────────────────────────────────────────────────────────
export function useAdminVendorsLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get("/api/v1/vendors/all").then((r) => r.data).catch(() => ({ items: [] }));
        if (cancelled) return;
        const items = res.items || res.vendors || res || [];
        const root = document.querySelector('[data-pmc-e-page="admin-vendors-e"]');
        if (!root) return;
        // Update the top KPI (Approved N)
        const kpi = root.querySelector(".pmc-kpi .pmc-figure");
        if (kpi) kpi.textContent = items.length;
        // Populate list rows
        const rows = root.querySelectorAll("tbody tr");
        items.slice(0, rows.length).forEach((v, i) => {
          const r = rows[i];
          const nameCell = r.querySelector("td:first-child, .pmc-vname");
          const refCell = r.querySelector(".pmc-ref");
          if (nameCell) {
            const nb = nameCell.querySelector("b, strong") || nameCell;
            nb.textContent = v.company_name || v.name || v.vendor_ref;
          }
          if (refCell) refCell.textContent = v.vendor_ref;
        });
        rows.forEach((r, i) => { if (i >= items.length) r.style.display = "none"; });
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.debug("Admin vendors live skipped:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Universal small helpers used by v50 hooks below
// ────────────────────────────────────────────────────────────────────
function _patchKpiFigures(root, values) {
  const figs = root.querySelectorAll(".pmc-kpi .pmc-figure");
  values.forEach((v, i) => { if (figs[i] && v != null) figs[i].textContent = v; });
}
function _patchTableRefs(root, refs) {
  const rows = root.querySelectorAll("tbody tr, .pmc-panel tr, .pmc-notice-row");
  refs.slice(0, rows.length).forEach((r, i) => {
    const refEl = rows[i].querySelector(".pmc-ref");
    if (refEl && r.ref) refEl.textContent = r.ref;
    const titleCell = rows[i].querySelector("td:nth-child(2) a, td:nth-child(2) b, td:nth-child(1) b");
    if (titleCell && r.title) titleCell.textContent = r.title;
    if (r.href) rows[i].querySelectorAll("a").forEach((a) => { if (a.getAttribute("href") === "#") a.setAttribute("href", r.href); });
  });
  rows.forEach((r, i) => { if (i >= refs.length) r.style.display = "none"; });
}
function _patchSummary(root, text) {
  const el = root.querySelector(".pmc-crumb + div .pmc-muted, h1.pmc-display + .pmc-muted, h1 + .pmc-muted");
  if (el) el.textContent = text;
}

// ────────────────────────────────────────────────────────────────────
// Vendor: Find tenders  (same feed as public tenders list)
// ────────────────────────────────────────────────────────────────────
export function useVendorFindTendersLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await publicApi.listNotices({});
        const items = (res.items || []).filter((n) => !n.submission_deadline || new Date(n.submission_deadline) > new Date());
        const root = document.querySelector('[data-pmc-e-page="vendor-find-tenders-e"]');
        if (!root) return;
        const rows = root.querySelectorAll(".tl-row, .pmc-notice, .pmc-tender");
        items.slice(0, rows.length).forEach((n, i) => {
          const r = rows[i];
          const ref = r.querySelector(".pmc-ref"); if (ref) ref.textContent = n.notice_ref;
          const h3 = r.querySelector("h3 a, h3"); if (h3) h3.textContent = n.title || "";
          const view = r.querySelector(".tl-act a, .pmc-tender__foot a"); if (view) view.setAttribute("href", `/notices/${n.notice_ref}`);
          const cd = r.querySelector(".pmc-countdown"); if (cd) cd.textContent = relTime(n.submission_deadline);
        });
        rows.forEach((r, i) => { if (i >= items.length) r.style.display = "none"; });
        _patchSummary(root, `${items.length} open tenders match your profile`);
      } catch (e) { console.debug("VendorFindTenders skip:", e); }
    })();
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Vendor: EMD & Payments
// ────────────────────────────────────────────────────────────────────
export function useVendorEmdLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const bids = await bidApi.mine().catch(() => []);
        const root = document.querySelector('[data-pmc-e-page="vendor-emd-e"]');
        if (!root) return;
        const paid = bids.filter((b) => b.emd_paid_amount > 0);
        const pending = bids.filter((b) => b.status === "emd_pending");
        const totalUsd = paid.reduce((s, b) => s + (b.emd_paid_amount || 0) * (b.emd_currency === "USD" ? 1 : 0.012), 0);
        _patchKpiFigures(root, [`$${Math.round(totalUsd).toLocaleString()}`, paid.length, pending.length]);
        const rows = root.querySelectorAll("tbody tr, .pmc-txn");
        paid.slice(0, rows.length).forEach((b, i) => {
          const r = rows[i];
          const ref = r.querySelector(".pmc-ref"); if (ref) ref.textContent = b.bid_ref;
          const amt = r.querySelector(".pmc-amt, td:last-child"); if (amt) amt.textContent = money(b.emd_paid_amount, b.emd_currency);
        });
        rows.forEach((r, i) => { if (i >= paid.length) r.style.display = "none"; });
      } catch (e) { console.debug("VendorEmd skip:", e); }
    })();
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Vendor: Signatures
// ────────────────────────────────────────────────────────────────────
// ────────────────────────────────────────────────────────────────────
// Vendor: Signatures — v49n wired to real DocuSign envelopes
// ────────────────────────────────────────────────────────────────────
export function useVendorSignaturesLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const root = document.querySelector('[data-pmc-e-page="vendor-signatures-e"]');
        if (!root) return;
        const data = await docusignApi.listMine().catch(() => ({ items: [] }));
        const items = Array.isArray(data?.items) ? data.items : [];
        const pending = items.filter((e) => e.status === "sent" || e.status === "delivered");
        const done = items.filter((e) => e.status === "completed");
        _patchKpiFigures(root, [pending.length, done.length]);

        // Sidebar "Signatures" count badge
        root.querySelectorAll(".pmc-lnav a").forEach((a) => {
          if ((a.textContent || "").includes("Signatures")) {
            const c = a.querySelector(".c");
            if (c) c.textContent = String(pending.length);
          }
        });

        // "Needs your signature" hero card
        const nextCard = root.querySelector(".pmc-next");
        if (nextCard) {
          if (pending.length) {
            const e0 = pending[0];
            nextCard.setAttribute("data-envelope-id", e0.envelope_id);
            nextCard.querySelectorAll("a.pmc-btn, button.pmc-btn").forEach((b) =>
              b.setAttribute("data-envelope-id", e0.envelope_id));
            const h2 = nextCard.querySelector("h2");
            if (h2) h2.textContent = e0.subject || e0.award_ref || "Award document";
            const sub = nextCard.querySelector(".pmc-muted");
            if (sub) sub.textContent = `${e0.signer_name || "You"} · sent ${(e0.created_at || "").slice(0, 10)} · signing with DocuSign takes about 2 minutes.`;
            // v49p — give the hero card a Download button (user request) so the
            // document can be saved without entering the signing ceremony.
            const btnRow = [...nextCard.querySelectorAll("div")].find((d) =>
              d.querySelector(":scope > a.pmc-btn, :scope > button.pmc-btn"));
            if (btnRow && !btnRow.querySelector("[data-dl-btn]")) {
              const dl = document.createElement("a");
              dl.href = "#";
              dl.className = "pmc-btn pmc-btn--secondary";
              dl.textContent = "Download";
              dl.setAttribute("data-dl-btn", "1");
              dl.setAttribute("data-envelope-id", e0.envelope_id);
              dl.setAttribute("data-testid", "sig-hero-download");
              btnRow.insertBefore(dl, btnRow.lastElementChild);
            }
          } else {
            nextCard.style.display = "none";
          }
        }

        // Status table rows
        const rows = Array.from(root.querySelectorAll("tbody tr"));
        rows.forEach((r, i) => {
          const env = items[i];
          if (!env) { r.style.display = "none"; return; }
          const ref = r.querySelector(".pmc-ref");
          if (ref) ref.textContent = env.award_ref || env.envelope_id || "—";
          const ttl = r.querySelector("td div");
          if (ttl) ttl.textContent = env.subject || env.kind || "Document";
          const pill = r.querySelector(".pmc-pill");
          if (pill) {
            const map = {
              sent: ["Awaiting your signature", "pmc-pill--warning"],
              delivered: ["Awaiting your signature", "pmc-pill--warning"],
              completed: ["Completed", "pmc-pill--success"],
              voided: ["Cancelled", ""],
              declined: ["Declined", ""],
            };
            const [txt, cls] = map[env.status] || [env.status, ""];
            pill.textContent = txt;
            pill.className = `pmc-pill ${cls}`.trim();
          }
          // Row-level action: pending envelopes get Review & sign wired to
          // this specific envelope; completed rows keep View/Download labels.
          const btn = r.querySelector("a.pmc-btn, button.pmc-btn");
          if (btn) {
            btn.setAttribute("data-envelope-id", env.envelope_id);
            if (env.status === "sent" || env.status === "delivered") btn.textContent = "Review & sign";
            else if (env.status === "completed") btn.textContent = "View";
          }
          const det = r.querySelectorAll("td")[2];
          if (det) det.textContent = `Sent ${(env.created_at || "").slice(0, 10)} · ${env.signer_name || ""}`;
        });
        // If the page has no envelopes at all, drop a friendly empty note
        const table = root.querySelector(".pmc-table");
        if (table && !items.length) {
          const note = document.createElement("div");
          note.className = "pmc-muted";
          note.style.cssText = "padding:20px;text-align:center;font-size:14px";
          note.textContent = "Nothing to sign right now — award documents will appear here when PMC sends them.";
          table.replaceWith(note);
        }
      } catch (e) { console.debug("VendorSignatures skip:", e); }
    })();
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Vendor: Account & Security
// ────────────────────────────────────────────────────────────────────
export function useVendorAccountLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const me = await vendorApi.me().catch(() => null);
        if (!me) return;
        const root = document.querySelector('[data-pmc-e-page="vendor-account-e"]');
        if (!root) return;
        const h1 = root.querySelector("h1"); if (h1) h1.textContent = "Account & security";
        // email + phone + 2FA state
        root.querySelectorAll("dd").forEach((dd, i) => {
          if (i === 0 && me.email) dd.textContent = me.email;
          if (i === 1 && me.contact_name) dd.textContent = me.contact_name;
          if (i === 2 && me.phone) dd.textContent = me.phone;
        });
      } catch (e) { console.debug("VendorAccount skip:", e); }
    })();
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Vendor: Alerts (uses notifications API when available)
// ────────────────────────────────────────────────────────────────────
export function useVendorAlertsLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/notifications").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="vendor-alerts-e"]');
        if (!root) return;
        const items = res.items || res || [];
        _patchKpiFigures(root, [items.length, items.filter((n) => !n.read_at).length]);
      } catch (e) { console.debug("VendorAlerts skip:", e); }
    })();
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Vendor: Reviews
// ────────────────────────────────────────────────────────────────────
export function useVendorReviewsLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const me = await vendorApi.me().catch(() => null);
        if (!me?.vendor_ref) return;
        const res = await api.get(`/api/v1/vendors/${me.vendor_ref}/reviews`).then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="vendor-reviews-e"]');
        if (!root) return;
        const items = res.items || res || [];
        const avg = items.length ? (items.reduce((s, r) => s + (r.stars || 0), 0) / items.length).toFixed(1) : "—";
        _patchKpiFigures(root, [avg, items.length]);
      } catch (e) { console.debug("VendorReviews skip:", e); }
    })();
  }, [enabled]);
}

// ────────────────────────────────────────────────────────────────────
// Vendor: Bid workspace  (uses :bidId from URL)
// ────────────────────────────────────────────────────────────────────
export function useVendorBidWorkspaceLive({ enabled = true, bidId } = {}) {
  useEffect(() => {
    if (!enabled || !bidId) return;
    (async () => {
      try {
        const bid = await bidApi.get(bidId).catch(() => null);
        if (!bid) return;
        const root = document.querySelector('[data-pmc-e-page="vendor-bid-workspace-e"]');
        if (!root) return;
        const ref = root.querySelector(".pmc-ref"); if (ref) ref.textContent = bid.bid_ref;
        const h1 = root.querySelector("h1"); if (h1) h1.textContent = bid.notice_title || bid.notice_ref || "Bid workspace";
      } catch (e) { console.debug("BidWorkspace skip:", e); }
    })();
  }, [enabled, bidId]);
}

// ────────────────────────────────────────────────────────────────────
// Admin: helper that just refreshes KPI numbers from a stats bundle
// ────────────────────────────────────────────────────────────────────
async function _adminBundle() {
  const [notices, vendors, packages, stats, escrow, bids] = await Promise.all([
    publicApi.listNotices({}).catch(() => ({ items: [] })),
    api.get("/api/v1/vendors/all").then((r) => r.data).catch(() => ({ items: [] })),
    api.get("/api/v1/packages/all").then((r) => r.data).catch(() => ({ items: [] })),
    publicApi.publicStats().catch(() => ({})),
    api.get("/api/v1/meta/public/escrow-summary").then((r) => r.data).catch(() => null),
    api.get("/api/v1/bids").then((r) => r.data).catch(() => ({ items: [] })),
  ]);
  return {
    notices: notices.items || [],
    vendors: vendors.items || vendors.vendors || vendors || [],
    packages: packages.items || packages.packages || packages || [],
    stats: stats || {},
    escrow: escrow || {},
    bids: bids.items || bids || [],
  };
}

export function useAdminProgrammeLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const b = await _adminBundle();
        const root = document.querySelector('[data-pmc-e-page="admin-programme-e"]');
        if (!root) return;
        const openN = b.notices.filter((n) => !n.submission_deadline || new Date(n.submission_deadline) > new Date());
        _patchKpiFigures(root, [openN.length, b.vendors.length, b.packages.length, `$${Math.round(b.escrow.total_usd_equiv || 0).toLocaleString()}`]);
      } catch (e) { console.debug("AdminProgramme skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminAuditLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/audit-events", { params: { limit: 20 } }).then((r) => r.data).catch(() => null);
        const root = document.querySelector('[data-pmc-e-page="admin-audit-e"]');
        if (!root || !res) return;
        const events = res.items || res || [];
        _patchKpiFigures(root, [events.length]);
      } catch (e) { console.debug("AdminAudit skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminCorrigendaLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await publicApi.listNotices({});
        const root = document.querySelector('[data-pmc-e-page="admin-corrigenda-e"]');
        if (!root) return;
        const corr = (res.items || []).filter((n) => n.deadline_last_amended_by_corr);
        _patchKpiFigures(root, [corr.length]);
      } catch (e) { console.debug("AdminCorrigenda skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminWorkPackagesLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/packages/all").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="admin-work-packages-e"]');
        if (!root) return;
        const items = res.items || res || [];
        _patchKpiFigures(root, [items.length]);
        _patchTableRefs(root, items.map((p) => ({ ref: p.package_ref, title: p.title })));
      } catch (e) { console.debug("AdminWorkPackages skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminCatalogLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/packages/all").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="admin-catalog-e"]');
        if (!root) return;
        _patchKpiFigures(root, [(res.items || res || []).length]);
      } catch (e) { console.debug("AdminCatalog skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminRegistrationsLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/registrations").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="admin-registrations-e"]');
        if (!root) return;
        const items = res.items || res || [];
        const pending = items.filter((r) => r.status === "pending" || r.status === "submitted").length;
        _patchKpiFigures(root, [items.length, pending]);
        _patchTableRefs(root, items.map((r) => ({ ref: r.registration_ref || r.id, title: r.company_name || r.contact_name })));
      } catch (e) { console.debug("AdminRegistrations skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminVendorKycLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/vendors/all").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="admin-vendor-kyc-e"]');
        if (!root) return;
        const items = res.items || res.vendors || res || [];
        const pending = items.filter((v) => v.kyc_status === "pending").length;
        const verified = items.filter((v) => v.kyc_status === "verified").length;
        _patchKpiFigures(root, [pending, verified]);
      } catch (e) { console.debug("AdminVendorKyc skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminVendorIntelLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/vendor-intel/pending-count").then((r) => r.data).catch(() => ({ count: 0 }));
        const root = document.querySelector('[data-pmc-e-page="admin-vendor-intel-e"]');
        if (!root) return;
        _patchKpiFigures(root, [res.count]);
      } catch (e) { console.debug("AdminVendorIntel skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminBiddingOpsLive({ enabled = true, tick = 0 } = {}) {
  useEffect(() => {
    if (!enabled) return;
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get("/api/v1/bids").then((r) => r.data).catch(() => []);
        if (cancelled) return;
        const root = document.querySelector('[data-pmc-e-page="admin-bidding-ops-e"]');
        if (!root) return;
        const items = Array.isArray(res) ? res : (res.items || []);

        // Bucket each bid → supplier (waiting on vendor), pmc (waiting on
        // a PMC role), awarded (closed L1). Everything else is "other" and
        // shown only under the All tab.
        const supplierS = new Set(["emd_pending", "submitted"]);
        const awardedS = new Set(["awarded", "closed"]);
        const rejected = new Set(["rejected", "withdrawn"]);
        // Stage index mirrors the 6-step Escrow→Committee pipeline.
        const stageIndex = {
          emd_paid: 1, escrow_accepted: 2, admin_flagged: 3,
          certifier_cleared: 4, legal_cleared: 5, accounting_cleared: 6,
        };
        const stageOwner = ["Supplier","Escrow agent","Tender desk","Certifier","Legal counsel","Accounts"];
        const stageLabel = ["Pay EMD","Confirm receipt","Flag for review","Site inspection","KYC clearance","Sign-off"];

        // Flow counters
        const flow = { emd:0, escrow:0, admin:0, certifier:0, legal:0, accounts:0, awarded:0 };
        const tabCounts = { pmc:0, supplier:0, awarded:0, all:0 };
        let testCount = 0;
        const rows = [];
        let anomalies = 0;

        items.forEach((b) => {
          const st = b.status || "submitted";
          if (rejected.has(st)) return; // hide withdrawn/rejected from view
          const ref = b.bid_ref || b.id || "—";
          const _v = (b.vendor_ref || "").toLowerCase();
          const _t = (b.notice_title || b.title || "").toLowerCase();
          const isTest = !!(b.is_demo || _v.includes("test") || _t.startsWith("test") || (b.bid_ref || "").toLowerCase().includes("test"));

          let group, next, ownerIdx, dots;
          if (supplierS.has(st)) {
            group = "supplier";
            next = "Pay EMD";
            ownerIdx = 0;
            dots = ["n","","","","",""];
            flow.emd++;
          } else if (awardedS.has(st)) {
            group = "awarded";
            next = "Awarded";
            ownerIdx = null;
            dots = ["d","d","d","d","d","d"];
            flow.awarded++;
          } else {
            group = "pmc";
            const idx = stageIndex[st] || 1;
            next = stageLabel[idx] || "Review";
            ownerIdx = idx;
            dots = Array(6).fill("").map((_, i) => i < idx ? "d" : i === idx ? "n" : "");
            if (idx === 1) flow.escrow++;
            else if (idx === 2) flow.admin++;
            else if (idx === 3) flow.certifier++;
            else if (idx === 4) flow.legal++;
            else if (idx === 5) flow.accounts++;
          }
          tabCounts[group] = (tabCounts[group] || 0) + 1;
          tabCounts.all++;
          if (isTest) testCount++;

          // Waiting age
          const updatedAt = b.updated_at || b.created_at;
          let age = "";
          if (updatedAt) {
            const days = Math.floor((Date.now() - new Date(updatedAt)) / 86400000);
            age = days > 0 ? `Waiting ${days}d` : "Waiting today";
          }

          // Price anomaly: bid vs notice.budget_amount
          const price = Number(b.price_amount || 0);
          const budget = Number(b.notice_budget_amount || b.notice?.budget_amount || 0);
          let anomHtml = "";
          if (price && budget && price > budget * 1.5) {
            const times = (price / budget).toFixed(price / budget > 100 ? 0 : 1);
            anomHtml = `<div class="bo-flag"><svg class="pmc-ico" aria-hidden="true"><use href="#i-flag"/></svg>Price ${times}× estimate</div>`;
            anomalies++;
          }

          // EMD line
          const emdAmt = Number(b.emd_due_amount || b.emd_amount || 0);
          const emdCur = b.emd_currency || b.price_currency || "USD";
          const emdPaid = b.emd_paid_at || b.emd_status === "paid" || st === "emd_paid" || (stageIndex[st] || 0) >= 2 || awardedS.has(st);
          let emdLine;
          if (!emdAmt) {
            emdLine = `EMD <span>—</span>`;
          } else if (emdPaid) {
            emdLine = `EMD <b>${emdCur} ${emdAmt.toLocaleString()}</b> <span style="color:var(--success);font-weight:600">· paid</span>`;
          } else if (b.emd_link_sent_at) {
            emdLine = `EMD <b>${emdCur} ${emdAmt.toLocaleString()}</b> <span style="color:var(--warning);font-weight:600">· link sent</span>`;
          } else {
            emdLine = `EMD <span>not paid</span>`;
          }

          // Action button — real endpoints only (same ones the legacy panel used)
          let actionHtml;
          if (group === "awarded") {
            actionHtml = `<button type="button" class="pmc-btn pmc-btn--ghost pmc-btn--sm" data-bo-action="view" data-bid-id="${b.id || ""}">View</button>`;
          } else if (group === "supplier") {
            actionHtml = emdAmt > 0
              ? `<button type="button" class="pmc-btn pmc-btn--secondary pmc-btn--sm" data-bo-action="send" data-bid-id="${b.id || ""}">${b.emd_link_sent_at ? "Resend link" : "Send link"}</button>`
              : `<button type="button" class="pmc-btn pmc-btn--secondary pmc-btn--sm" data-bo-action="review" data-bid-id="${b.id || ""}">Review</button>`;
          } else if (st === "escrow_accepted") {
            actionHtml = `<button type="button" class="pmc-btn pmc-btn--primary pmc-btn--sm" data-bo-action="flag" data-bid-id="${b.id || ""}">Flag to certifier</button>`;
          } else {
            actionHtml = `<button type="button" class="pmc-btn pmc-btn--primary pmc-btn--sm" data-bo-action="review" data-bid-id="${b.id || ""}">Review</button>`;
          }

          const disabledAttr = group === "awarded" || group === "pmc" ? "disabled" : "";
          const stepLabel = ownerIdx == null ? "Closed"
                          : `Step ${ownerIdx + 1}/6 · ${stageOwner[ownerIdx] || "—"}`;
          const priceStr = price ? `${b.price_currency || "USD"} ${price.toLocaleString()}` : "—";
          const title = b.notice_title || b.title || "(Untitled bid)";
          const vendor = b.vendor_ref || b.company_name || "—";
          const notice = b.notice_ref || "—";

          rows.push(
            `<tr class="bo-r${isTest ? " is-test" : ""}" data-g="${group}" data-test="${isTest ? 1 : 0}" data-ref="${ref}" data-bid-id="${b.id || ""}">` +
            `<td style="width:34px"><input type="checkbox" class="chk" ${disabledAttr} aria-label="Select ${ref}"/></td>` +
            `<td><div class="bo-ref">${ref}${isTest ? '<span class="bo-test">Test</span>' : ""}</div><div class="bo-t">${title}</div><div class="bo-sub">${notice} · ${vendor}</div></td>` +
            `<td class="num"><b>${priceStr}</b>${anomHtml}<div class="bo-emd">${emdLine}</div></td>` +
            `<td style="width:170px"><span class="bo-dots">${dots.map((d) => `<i class="${d}"></i>`).join("")}</span><div class="bo-next" style="margin-top:6px">${next}</div><div class="bo-sub">${stepLabel}</div>${age ? `<div class="bo-sub">${age}</div>` : ""}</td>` +
            `<td class="bo-act">${actionHtml}<button type="button" class="pmc-ib bo-more" aria-label="More actions" title="Hold · Reject · View history" data-bo-action="review" data-bid-id="${b.id || ""}">⋯</button></td>` +
            `</tr>`
          );
        });

        const tbody = root.querySelector("#bo-rows");
        if (tbody) {
          tbody.innerHTML = rows.length ? rows.join("") : `<tr><td colspan="5" class="bo-empty">No bids in the pipeline yet.</td></tr>`;
        }
        root._bids = items;
        // Update flow counters
        Object.entries(flow).forEach(([k, v]) => {
          root.querySelectorAll(`[data-flow-count="${k}"]`).forEach((el) => { el.textContent = v; });
          // hot glow on stages with load
          const step = root.querySelector(`.bo-step[data-flow="${k}"]`);
          if (step && k !== "awarded") {
            step.classList.toggle("hot", v > 0);
            step.classList.toggle("sup", v === 0 && k === "emd");
          }
        });
        // Tab counts
        Object.entries(tabCounts).forEach(([k, v]) => {
          root.querySelectorAll(`[data-tab-count="${k}"]`).forEach((el) => { el.textContent = v; });
        });
        // Subtitle + hidden-test badge + sidebar counter
        const totalEl = root.querySelector("[data-bo-total]");
        if (totalEl) totalEl.textContent = tabCounts.all;
        const tc = root.querySelector("[data-bo-test-count]");
        if (tc) tc.textContent = testCount;
        const sideCount = root.querySelector('[data-testid="side-bidding-count"]');
        if (sideCount) sideCount.textContent = tabCounts.pmc;
        // Anomaly callout
        const callout = root.querySelector("#bo-anomaly-callout");
        const acount = root.querySelector("#bo-anomaly-count");
        if (callout && acount) {
          if (anomalies > 0) { callout.style.display = "flex"; acount.textContent = anomalies; }
          else { callout.style.display = "none"; }
        }

        // Fetch open committee for the side panel
        try {
          const committees = await api.get("/api/v1/committees").then((r) => r.data).catch(() => []);
          const open = (Array.isArray(committees) ? committees : []).find((c) => c.status === "open");
          const body = root.querySelector("#bo-committee-body");
          const pill = root.querySelector("#bo-committee-pill");
          if (open && body) {
            pill.textContent = "Open"; pill.className = "pmc-pill pmc-pill--success";
            const ext = (open.external_invitees || []).filter((i) => i.status === "accepted").length;
            body.innerHTML =
              `<div><span class="pmc-ref" style="color:var(--ink)">${open.notice_ref}</span><div class="pmc-muted" style="font-size:13px">${(open.member_ids||[]).length} internal · ${ext} external accepted · quorum ${open.quorum}</div></div>` +
              `<div style="display:flex;gap:8px"><a href="/admin/e/evaluation" class="pmc-btn pmc-btn--secondary pmc-btn--sm">Open room</a><a href="/admin/e/evaluation" class="pmc-btn pmc-btn--ghost pmc-btn--sm">Invite</a></div>`;
          } else if (pill) {
            pill.textContent = "None"; pill.className = "pmc-pill";
          }
        } catch (e) { /* committee endpoint requires admin auth; ignore */ }
      } catch (e) { console.debug("AdminBiddingOps skip:", e); }
    })();
    return () => { cancelled = true; };
  }, [enabled, tick]);
}

export function useAdminEscrowLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const s = await api.get("/api/v1/meta/public/escrow-summary").then((r) => r.data).catch(() => null);
        const root = document.querySelector('[data-pmc-e-page="admin-escrow-e"]');
        if (!root || !s) return;
        _patchKpiFigures(root, [`$${Math.round(s.total_usd_equiv || 0).toLocaleString()}`, s.bids_paid, s.bids_pending]);
      } catch (e) { console.debug("AdminEscrow skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminBillingLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const s = await api.get("/api/v1/meta/public/escrow-summary").then((r) => r.data).catch(() => null);
        const root = document.querySelector('[data-pmc-e-page="admin-billing-e"]');
        if (!root || !s) return;
        _patchKpiFigures(root, [`$${Math.round(s.total_usd_equiv || 0).toLocaleString()}`]);
      } catch (e) { console.debug("AdminBilling skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminEvaluationsLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/bids").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="admin-evaluation-list-e"], [data-pmc-e-page="admin-evaluation-e"]');
        if (!root) return;
        const items = (res.items || res || []).filter((b) => ["evaluating","tech_eval","comm_eval"].includes(b.status));
        _patchKpiFigures(root, [items.length]);
      } catch (e) { console.debug("AdminEvaluations skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminAwardsLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/bids").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="admin-awards-e"], [data-pmc-e-page="admin-l1-award-e"]');
        if (!root) return;
        const awarded = (res.items || res || []).filter((b) => b.status === "awarded");
        _patchKpiFigures(root, [awarded.length]);
      } catch (e) { console.debug("AdminAwards skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminDocuSignLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/bids").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="admin-docusign-e"]');
        if (!root) return;
        const sig = (res.items || res || []).filter((b) => b.status === "awaiting_signature");
        _patchKpiFigures(root, [sig.length]);
      } catch (e) { console.debug("AdminDocuSign skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminEventsLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/audit-events", { params: { limit: 30 } }).then((r) => r.data).catch(() => null);
        const root = document.querySelector('[data-pmc-e-page="admin-events-e"]');
        if (!root || !res) return;
        _patchKpiFigures(root, [(res.items || res || []).length]);
      } catch (e) { console.debug("AdminEvents skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminEngagementsLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/notices/admin/all").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="admin-engagements-e"]');
        if (!root) return;
        _patchKpiFigures(root, [(res.items || res || []).length]);
      } catch (e) { console.debug("AdminEngagements skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminTenderBuilderLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/notices/admin/all").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="admin-tender-builder-e"]');
        if (!root) return;
        const items = res.items || res || [];
        const drafts = items.filter((n) => n.is_published === false).length;
        _patchKpiFigures(root, [drafts, items.length]);
      } catch (e) { console.debug("AdminTenderBuilder skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminBoqLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/boqs").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="admin-boq-contracts-e"]');
        if (!root) return;
        _patchKpiFigures(root, [(res.items || res || []).length]);
      } catch (e) { console.debug("AdminBoq skip:", e); }
    })();
  }, [enabled]);
}

export function useAdminPermissionsLive({ enabled = true } = {}) {
  useEffect(() => {
    if (!enabled) return;
    (async () => {
      try {
        const res = await api.get("/api/v1/staff").then((r) => r.data).catch(() => ({ items: [] }));
        const root = document.querySelector('[data-pmc-e-page="admin-permissions-e"]');
        if (!root) return;
        _patchKpiFigures(root, [(res.items || res || []).length]);
      } catch (e) { console.debug("AdminPermissions skip:", e); }
    })();
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
        const [notices, vendors, packages, stats, escrow, bids, auditEvents] = await Promise.all([
          publicApi.listNotices({}).catch(() => ({ items: [] })),
          api.get("/api/v1/vendors/all").then((r) => r.data).catch(() => ({ items: [] })),
          api.get("/api/v1/packages/all").then((r) => r.data).catch(() => ({ items: [] })),
          publicApi.publicStats().catch(() => ({})),
          api.get("/api/v1/meta/public/escrow-summary").then((r) => r.data).catch(() => null),
          api.get("/api/v1/bids").then((r) => r.data).catch(() => []),
          api.get("/api/v1/audit-events", { params: { limit: 6 } }).then((r) => r.data).catch(() => []),
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

        const stages = document.querySelectorAll('[data-pmc-e-page="admin-dashboard-e"] .ad-pipe a');
        stages.forEach((a, i) => {
          const c = a.querySelector(".c");
          const bar = a.querySelector(".vb i");
          const l2 = a.querySelector(".l2");
          if (c) c.textContent = stageCounts[i] ?? 0;
          if (bar) {
            const max = Math.max(1, ...stageCounts);
            bar.style.height = `${Math.max(4, Math.round((stageCounts[i] || 0) / max * 100))}%`;
          }
          if (l2 && i === 3) l2.textContent = closingThisWeek ? `${closingThisWeek} CLOSE THIS WEEK` : "";
          a.classList.toggle("hot", i === 3 && (stageCounts[i] || 0) > 0);
        });
        const activeEl = document.querySelector('[data-pmc-e-page="admin-dashboard-e"] [data-dash-active]');
        if (activeEl) activeEl.textContent = stageCounts.reduce((s, x) => s + (x || 0), 0);
        const dateEl = document.querySelector('[data-pmc-e-page="admin-dashboard-e"] [data-dash-date]');
        if (dateEl) dateEl.textContent = `FY 2026–27 · ${new Date().toLocaleDateString("en-GB", { weekday: "short", day: "2-digit", month: "short", year: "numeric" }).toUpperCase()}`;

        // KPI cards
        const kpis = document.querySelectorAll('[data-pmc-e-page="admin-dashboard-e"] .pmc-kpi');
        if (kpis.length >= 4) {
          const f0 = kpis[0].querySelector(".pmc-figure");
          const s0 = kpis[0].querySelector(".s");
          const f1 = kpis[1].querySelector(".pmc-figure");
          const f2 = kpis[2].querySelector(".pmc-figure");
          const s2 = kpis[2].querySelector(".s");
          const f3 = kpis[3].querySelector(".pmc-figure");
          const s3 = kpis[3].querySelector(".s");
          const bidItems = Array.isArray(bids) ? bids : (bids.items || []);
          const awardedBids = bidItems.filter((b) => b.status === "awarded" || b.status === "closed").length;
          if (f2) f2.textContent = bidItems.filter((b) => !["awarded","closed","rejected","withdrawn"].includes(b.status)).length;
          if (s2) s2.textContent = `${awardedBids} awarded`;
          if (f3) f3.textContent = vItems.length || stats.suppliers_approved || 0;
          if (s3) s3.textContent = "KYC verified";
          if (f1) f1.textContent = openN.filter((n) => n.form_of_contract || n.is_published).length || 0;
          if (f0 && escrow) {
            const total = escrow.total_usd_equiv || 0;
            f0.textContent = `$${Math.round(total).toLocaleString()}`;
            if (s0) s0.textContent = `${escrow.bids_pending || 0} pending · ${escrow.bids_paid || 0} paid`;
          }
        }

        // Attention strip
        const bidItems = Array.isArray(bids) ? bids : (bids.items || []);
        const emdWaiting = bidItems.filter((b) => b.status === "emd_pending" || b.status === "submitted").length;
        const attn = (k) => document.querySelector(`[data-pmc-e-page="admin-dashboard-e"] [data-attn="${k}"]`);
        if (attn("closing")) attn("closing").textContent = String(closingThisWeek).padStart(2, "0");
        if (attn("approvals")) attn("approvals").textContent = String(draft).padStart(2, "0");
        if (attn("emd")) attn("emd").textContent = String(emdWaiting).padStart(2, "0");

        // Bids waiting on a step
        const bidsBody = document.getElementById("dash-bids-rows");
        if (bidsBody) {
          const inFlight = bidItems
            .filter((b) => !["awarded","closed","rejected","withdrawn"].includes(b.status))
            .sort((a, b2) => new Date(a.updated_at || a.created_at || 0) - new Date(b2.updated_at || b2.created_at || 0))
            .slice(0, 5);
          const statusPill = (st) => {
            const warn = st === "emd_pending" || st === "submitted";
            const label = { emd_pending: "Awaiting EMD", submitted: "Awaiting EMD", emd_paid: "EMD paid",
              escrow_accepted: "Escrow accepted", admin_flagged: "Admin flagged", certifier_cleared: "Certifier cleared",
              legal_cleared: "Legal cleared", accounting_cleared: "Accounts cleared", on_hold: "On hold" }[st] || st;
            return `<span class="pmc-pill pmc-pill--${warn ? "warning" : "info"}">${label}</span>`;
          };
          bidsBody.innerHTML = inFlight.length
            ? inFlight.map((b) => {
                const price = b.price_amount != null ? `${b.price_currency || "USD"} ${Number(b.price_amount).toLocaleString()}` : "—";
                const next = (b.active_step && b.active_step.label) || "—";
                return `<tr data-testid="dash-bid-row"><td><div style="font-weight:600">${b.notice_title || b.title || "(Untitled bid)"}</div><div style="font-size:12px;color:var(--ink-muted)"><span class="pmc-ref">${b.bid_ref || "—"}</span> · ${b.vendor_ref || b.company_name || "—"}</div></td><td class="num" style="font-weight:600">${price}</td><td>${statusPill(b.status)}</td><td class="pmc-next-owner">${next}</td><td style="text-align:right;width:40px"><a href="/admin/e/bidding" aria-label="Open in bidding ops"><svg class="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></a></td></tr>`;
              }).join("")
            : `<tr><td colspan="5" style="padding:24px;text-align:center;color:var(--ink-muted)">No bids waiting on a step right now.</td></tr>`;
        }

        // Closing this week
        const cwBody = document.getElementById("dash-closing-rows");
        const cwCount = document.querySelector('[data-pmc-e-page="admin-dashboard-e"] [data-cw-count]');
        if (cwBody) {
          const closing = openN
            .filter((n) => n.submission_deadline && (new Date(n.submission_deadline) - new Date()) < 7 * 86400 * 1000)
            .sort((a, b) => new Date(a.submission_deadline) - new Date(b.submission_deadline))
            .slice(0, 5);
          if (cwCount) cwCount.textContent = String(closing.length).padStart(2, "0");
          cwBody.innerHTML = closing.length
            ? closing.map((n) => {
                const sealed = bidItems.filter((b) => b.notice_ref === n.notice_ref).length;
                return `<tr data-testid="dash-closing-row"><td><div style="font-weight:500">${n.title || "(Untitled)"}</div><div class="pmc-ref">${n.notice_ref || "—"}${n.category ? " · " + n.category : ""}${n.country ? " · " + n.country : ""}</div></td><td class="num">${String(sealed).padStart(2, "0")}</td><td class="num">${String(n.clarifications_count || 0).padStart(2, "0")}</td><td class="num"><span class="closes">${relTime(n.submission_deadline)}</span></td></tr>`;
              }).join("")
            : `<tr><td colspan="4" style="padding:24px;text-align:center;color:var(--ink-muted)">Nothing closes this week.</td></tr>`;
        }

        // Approvals queue — draft notices pending publish
        const apprList = document.getElementById("dash-approvals");
        const apprPill = document.querySelector('[data-pmc-e-page="admin-dashboard-e"] [data-appr-pill]');
        if (apprList) {
          const drafts = nItems.filter((n) => n.is_published === false)
            .sort((a, b) => new Date(a.created_at || 0) - new Date(b.created_at || 0))
            .slice(0, 3);
          if (apprPill) apprPill.textContent = `${drafts.length} of ${draft} shown`;
          apprList.innerHTML = drafts.length
            ? drafts.map((n) => {
                const age = n.created_at ? new Date(n.created_at).toLocaleDateString("en-GB", { day: "2-digit", month: "short" }) : "";
                return `<li data-testid="dash-approval-row"><span><span class="k">Publish</span><span class="t" style="display:block">${n.notice_ref || "—"} — ${n.title || "(Untitled)"}</span><span class="s">${n.created_by_email || "Tender desk"}${age ? " · " + age : ""}</span></span><a href="/admin/e/notices" class="pmc-btn pmc-btn--secondary pmc-btn--sm">Review</a></li>`;
              }).join("")
            : `<li class="ad-appr__empty">No drafts awaiting approval.</li>`;
        }

        // Audit stream
        const auditList = document.getElementById("dash-audit");
        if (auditList) {
          const events = Array.isArray(auditEvents) ? auditEvents : [];
          auditList.innerHTML = events.length
            ? events.map((e) => {
                let t = "—";
                try { t = new Date(e.at).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit" }); } catch {}
                const detail = [e.target_id, e.actor_email].filter(Boolean).join(" · ");
                return `<li data-testid="dash-audit-row"><time>${t}</time><span><span class="a">${e.event_type || "event"}</span><span class="s" style="display:block">${detail}</span></span></li>`;
              }).join("")
            : `<li><time>—</time><span class="s">No audit events yet.</span></li>`;
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
      } catch (e) {
        if (process.env.NODE_ENV !== "production") console.debug("Admin live data skipped:", e);
      }
    })();
    return () => { cancelled = true; };
  }, [enabled]);
}
