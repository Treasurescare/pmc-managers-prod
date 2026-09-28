import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function AdminDashboardE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useEffect(() => {
    if (!isE) return;
    const tick = () => {
      document.querySelectorAll("[data-in]").forEach((el) => {
        const secs = parseInt(el.getAttribute("data-in") || "0", 10);
        if (!secs) return;
        const d = Math.floor(secs/86400), h = Math.floor((secs%86400)/3600), m = Math.floor((secs%3600)/60);
        el.textContent = d>0 ? `${d}d ${h}h` : h>0 ? `${h}h ${m}m` : `${m}m`;
      });
    };
    tick();
  }, [isE]);
  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;
  return (
    <div data-testid="admin-dashboard-e" data-pmc-e-page="admin-dashboard-e">
<div className="pmc-adm">
<aside className="pmc-side" aria-label="Admin"><div className="pmc-side__brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Admin console</span></div><div className="pmc-side__group">Overview</div><a href="#" className="pmc-side__item" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Dashboard</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>Audit ledger</a><div className="pmc-side__group">Procurement</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Notices<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>29</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg>Tender builder</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Corrigenda</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>BOQ & contracts</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-box" /></svg>Work packages<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>50</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>Catalog</a><div className="pmc-side__group">Market</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Vendors<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>76</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Registrations</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-eye" /></svg>Vendor intel</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg>Engagements</a><div className="pmc-side__group">Money & compliance</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>Bidding ops<span className="pmc-side__count">10</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>Escrow / EMD</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Billing</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Evaluation</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chart" /></svg>L1 comparison</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Awards</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>DocuSign</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>Permissions</a><div className="pmc-side__group">Events</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>Events & alerts</a></aside>
<div>
<header className="pmc-atop">
  <div className="crumb">Overview / <b>Dashboard</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r">
    <a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Create</a>
    <button className="pmc-btn pmc-btn--secondary" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-ib pmc-bell" aria-label="6 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">6</span></button>
    <button className="pmc-ib" aria-label="AI copilot" title="AI copilot"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg></button>
    <span className="pmc-avatar" title="adminsupport@pmcmanagers.com · 2FA on">A</span>
  </div>
</header>
<main className="pmc-amain">
  <div className="pmc-ahead">
    <div><div className="pmc-eyebrow">Monday, 28 September 2026 · Production</div><h1>Good morning. 5 things need you.</h1></div>
    <div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg> New tender from DPR</a><a href="#" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg> Form committee</a></div>
  </div>

      <section>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}><h2 style={{ margin: "0", fontSize: "17px" }}>Tender pipeline</h2><span className="pmc-muted" style={{ fontSize: "13px" }}>Live counts · select a stage to filter</span></div>
        <div className="pmc-pipe"><a href="#" className=""><span className="n">I</span><span className="c">23</span><span className="l">Draft</span><span className="bar"><i style={{ width: "80%" }}></i></span><span className="l2" style={{ fontSize: "12px", minHeight: "16px" }}></span></a><a href="#" className=""><span className="n">II</span><span className="c">29</span><span className="l">Published</span><span className="bar"><i style={{ width: "100%" }}></i></span><span className="l2" style={{ fontSize: "12px", minHeight: "16px" }}></span></a><a href="#" className=""><span className="n">III</span><span className="c">0</span><span className="l">Clarifications</span><span className="bar"><i style={{ width: "0%" }}></i></span><span className="l2" style={{ fontSize: "12px", minHeight: "16px" }}></span></a><a href="#" className="is-hot"><span className="n">IV</span><span className="c">10</span><span className="l">Bidding</span><span className="bar"><i style={{ width: "35%" }}></i></span><span className="l2" style={{ fontSize: "12px", minHeight: "16px" }}>3 close this week</span></a><a href="#" className=""><span className="n">V</span><span className="c">0</span><span className="l">Technical eval</span><span className="bar"><i style={{ width: "0%" }}></i></span><span className="l2" style={{ fontSize: "12px", minHeight: "16px" }}></span></a><a href="#" className=""><span className="n">VI</span><span className="c">11</span><span className="l">Commercial eval</span><span className="bar"><i style={{ width: "38%" }}></i></span><span className="l2" style={{ fontSize: "12px", minHeight: "16px" }}></span></a><a href="#" className=""><span className="n">VII</span><span className="c">3</span><span className="l">Awarded</span><span className="bar"><i style={{ width: "10%" }}></i></span><span className="l2" style={{ fontSize: "12px", minHeight: "16px" }}></span></a></div>
      </section>
      <div className="pmc-kpis">
        <div className="pmc-kpi"><div className="l">EMD collected</div><div className="pmc-figure">$3,063,000</div><div className="s">0 pending</div></div>
        <div className="pmc-kpi"><div className="l">Active contracts</div><div className="pmc-figure">11</div><div className="s">milestones tracked</div></div>
        <div className="pmc-kpi"><div className="l">Bids in pipeline</div><div className="pmc-figure">10</div><div className="s">3 awarded</div></div>
        <div className="pmc-kpi"><div className="l">Approved vendors</div><div className="pmc-figure">76</div><div className="s">1 review pending</div></div>
      </div>
  <div className="pmc-cols">
    <div className="pmc-stack">
      <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">Needs you today</h2><span className="pmc-pill pmc-pill--warning">5 open</span></div><div className="pmc-inbox"><div className="pmc-inrow warn"><span className="pmc-inrow__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg></span><div><b>Approve publication · Dual Medical University & Teaching Hospital Complex</b><span className="s">Draft v2 from the tender builder · submitted by Tender desk · 1 DPR field still empty</span></div><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Review draft</a></div><div className="pmc-inrow "><span className="pmc-inrow__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg></span><div><b>Confirm EMD receipt · PMC-BID-2026-00020</b><span className="s">INR 1,240,000 · Supply & Installation of OPD Queue Management · escrow step 1 of 6</span></div><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Confirm</a></div><div className="pmc-inrow "><span className="pmc-inrow__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg></span><div><b>Legal KYC clearance · PMC-BID-2026-00003</b><span className="s">Certifier cleared · waiting for legal counsel · step 4 of 6</span></div><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Open bid</a></div><div className="pmc-inrow "><span className="pmc-inrow__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg></span><div><b>1 supplier review awaiting moderation</b><span className="s">Peer review on PMC-SUP-000022</span></div><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Moderate</a></div><div className="pmc-inrow bad"><span className="pmc-inrow__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg></span><div><b>12 test notices are visible on the public board</b><span className="s">Titles such as “test_21” and “8000 apples” reduce buyer and supplier trust</span></div><a href="#" className="pmc-btn pmc-btn--danger pmc-btn--sm">Hide from public</a></div></div></section>
      <section className="pmc-panel">
        <div className="pmc-panel__head"><h2 className="pmc-panel__title">Bids waiting on a step</h2><a href="#">Open bidding ops</a></div>
        <table className="pmc-table"><thead><tr><th>Bid · vendor</th><th className="num">Price</th><th>Status</th><th>Next step</th><th></th></tr></thead><tbody><tr><td><div style={{ fontWeight: "600" }}>OPD Queue Management & Digital Signage</div><div style={{ fontSize: "12px", color: "var(--ink-muted)" }}><span className="pmc-ref">PMC-BID-2026-00020</span> · Emerald Corporates</div></td><td className="num" style={{ fontWeight: "600" }}>INR 58,900,000</td><td><span className="pmc-pill pmc-pill--info">EMD paid</span></td><td className="pmc-next-owner">Escrow · confirm receipt</td><td style={{ textAlign: "right", width: "40px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></td></tr><tr><td><div style={{ fontWeight: "600" }}>Turnkey IVF Laboratory Setup</div><div style={{ fontSize: "12px", color: "var(--ink-muted)" }}><span className="pmc-ref">PMC-BID-2026-00017</span> · Emerald Corporates</div></td><td className="num" style={{ fontWeight: "600" }}>USD 2,046,000</td><td><span className="pmc-pill pmc-pill--warning">Awaiting EMD</span></td><td className="pmc-next-owner">Supplier · pay EMD</td><td style={{ textAlign: "right", width: "40px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></td></tr><tr><td><div style={{ fontWeight: "600" }}>Supply of 400 Laptops</div><div style={{ fontSize: "12px", color: "var(--ink-muted)" }}><span className="pmc-ref">PMC-BID-2026-00021</span> · Rash ME</div></td><td className="num" style={{ fontWeight: "600" }}>USD 78,000.91</td><td><span className="pmc-pill pmc-pill--warning">Awaiting EMD</span></td><td className="pmc-next-owner">Supplier · pay EMD</td><td style={{ textAlign: "right", width: "40px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></td></tr><tr><td><div style={{ fontWeight: "600" }}>Modular Operation Theatres (OTs)</div><div style={{ fontSize: "12px", color: "var(--ink-muted)" }}><span className="pmc-ref">PMC-BID-2026-00003</span> · Supplier C (sample)</div></td><td className="num" style={{ fontWeight: "600" }}>USD 950,000</td><td><span className="pmc-pill pmc-pill--info">Certifier cleared</span></td><td className="pmc-next-owner">Legal · KYC clearance</td><td style={{ textAlign: "right", width: "40px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></td></tr><tr><td><div style={{ fontWeight: "600" }}>Birth Suites — Consumables & Kits</div><div style={{ fontSize: "12px", color: "var(--ink-muted)" }}><span className="pmc-ref">PMC-BID-2026-00016</span> · Supplier D (sample)</div></td><td className="num" style={{ fontWeight: "600" }}>KZT 5,000,000</td><td><span className="pmc-pill pmc-pill--info">EMD paid</span></td><td className="pmc-next-owner">Escrow · confirm receipt</td><td style={{ textAlign: "right", width: "40px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></td></tr></tbody></table>
      </section>
    </div>
    <div className="pmc-stack">
      <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">AI bid anomaly check</h2><span className="pmc-pill pmc-pill--success">0 flagged</span></div>
        <div className="pmc-panel__body" style={{ display: "grid", gap: "12px" }}><select className="pmc-input" aria-label="Bid"><option>All 10 bids in pipeline</option></select><button className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg> Run check</button><div className="pmc-muted" style={{ fontSize: "13px" }}>Checks price outliers against the estimate and other bids. Last run today 09:12, no anomalies.</div></div></section>
      <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">Audit ledger</h2><span className="pmc-pill pmc-pill--success">Chain intact</span></div>
        <div className="pmc-panel__body" style={{ paddingTop: "6px" }}><div className="pmc-led">
          <div><span className="pmc-ref">#1905</span><span>staff.login · adminsupport</span><span className="pmc-muted">01:41</span></div>
          <div><span className="pmc-ref">#1904</span><span>staff.login · adminsupport</span><span className="pmc-muted">01:31</span></div>
          <div><span className="pmc-ref">#1903</span><span>vendor.login · 64943c36</span><span className="pmc-muted">01:29</span></div>
          <div><span className="pmc-ref">#1901</span><span>contract.create · 026-0015</span><span className="pmc-muted">Sun</span></div>
        </div><button className="pmc-btn pmc-btn--secondary" style={{ width: "100%", marginTop: "12px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg> Verify whole chain</button></div></section>
      <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">System readiness</h2></div>
        <div className="pmc-panel__body" style={{ display: "grid", gap: "12px", fontSize: "14px" }}>
          <div style={{ display: "flex", justifyContent: "space-between" }}><span>Two-factor sign-in</span><span className="pmc-pill pmc-pill--success">On</span></div>
          <div style={{ display: "flex", justifyContent: "space-between" }}><span>DocuSign</span><span className="pmc-pill pmc-pill--warning">Sandbox</span></div>
          <div style={{ display: "flex", justifyContent: "space-between" }}><span>Public board</span><span className="pmc-pill pmc-pill--danger">12 test notices</span></div>
          <div className="pmc-muted" style={{ fontSize: "13px" }}>Switch DocuSign to production and hide test data before launch.</div>
        </div></section>
    </div>
  </div>
</main>
</div>
</div>

<div className="pmc-drawer-scrim" data-help-close=""></div>
<aside className="pmc-drawer" role="dialog" aria-modal="true" aria-label="Help and FAQs">
  <div className="pmc-drawer__head">
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
      <div><div className="pmc-eyebrow">Help &amp; FAQs</div><div style={{ fontSize: "20px", lineHeight: "28px", fontWeight: "600" }}>How can we help?</div></div>
      <button className="pmc-btn pmc-btn--ghost pmc-btn--sm" data-help-close="" aria-label="Close help">Close <span className="pmc-kbd">Esc</span></button>
    </div>
    <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input data-help-q="" placeholder="Search help, e.g. “bank guarantee”" /></label>
  </div>
  <div className="pmc-drawer__body">
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Admin dashboard</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Work the inbox top-down</b>“Needs you today” lists only items waiting on your role, oldest first.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Pipeline stages are filters</b>Select a stage to open the notices or bids in it.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Ctrl K finds anything</b>Tender, bid or vendor reference, or a ledger event number.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="admin"><summary>How do I publish a tender from a DPR?</summary><p>Open <b>Tender builder</b>, choose <b>AI generate from DPR</b> and upload the document. Check any fields the AI could not extract, save, then send for approval.</p></details><details className="pmc-faq" data-cat="admin"><summary>How do I issue a corrigendum?</summary><p>Open the notice, choose <b>Issue corrigendum</b>, set the effective date and describe the change. Every bidder and follower is alerted.</p></details><details className="pmc-faq" data-cat="admin"><summary>How do I form an evaluation committee?</summary><p>From <b>Bidding ops</b>, choose <b>Form committee</b>, add internal members, invite external evaluators and set the quorum.</p></details><details className="pmc-faq" data-cat="admin"><summary>How do I verify the audit ledger?</summary><p>Open <b>Audit ledger</b> and choose <b>Verify chain</b>. The check re-computes every SHA-256 link and reports the first break, if any.</p></details></div>
    <p data-help-empty="" hidden style={{ color: "var(--ink-muted)", fontSize: "14px" }}>No answer matches yet. Raise a ticket below and the PMC desk will reply.</p>
    <a href="#" className="pmc-btn pmc-btn--secondary" style={{ width: "100%", marginTop: "16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Open the full Help Centre</a>
  </div>
  <div className="pmc-drawer__foot">
    <a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a>
    <a href="mailto:tenders@pmcmanagers.com" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-mail" /></svg> Email the desk</a>
  </div>
</aside>
<button className="pmc-helpfab" data-help-open="" aria-label="Open help"><span className="pmc-helpfab__q">?</span>Help</button>
    </div>
  );
}
