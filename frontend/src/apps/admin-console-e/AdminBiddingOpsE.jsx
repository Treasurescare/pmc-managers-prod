import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { useAdminBiddingOpsLive } from "@/lib/pmcELiveData";
import "./bidding-ops.css";

// Sidebar preserved from the existing admin console shell so nav stays
// consistent. Table body + right-side panels are hydrated by
// useAdminBiddingOpsLive from /api/v1/bids.
export default function AdminBiddingOpsE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useAdminBiddingOpsLive({ enabled: isE });

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
      let visible = 0;
      root.querySelectorAll('.bo-r').forEach((r) => {
        const ok = (tab === "all" || r.dataset.g === tab) && !(hide && r.dataset.test === "1");
        r.hidden = !ok;
        if (ok) visible++;
      });
      const empty = root.querySelector('#bo-empty');
      if (empty) empty.hidden = visible > 0;
      const shown = root.querySelector('#bo-shown');
      const total = root.querySelectorAll('.bo-r').length;
      if (shown) shown.textContent = total ? `Showing ${visible} of ${total}` : '';
    };
    const onTab = (e) => {
      const b = e.currentTarget;
      root.querySelectorAll('[data-tab]').forEach((x) => x.setAttribute('aria-selected', x === b ? 'true' : 'false'));
      paint();
    };
    const onHide = () => paint();
    const onRowClick = (e) => {
      if (e.target.closest('.chk') || e.target.closest('.bo-act')) return;
      const r = e.currentTarget;
      root.querySelectorAll('.bo-r').forEach((x) => x.classList.toggle('sel', x === r));
    };
    const onChk = (e) => {
      e.stopPropagation();
      const n = root.querySelectorAll('.chk:checked').length;
      const bulk = root.querySelector('#bo-bulk');
      const bn = root.querySelector('#bo-bulkn');
      if (bulk) bulk.hidden = n === 0;
      if (bn) bn.textContent = `${n} selected`;
    };
    root.querySelectorAll('[data-tab]').forEach((b) => b.addEventListener('click', onTab));
    root.querySelector('#bo-hidetest')?.addEventListener('change', onHide);
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
    return () => { if (mo) mo.disconnect(); };
  }, [isE]);

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="admin-bidding-ops-e" data-pmc-e-page="admin-bidding-ops-e">
<div className="pmc-adm"><aside className="pmc-side" aria-label="Admin"><div className="pmc-side__brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Admin console</span></div><div className="pmc-side__group">Overview</div><a href="/admin/e/dashboard" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Dashboard</a><a href="/admin/e/audit" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>Audit ledger</a><div className="pmc-side__group">Procurement</div><a href="/admin/e/notices" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Notices</a><a href="/admin/e/tender-builder" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg>Tender builder</a><a href="/admin/e/corrigenda" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Corrigenda</a><a href="/admin/e/boq" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>BOQ & contracts</a><a href="/admin/e/work-packages" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-box" /></svg>Work packages</a><a href="/admin/e/catalog" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>Catalog</a><div className="pmc-side__group">Market</div><a href="/admin/e/vendors" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Vendors</a><a href="/admin/e/registrations" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Registrations</a><a href="/admin/e/vendor-intel" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-eye" /></svg>Vendor intel</a><a href="/admin/e/engagements" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg>Engagements</a><div className="pmc-side__group">Money & compliance</div><a href="/admin/e/bidding" className="pmc-side__item" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>Bidding ops<span className="pmc-side__count" data-testid="side-bidding-count">0</span></a><a href="/admin/e/escrow" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>Escrow / EMD</a><a href="/admin/e/billing" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Billing</a><a href="/admin/e/evaluation" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Evaluation</a><a href="/admin/e/l1" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chart" /></svg>L1 comparison</a><a href="/admin/e/awards" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Awards</a><a href="/admin/e/docusign" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>DocuSign</a><a href="/admin/e/permissions" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>Permissions</a><div className="pmc-side__group">Events</div><a href="/admin/e/events" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>Events & alerts</a></aside>
<div>
<header className="pmc-atop">
  <div className="crumb">Money &amp; compliance / <b>Bidding ops</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" data-testid="admin-search-input" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r"><a href="/admin/e/tender-builder" className="pmc-btn pmc-btn--primary" data-testid="bo-create-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Create</a><button className="pmc-btn pmc-btn--secondary" data-help-open="" data-testid="bo-help-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button><button className="pmc-ib pmc-bell" aria-label="Alerts" data-testid="bo-bell-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">0</span></button><span className="pmc-avatar" title="Admin">A</span></div>
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
    </div>
  );
}
