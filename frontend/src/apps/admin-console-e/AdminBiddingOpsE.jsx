import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { bidApi, staffApi, showApiError } from "@/lib/api";
import { useUiTheme } from "@/context/UiThemeContext";
import { useAdminBiddingOpsLive } from "@/lib/pmcELiveData";
import AdminAvatarMenu from "./AdminAvatarMenu";
import AdminSideNavE from "./AdminSideNavE";
import AssignSpecialistsModal from "../admin-console/bidding/AssignSpecialistsModal";
import MoneyFilterBar from "@/components/MoneyFilterBar";
import "./bidding-ops.css";

// Sidebar preserved from the existing admin console shell so nav stays
// consistent. Table body + right-side panels are hydrated by
// useAdminBiddingOpsLive from /api/v1/bids.
export default function AdminBiddingOpsE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [navOpen, setNavOpen] = useState(false);
  const navigate = useNavigate();
  const [tick, setTick] = useState(0);
  useAdminBiddingOpsLive({ enabled: isE, tick });

  // v56 — per-role specialist assignment. The row list + detail panel are
  // DOM-rendered by the live-data layer, so we expose the React opener via a
  // ref and render the modal from JSX.
  const [specialistFor, setSpecialistFor] = useState(null);
  const [staffList, setStaffList] = useState([]);
  const specialistOpenRef = useRef(null);
  specialistOpenRef.current = setSpecialistFor;
  useEffect(() => {
    if (!isE) return;
    staffApi.listStaff().then((r) => setStaffList(r || [])).catch(() => setStaffList([]));
  }, [isE]);
  const assignSpecialist = async (role, staffId) => {
    if (!specialistFor) return;
    try {
      const res = await bidApi.assign(specialistFor.id, role, staffId);
      toast.success(staffId ? "Specialist assigned" : "Assignment cleared");
      setTick((t) => t + 1);
      return res;
    } catch (e) { showApiError(e); }
  };

  // Wire tabs, hide-test, select-all, row selection — pure DOM so it
  // survives live-data innerHTML replacements.
  useEffect(() => {
    if (!isE) return;
    const root = document.querySelector('[data-pmc-e-page="admin-bidding-ops-e"]');
    if (!root) return;
    const paint = () => {
      const activeTab = root.querySelector('[data-tab][aria-selected="true"]');
      const tab = activeTab ? activeTab.dataset.tab : "pmc";
      const hide = root.querySelector('#bo-hidetest')?.checked;
      const q = (root._boq || "").toLowerCase();
      const allRows = root.querySelectorAll('.bo-r');
      // Recompute per-tab counts from the rows that WOULD appear under each tab
      // (respecting hide-test + search). Keeps the tab badges honest instead of
      // showing a static total that drifts from the rows actually rendered.
      const tabCounts = { pmc: 0, supplier: 0, awarded: 0, all: 0 };
      allRows.forEach((r) => {
        const isTest = r.dataset.test === "1";
        const g = r.dataset.g;
        const matches = (!q || r.textContent.toLowerCase().includes(q)) && !(hide && isTest);
        if (!matches) return;
        tabCounts.all++;
        if (g && tabCounts[g] !== undefined) tabCounts[g]++;
      });
      Object.entries(tabCounts).forEach(([k, v]) => {
        root.querySelectorAll(`[data-tab-count="${k}"]`).forEach((el) => { el.textContent = v; });
      });
      const totalEl = root.querySelector('[data-bo-total]');
      if (totalEl) totalEl.textContent = tabCounts.all;
      const sideCount = root.querySelector('[data-testid="side-bidding-count"]');
      if (sideCount) sideCount.textContent = tabCounts.pmc;
      // v51az — flow-step filter: which statuses belong to each pipeline step.
      const FLOW_STATUS = {
        emd: ["emd_pending", "submitted"],
        escrow: ["emd_paid"],
        admin: ["escrow_accepted"],
        certifier: ["admin_flagged"],
        legal: ["certifier_cleared"],
        accounts: ["legal_cleared", "accounting_cleared"],
        awarded: ["awarded", "closed"],
      };
      const flowFilter = root._flowFilter || "";
      const flowStatuses = flowFilter ? (FLOW_STATUS[flowFilter] || []) : null;
      // Now show/hide rows according to the active tab.
      let visible = 0;
      allRows.forEach((r) => {
        // v52cs — zero-EMD bids sit at the Escrow step (nothing for the
        // supplier to pay), so they must not match the EMD flow filter and
        // must match the Escrow filter instead.
        const rowSt = (r.dataset.status || "").toLowerCase();
        const zeroEmd = r.dataset.emd === "0";
        let flowOk = true;
        if (flowStatuses) {
          flowOk = flowStatuses.includes(rowSt);
          if (zeroEmd && ["emd_pending", "submitted"].includes(rowSt)) {
            flowOk = flowFilter === "escrow";
          }
        }
        const ok = (tab === "all" || r.dataset.g === tab) && !(hide && r.dataset.test === "1")
          && (!q || r.textContent.toLowerCase().includes(q))
          && flowOk;
        r.hidden = !ok;
        if (ok) visible++;
      });
      const empty = root.querySelector('#bo-empty');
      if (empty) empty.hidden = visible > 0;
      const shown = root.querySelector('#bo-shown');
      const total = allRows.length;
      if (shown) shown.textContent = total ? `Showing ${visible} of ${total}` : '';
    };
    const onTab = (e) => {
      const b = e.currentTarget;
      root.querySelectorAll('[data-tab]').forEach((x) => x.setAttribute('aria-selected', x === b ? 'true' : 'false'));
      paint();
    };
    const onHide = () => paint();
    // v51az — the pipeline step numbers (EMD → Escrow → Admin → Certifier →
    // Legal → Accounts → Awarded) were never wired to a click handler, so
    // clicking them did nothing ("none of them work"). Now: click a step to
    // filter the list to that stage (highlighted); click it again to clear.
    const onFlowClick = (e) => {
      e.preventDefault();
      e.stopPropagation();
      const stepEl = e.currentTarget;
      const key = stepEl.dataset.flow;
      const wasActive = root._flowFilter === key;
      root._flowFilter = wasActive ? "" : key;
      root.querySelectorAll('.bo-step').forEach((s) => {
        const active = !wasActive && s.dataset.flow === key;
        s.style.boxShadow = active ? "0 0 0 2px var(--primary, #0F3B2E) inset" : "";
        s.style.background = active ? "var(--brand-pale, #F3EFE4)" : "";
        s.setAttribute("aria-pressed", active ? "true" : "false");
      });
      paint();
    };
    root.querySelectorAll('.bo-step').forEach((s) => s.addEventListener('click', onFlowClick));
    const stageNames = ["EMD", "Escrow", "Admin", "Certifier", "Legal", "Accounts"];
    const stageOwners = ["Supplier", "Escrow agent", "Tender desk", "Certifier", "Legal counsel", "Accounts"];
    const stageIndexMap = { emd_paid: 1, escrow_accepted: 2, admin_flagged: 3, certifier_cleared: 4, legal_cleared: 5, accounting_cleared: 6 };
    const showDetail = (row) => {
      const b = (root._bids || []).find((x) => (x.id || "") === (row.dataset.bidId || ""));
      if (!b) return;
      const st = b.status || "submitted";
      const awarded = ["awarded", "closed"].includes(st);
      // v52cs — a zero-EMD bid is never "waiting on the supplier" for a
      // payment; it is auto-cleared past the EMD step to Escrow.
      const emdDueN = Number(b.emd_due_amount || b.emd_amount || 0);
      const supplier = ["emd_pending", "submitted"].includes(st) && emdDueN > 0;
      const idx = awarded ? 7 : supplier ? 0 : (stageIndexMap[st] || 1);
      const refEl = root.querySelector('#d-ref'); if (refEl) refEl.textContent = b.bid_ref || "—";
      const tEl = root.querySelector('#d-t'); if (tEl) tEl.textContent = b.notice_title || b.title || "(Untitled bid)";
      const pill = root.querySelector('#d-pill');
      if (pill) { pill.textContent = awarded ? "Awarded" : stageNames[Math.min(idx, 5)]; pill.className = "pmc-pill " + (awarded ? "pmc-pill--success" : supplier ? "pmc-pill--warning" : "pmc-pill--info"); }
      const price = b.price_amount != null ? `${b.price_currency || "USD"} ${Number(b.price_amount).toLocaleString()}` : "—";
      const emdAmt = Number(b.emd_due_amount || b.emd_amount || 0);
      const emdCur = b.emd_currency || b.price_currency || "USD";
      const emdPaid = b.emd_paid_at || b.emd_status === "paid" || idx >= 2 || awarded;
      const emdTxt = !emdAmt ? "Not due" : emdPaid ? `${emdCur} ${emdAmt.toLocaleString()} · paid` : b.emd_link_sent_at ? `${emdCur} ${emdAmt.toLocaleString()} · link sent` : `${emdCur} ${emdAmt.toLocaleString()} · not paid`;
      const kv = root.querySelector('#d-kv');
      if (kv) kv.innerHTML = `<dt>Notice</dt><dd class="pmc-ref" style="color:var(--ink)">${b.notice_ref ? `<a href="/notices/${encodeURIComponent(b.notice_ref)}" target="_blank" rel="noopener" data-testid="bo-detail-notice-link" style="color:var(--primary,#0F3B2E);text-decoration:underline">${b.notice_ref}</a>` : "—"}</dd><dt>Vendor</dt><dd>${b.vendor_ref || b.company_name || "—"}</dd><dt>Price</dt><dd>${price}</dd><dt>EMD</dt><dd>${emdTxt}</dd>`;
      // v51ay — documents block: previously the panel never listed the bid's
      // envelope files, so admins had no way to open them from Bidding Ops
      // ("unable to load the documents"). Links hit the authed upload
      // endpoint directly (admin cookie is attached by the browser).
      const docsWrap = root.querySelector('#d-docs');
      const docs = Array.isArray(b.documents) ? b.documents.filter((d) => d && d.key) : [];
      if (docsWrap) {
        docsWrap.innerHTML = docs.length
          ? `<div class="pmc-muted" style="font-size:11px;text-transform:uppercase;letter-spacing:1px">Envelope documents · ${docs.length}</div>` +
            docs.map((d) => `<a href="/api/v1/uploads/files/${encodeURIComponent(d.key)}" target="_blank" rel="noopener" data-testid="bo-doc-${encodeURIComponent(d.key).slice(-12)}"
                style="display:flex;justify-content:space-between;gap:8px;padding:6px 8px;border:1px solid rgba(15,59,46,.15);font-size:13px;color:var(--ink);text-decoration:none">
                <span style="overflow:hidden;text-overflow:ellipsis;white-space:nowrap">${d.filename || d.file_name || d.key}</span>
                <span class="pmc-muted" style="white-space:nowrap">${d.kind || "doc"}${d.size_bytes ? ` · ${Math.round(d.size_bytes/1024)} KB` : ""}</span></a>`).join("")
          : `<div class="pmc-muted" style="font-size:12px">No envelope documents attached.</div>`;
      }
      const tl = root.querySelector('#d-tl');
      if (tl) tl.innerHTML = stageNames.map((s, i) => { const c = awarded || i < idx ? "done" : i === idx ? "now" : ""; return `<div class="${c}"><span class="dot"></span><div><b>${s}</b><span>${stageOwners[i]}${c === "now" ? " · waiting" : c === "done" ? " · cleared" : ""}</span></div></div>`; }).join("");
      const act = root.querySelector('#d-act');
      if (act) {
        if (awarded) act.innerHTML = `<button class="pmc-btn pmc-btn--secondary" data-bo-action="view" data-bid-id="${b.id}">Open award</button>`;
        else if (supplier) act.innerHTML = (emdAmt > 0 ? `<button class="pmc-btn pmc-btn--primary" data-bo-action="send" data-bid-id="${b.id}">${b.emd_link_sent_at ? "Resend EMD link" : "Send EMD link"}</button>` : "") + `<button class="pmc-btn pmc-btn--secondary" data-bo-action="review" data-bid-id="${b.id}">Open bid</button>`;
        else if (st === "on_hold") act.innerHTML = `<div class="pmc-callout pmc-callout--warn" style="margin:0" data-testid="bo-detail-hold-note"><b>On hold.</b> ${b.hold_reason ? `Reason: ${b.hold_reason}. ` : ""}${b.held_by ? `Held by ${b.held_by}. ` : ""}The vendor cannot change anything until you resume.</div><button class="pmc-btn pmc-btn--primary" data-bo-action="resume" data-bid-id="${b.id}" data-testid="bo-resume-btn">Resume bid</button><div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><button class="pmc-btn pmc-btn--secondary" data-bo-action="review" data-bid-id="${b.id}">Open bid</button><button class="pmc-btn pmc-btn--danger" data-bo-action="reject" data-bid-id="${b.id}">Reject…</button></div>`;
        else act.innerHTML = (st === "escrow_accepted" ? `<button class="pmc-btn pmc-btn--primary" data-bo-action="flag" data-bid-id="${b.id}">Flag to certifier</button>` : `<button class="pmc-btn pmc-btn--primary" data-bo-action="review" data-bid-id="${b.id}">Open bid</button>`) + `<div style="display:grid;grid-template-columns:1fr 1fr;gap:8px"><button class="pmc-btn pmc-btn--secondary" data-bo-action="hold" data-bid-id="${b.id}">Hold…</button><button class="pmc-btn pmc-btn--danger" data-bo-action="reject" data-bid-id="${b.id}">Reject…</button></div>`;
      }
      // v56 — specialist assignment available on every non-terminal bid.
      if (act && !awarded) {
        act.innerHTML += `<button class="pmc-btn pmc-btn--secondary" data-bo-action="assign" data-bid-id="${b.id}" data-testid="assign-specialists-${b.bid_ref}" style="margin-top:4px">Assign specialists</button>`;
      }
    };
    const onRowClick = (e) => {
      if (e.target.closest('.chk') || e.target.closest('.bo-act')) return;
      const r = e.currentTarget;
      root.querySelectorAll('.bo-r').forEach((x) => x.classList.toggle('sel', x === r));
      showDetail(r);
    };
    const onChk = (e) => {
      e.stopPropagation();
      const n = root.querySelectorAll('.chk:checked').length;
      const bulk = root.querySelector('#bo-bulk');
      const bn = root.querySelector('#bo-bulkn');
      if (bulk) bulk.hidden = n === 0;
      if (bn) bn.textContent = `${n} selected`;
    };
    const onAction = async (e) => {
      const btn = e.target.closest('[data-bo-action]');
      if (!btn) return;
      e.preventDefault();
      e.stopPropagation();
      const bidId = btn.dataset.bidId;
      const act = btn.dataset.boAction;
      if (!bidId) return;
      if (act === 'review' || act === 'view') {
        // v51az — revert the v51as inline-panel behavior. Admins expect
        // Review / Open bid to OPEN the full bid detail page (documents,
        // history, audit) at /admin/bids/{id}, not toggle the right-side
        // tracker. The tracker still opens on plain row click.
        navigate(`/admin/bids/${bidId}`);
        return;
      }
      if (act === 'detail') {
        // ⋯ opens the right-side detail panel (Hold / Reject / History live there)
        const row = root.querySelector(`.bo-r[data-bid-id="${bidId}"]`);
        if (row) row.click();
        return;
      }
      if (act === 'assign') {
        // v56 — open the Assign-specialists modal for this bid.
        const bid = (root._bids || []).find((x) => (x.id || "") === bidId);
        if (bid) specialistOpenRef.current?.(bid);
        return;
      }
      // v51ab — confirmation dialog before sending the EMD payment link so
      // the admin can see WHICH vendor email the link is going to. Pulls
      // the recipient from root._bids (populated by useAdminBiddingOpsLive).
      if (act === 'send') {
        const bid = (root._bids || []).find((x) => (x.id || "") === bidId);
        const to = bid?.vendor_email || bid?.company_name;
        if (!to) {
          toast.error("Cannot find the vendor email for this bid.");
          return;
        }
        const ok = window.confirm(
          `Send the EMD payment link to:\n\n` +
          `  ${to}\n` +
          (bid?.company_name && bid?.vendor_email ? `  (${bid.company_name})\n` : "") +
          `\nBid ${bid?.bid_ref || ""} · ${bid?.price_currency || "USD"} ${Number(bid?.emd_due_amount || 0).toLocaleString()} due.\n\n` +
          `OK to send · Cancel to keep editing.`
        );
        if (!ok) return;
      }
      btn.disabled = true;
      try {
        if (act === 'send') {
          const r = await bidApi.sendEmdLink(bidId);
          toast.success(`EMD payment link emailed to ${r.emailed_to || "bidder"}`);
        } else if (act === 'flag') {
          await bidApi.decide(bidId, { action: "accept", role: "admin", notes: "" });
          toast.success("Bid flagged to certifier");
        } else if (act === 'hold') {
          const reason = window.prompt("Hold bid? Optional reason:", "") ?? "";
          await bidApi.decide(bidId, { action: "hold", role: "admin", notes: reason });
          toast.success("Bid put on hold");
        } else if (act === 'resume') {
          if (!window.confirm("Resume this bid? It returns to the exact step it was paused from.")) { btn.disabled = false; return; }
          await bidApi.decide(bidId, { action: "resume", role: "admin", notes: "" });
          toast.success("Bid resumed — back in the pipeline");
        } else if (act === 'reject') {
          if (!window.confirm("Reject this bid? This is recorded on the audit ledger.")) { btn.disabled = false; return; }
          await bidApi.decide(bidId, { action: "reject", role: "admin", notes: "" });
          toast.success("Bid rejected");
        }
        setTick((t) => t + 1);
        // v51aj — the detail panel (#d-act) only rebuilds on row click, so
        // after hold/resume/reject it kept showing the stale buttons (and the
        // disabled-in-flight "greyed Hold"). Re-open the panel for the same
        // bid once the live rows have been rebuilt so the on_hold note and
        // Resume button appear immediately. (v51ay — single refresh; the old
        // double-fire at 900ms + 1800ms made the panel reopen twice.)
        setTimeout(() => {
          const row = root.querySelector(`.bo-r[data-bid-id="${bidId}"]`);
          if (row) row.click();
        }, 1200);
      } catch (err) { showApiError(err); btn.disabled = false; }
    };
    const onBulkRemind = async (e) => {
      e.preventDefault();
      const ids = [...root.querySelectorAll('.chk:checked')].map((c) => c.closest('.bo-r')?.dataset.bidId).filter(Boolean);
      if (!ids.length) return;
      // v51ab — show the full list of recipient emails before firing a bulk
      // reminder so the admin never emails the wrong vendor cohort.
      const bids = root._bids || [];
      const recipients = ids
        .map((id) => bids.find((b) => (b.id || "") === id))
        .filter(Boolean);
      const preview = recipients
        .slice(0, 10)
        .map((b) => `  • ${b.vendor_email || b.company_name || b.bid_ref}`)
        .join("\n");
      const extra = recipients.length > 10 ? `\n  …and ${recipients.length - 10} more` : "";
      if (!window.confirm(
        `Send EMD reminder to ${ids.length} bidder${ids.length > 1 ? "s" : ""}:\n\n${preview}${extra}\n\nOK to send · Cancel to review.`
      )) return;
      let ok = 0, fail = 0;
      for (const id of ids) {
        try { await bidApi.sendEmdLink(id); ok++; } catch { fail++; }
      }
      if (ok) toast.success(`EMD link sent for ${ok} bid${ok > 1 ? "s" : ""}`);
      if (fail) toast.error(`${fail} reminder${fail > 1 ? "s" : ""} failed`);
      root.querySelectorAll('.chk:checked').forEach((c) => { c.checked = false; });
      const bulk = root.querySelector('#bo-bulk'); if (bulk) bulk.hidden = true;
      setTick((t) => t + 1);
    };
    const onBulkClear = (e) => {
      e.preventDefault();
      root.querySelectorAll('.chk:checked').forEach((c) => { c.checked = false; });
      const bulk = root.querySelector('#bo-bulk'); if (bulk) bulk.hidden = true;
    };
    const onExport = (e) => {
      e.preventDefault();
      const items = root._bids || [];
      const head = ["bid_ref", "notice_ref", "vendor", "price", "currency", "status"];
      const rowsCsv = items.map((b) => [b.bid_ref, b.notice_ref, b.vendor_ref || b.company_name || "", b.price_amount ?? "", b.price_currency || "", b.status || ""].map((x) => `"${String(x).replace(/"/g, '""')}"`).join(","));
      const blob = new Blob([[head.join(","), ...rowsCsv].join("\n")], { type: "text/csv" });
      const a = document.createElement("a");
      a.href = URL.createObjectURL(blob);
      a.download = `bidding-ops-${new Date().toISOString().slice(0, 10)}.csv`;
      a.click();
      URL.revokeObjectURL(a.href);
    };
    const onSearch = (e) => { root._boq = e.target.value.trim(); paint(); };
    root.querySelectorAll('[data-tab]').forEach((b) => b.addEventListener('click', onTab));
    root.querySelector('[data-testid="bo-search-input"]')?.addEventListener('input', onSearch);
    root.querySelector('#bo-hidetest')?.addEventListener('change', onHide);
    root.addEventListener('click', onAction);
    root.querySelector('[data-testid="bo-bulk-remind"]')?.addEventListener('click', onBulkRemind);
    root.querySelector('[data-testid="bo-bulk-clear"]')?.addEventListener('click', onBulkClear);
    root.querySelector('[data-testid="bo-export-btn"]')?.addEventListener('click', onExport);
    // MutationObserver: re-wire rows whenever live data re-renders them.
    const wireRows = () => {
      root.querySelectorAll('.bo-r').forEach((r) => {
        r.removeEventListener('click', onRowClick);
        r.addEventListener('click', onRowClick);
      });
      root.querySelectorAll('.chk').forEach((c) => {
        c.removeEventListener('click', onChk);
        c.addEventListener('click', onChk);
      });
      paint();
    };
    wireRows();
    const tbody = root.querySelector('#bo-rows');
    let mo;
    if (tbody) {
      mo = new MutationObserver(wireRows);
      mo.observe(tbody, { childList: true });
    }
    return () => { if (mo) mo.disconnect(); root.removeEventListener('click', onAction); root.querySelectorAll('.bo-step').forEach((s) => s.removeEventListener('click', onFlowClick)); };
  }, [isE, navigate]);

  // v51ab — client-side filter bar for the Bidding Ops row list. Hooks into
  // the DOM rows the live-data layer renders (data-testid="bo-table") and
  // filters by tender ref/title/vendor, creator, created-from/to and status.
  const [, setBoFilter] = useState({});
  const boFilterEl = (
    <MoneyFilterBar
      testid="bidding-ops-filter"
      scopeSelector='[data-pmc-e-page="admin-bidding-ops-e"] [data-testid="bo-table"] tbody#bo-rows'
      rowSelector=".bo-r"
      onChange={setBoFilter}
      showExpiring={false}
      showCreator={false}
      statusOptions={[
        { value: "emd_pending",         label: "EMD pending" },
        { value: "submitted",           label: "Submitted" },
        { value: "escrow_accepted",     label: "Escrow accepted" },
        { value: "admin_flagged",       label: "Admin flagged" },
        { value: "certifier_cleared",   label: "Certifier cleared" },
        { value: "legal_cleared",       label: "Legal cleared" },
        { value: "accounting_cleared",  label: "Accounting cleared" },
        { value: "awarded",             label: "Awarded" },
        { value: "closed",              label: "Closed" },
      ]}
    />
  );

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="admin-bidding-ops-e" data-pmc-e-page="admin-bidding-ops-e">
<div className={"pmc-adm" + (navOpen ? " pmc-adm--navopen" : "")}>
<AdminSideNavE active="Bidding ops" />
<button className="pmc-side__scrim" aria-label="Close menu" onClick={() => setNavOpen(false)} data-testid="admin-nav-scrim" />
<div className="pmc-adm__main">
<header className="pmc-atop"><button className="pmc-navtoggle" aria-label="Open menu" aria-expanded={navOpen} onClick={() => setNavOpen((v) => !v)} data-testid="admin-nav-toggle"><svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg></button>
  <div className="crumb">Money &amp; compliance / <b>Bidding ops</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" data-testid="admin-search-input" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r"><a href="/admin/e/tender-builder" className="pmc-btn pmc-btn--primary" data-testid="bo-create-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Create</a><button className="pmc-btn pmc-btn--secondary" data-help-open="" data-testid="bo-help-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button><button className="pmc-ib pmc-bell" aria-label="Alerts" data-testid="bo-bell-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">0</span></button><AdminAvatarMenu /></div>
</header>
<main className="pmc-amain">
  <div className="bo-head">
    <div><div className="pmc-eyebrow">Money &amp; compliance</div><h1>Bidding ops</h1><div className="pmc-muted" style={{fontSize:"14px"}} data-testid="bo-subtitle"><span data-bo-total>0</span> bids moving through clearance · every step is on the audit ledger</div></div>
    <div style={{display:"flex",gap:"8px"}}>
      <a href="#" className="pmc-btn pmc-btn--secondary" data-testid="bo-export-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Export</a>
      <a href="/admin/e/evaluation" className="pmc-btn pmc-btn--primary" data-testid="bo-form-committee-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg> Form committee</a>
    </div>
  </div>
  <section className="bo-flow" aria-label="Clearance pipeline" data-testid="bo-flow">
    <a href="#" className="bo-step sup" data-flow="emd"><span className="n" data-flow-count="emd">0</span><span className="l">EMD</span><span className="o">Supplier pays</span></a>
    <span className="bo-arrow">→</span>
    <a href="#" className="bo-step" data-flow="escrow"><span className="n" data-flow-count="escrow">0</span><span className="l">Escrow</span><span className="o">Escrow agent</span></a>
    <span className="bo-arrow">→</span>
    <a href="#" className="bo-step" data-flow="admin"><span className="n" data-flow-count="admin">0</span><span className="l">Admin</span><span className="o">Tender desk</span></a>
    <span className="bo-arrow">→</span>
    <a href="#" className="bo-step" data-flow="certifier"><span className="n" data-flow-count="certifier">0</span><span className="l">Certifier</span><span className="o">Certifier</span></a>
    <span className="bo-arrow">→</span>
    <a href="#" className="bo-step" data-flow="legal"><span className="n" data-flow-count="legal">0</span><span className="l">Legal</span><span className="o">Legal counsel</span></a>
    <span className="bo-arrow">→</span>
    <a href="#" className="bo-step" data-flow="accounts"><span className="n" data-flow-count="accounts">0</span><span className="l">Accounts</span><span className="o">Accounts</span></a>
    <span className="bo-arrow">→</span>
    <a href="#" className="bo-step done" data-flow="awarded"><span className="n" data-flow-count="awarded">0</span><span className="l">Awarded</span><span className="o">Committee</span></a>
  </section>

  {/* v51ah — filters sit BELOW the step-number tiles (user-requested order) */}
  <div style={{padding: "12px 0 12px 0"}}>{boFilterEl}</div>

  <div className="bo-grid">
    <div style={{minWidth:0}}>
      <div className="bo-bar">
        <div className="pmc-seg" role="tablist" data-testid="bo-tabs">
          <button role="tab" aria-selected="true" data-tab="pmc" data-testid="bo-tab-pmc">Needs PMC <span className="c" data-tab-count="pmc">0</span></button>
          <button role="tab" aria-selected="false" data-tab="supplier" data-testid="bo-tab-supplier">Waiting on supplier <span className="c" data-tab-count="supplier">0</span></button>
          <button role="tab" aria-selected="false" data-tab="awarded" data-testid="bo-tab-awarded">Awarded <span className="c" data-tab-count="awarded">0</span></button>
          <button role="tab" aria-selected="false" data-tab="all" data-testid="bo-tab-all">All <span className="c" data-tab-count="all">0</span></button>
        </div>
        <label className="pmc-search" style={{flex:1,minWidth:"200px",height:"36px"}}><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Bid, notice or vendor" data-testid="bo-search-input" /></label>
        <label className="bo-tog"><input type="checkbox" id="bo-hidetest" data-testid="bo-hidetest" /> Hide test data <span className="pmc-muted">(<span data-bo-test-count>0</span>)</span></label>
      </div>
      <div className="bo-bulk" id="bo-bulk" hidden data-testid="bo-bulk-bar">
        <b id="bo-bulkn">0 selected</b>
        <span className="pmc-muted">·</span>
        <a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm" data-testid="bo-bulk-remind"><svg className="pmc-ico" aria-hidden="true"><use href="#i-mail" /></svg> Send EMD reminders</a>
        <a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm" data-testid="bo-bulk-clear">Clear</a>
      </div>
      <section className="pmc-panel" style={{overflow:"hidden"}}>
        <table className="pmc-table bo-table" data-testid="bo-table">
          <thead><tr><th></th><th>Bid · notice · vendor</th><th className="num">Price · EMD</th><th>Clearance · next step</th><th style={{textAlign:"right"}}>Action</th></tr></thead>
          <tbody id="bo-rows"><tr><td colSpan={5} className="bo-empty" data-testid="bo-loading">Loading bids…</td></tr></tbody>
        </table>
        <div className="bo-empty" id="bo-empty" hidden data-testid="bo-empty">Nothing here. Every bid in this view has moved on.</div>
        <div className="bo-foot"><span className="pmc-muted" id="bo-shown" data-testid="bo-shown"></span><span className="pmc-muted">Sorted by longest waiting first</span></div>
      </section>
      <div className="pmc-callout pmc-callout--warn" style={{marginTop:"12px",display:"none"}} id="bo-anomaly-callout" data-testid="bo-anomaly-callout">
        <svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>
        <div><b><span id="bo-anomaly-count">0</span> prices look off.</b> The AI anomaly check flagged bids whose price is far from the estimate. Confirm with the bidder before clearing EMD.</div>
      </div>
    </div>

    <aside className="bo-side" data-testid="bo-side">
      <section className="pmc-panel" id="detail" data-testid="bo-detail-panel">
        <div className="pmc-panel__head">
          <div><div className="pmc-ref" id="d-ref" data-testid="bo-detail-ref">—</div><h2 className="pmc-panel__title" id="d-t" data-testid="bo-detail-title">Select a bid to see its clearance path</h2></div>
          <span className="pmc-pill" id="d-pill" data-testid="bo-detail-pill">—</span>
        </div>
        <div className="pmc-panel__body" style={{display:"grid",gap:"14px"}}>
          <dl className="pmc-kv" id="d-kv"></dl>
          <div className="bo-tl" id="d-tl"></div>
          <div id="d-docs" style={{display:"grid",gap:"6px"}}></div>
          <div id="d-act" style={{display:"grid",gap:"8px"}}></div>
        </div>
      </section>

      <section className="pmc-panel" data-testid="bo-committee-panel">
        <div className="pmc-panel__head"><h2 className="pmc-panel__title">Active committee</h2><span className="pmc-pill" id="bo-committee-pill">—</span></div>
        <div className="pmc-panel__body" style={{display:"grid",gap:"10px",fontSize:"14px"}} id="bo-committee-body">
          <div className="pmc-muted" style={{fontSize:"13px"}}>No open committee.</div>
          <div style={{display:"flex",gap:"8px"}}>
            <a href="/admin/e/evaluation" className="pmc-btn pmc-btn--secondary pmc-btn--sm" data-testid="bo-committee-form">Form committee</a>
          </div>
        </div>
      </section>
    </aside>
  </div>
</main>
</div>
</div>
      <AssignSpecialistsModal
        bid={specialistFor}
        staffList={staffList}
        onAssign={assignSpecialist}
        onClose={() => setSpecialistFor(null)}
      />
    </div>
  );
}
