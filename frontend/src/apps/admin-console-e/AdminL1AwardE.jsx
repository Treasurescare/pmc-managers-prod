import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function AdminL1AwardE({ legacy: Legacy }) {
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
  return (
    <div data-testid="admin-l1-award-e" data-pmc-e-page="admin-l1-award-e">
<div className="pmc-adm"><aside className="pmc-side" aria-label="Admin"><div className="pmc-side__brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Admin console</span></div><div className="pmc-side__group">Overview</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Dashboard</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>Audit ledger</a><div className="pmc-side__group">Procurement</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Notices<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>29</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg>Tender builder</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Corrigenda</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>BOQ & contracts</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-box" /></svg>Work packages<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>50</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>Catalog</a><div className="pmc-side__group">Market</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Vendors<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>76</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Registrations</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-eye" /></svg>Vendor intel</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg>Engagements</a><div className="pmc-side__group">Money & compliance</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>Bidding ops<span className="pmc-side__count">10</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>Escrow / EMD</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Billing</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Evaluation</a><a href="#" className="pmc-side__item" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chart" /></svg>L1 comparison</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Awards</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>DocuSign</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>Permissions</a><div className="pmc-side__group">Events</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>Events & alerts</a></aside><div>
<header className="pmc-atop"><div className="crumb">Money &amp; compliance / L1 comparison / <b>PMC-NOT-2026-0055</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r"><a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Create</a><button className="pmc-btn pmc-btn--secondary" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button><button className="pmc-ib pmc-bell" aria-label="6 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">6</span></button><button className="pmc-ib" aria-label="AI copilot"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg></button><span className="pmc-avatar" title="adminsupport@pmcmanagers.com · 2FA on">A</span></div>
</header><main className="pmc-amain"><div className="ah"><div><div className="pmc-eyebrow">Money &amp; compliance · L1 comparison</div><h1>Turnkey IVF Laboratory Setup</h1><div className="pmc-muted" style={{ fontSize: "14px", marginTop: "4px" }}>PMC-NOT-2026-0055 · commercial opened 2 Oct 2026, 11:00 · estimate USD 2,100,000</div></div><div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Comparative statement</a><a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg> Recommend award</a></div></div>
<div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 340px", gap: "24px", alignItems: "start" }}>
<div style={{ display: "grid", gap: "16px" }}>
<section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">Ranking · qualified bids only</h2><span className="pmc-muted" style={{ fontSize: "13px" }}>Bidder C failed technical (47) · envelope returned unopened</span></div>
<table className="pmc-table"><thead><tr><th>Rank</th><th>Bidder</th><th className="num">Evaluated price</th><th className="num">vs estimate</th><th className="num">Technical</th><th>AI check</th></tr></thead><tbody><tr><td><span className="ad-rank l1">1</span></td><td style={{ fontWeight: "600" }}>Emerald Corporates</td><td className="num" style={{ fontWeight: "600" }}>USD 2,046,000</td><td className="num" style={{ color: "var(--success)" }}>−2.6%</td><td className="num">89</td><td><span className="pmc-pill pmc-pill--success">No anomaly</span></td></tr><tr><td><span className="ad-rank ">2</span></td><td style={{ fontWeight: "600" }}>Bidder B</td><td className="num" style={{ fontWeight: "600" }}>USD 2,188,500</td><td className="num" style={{ color: "var(--warning)" }}>+4.2%</td><td className="num">82</td><td><span className="pmc-pill pmc-pill--success">No anomaly</span></td></tr></tbody></table></section>
<section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">Price against estimate</h2></div><div className="pmc-panel__body">
<svg viewBox="0 0 720 150" style={{ width: "100%", height: "auto" }} role="img" aria-label="Bids against estimate">
<line x1="40" y1="110" x2="700" y2="110" stroke="var(--line-strong)" />
<line x1="430" y1="20" x2="430" y2="118" stroke="var(--ink-muted)" stroke-dasharray="4 4" /><text x="430" y="14" text-anchor="middle" font-size="12" fill="var(--ink-muted)" font-family="var(--font-sans)">Estimate USD 2,100,000</text>
<circle cx="390" cy="80" r="9" fill="var(--brass)" /><text x="390" y="60" text-anchor="middle" font-size="12" font-weight="600" fill="var(--ink)" font-family="var(--font-sans)">L1 · 2.046M</text>
<circle cx="535" cy="80" r="9" fill="var(--primary)" /><text x="535" y="60" text-anchor="middle" font-size="12" font-weight="600" fill="var(--ink)" font-family="var(--font-sans)">L2 · 2.189M</text>
<text x="40" y="136" font-size="12" fill="var(--ink-muted)" font-family="var(--font-mono)">1.6M</text><text x="700" y="136" text-anchor="end" font-size="12" fill="var(--ink-muted)" font-family="var(--font-mono)">2.6M</text>
</svg></div></section>
</div>
<aside style={{ display: "grid", gap: "16px", position: "sticky", top: "88px" }}>
<div className="pmc-panel" style={{ padding: "18px" }}><b>Award recommendation</b><dl className="pmc-kv" style={{ marginTop: "12px" }}><dt>Recommended</dt><dd>Emerald Corporates</dd><dt>Value</dt><dd>USD 2,046,000</dd><dt>Basis</dt><dd>L1 among qualified</dd><dt>Savings vs estimate</dt><dd style={{ color: "var(--success)" }}>USD 54,000</dd></dl>
<div className="pmc-field" style={{ marginTop: "14px" }}><label>Committee note</label><textarea className="pmc-input" style={{ height: "72px", padding: "10px" }}>L1 is technically strong (89) and within estimate.</textarea></div>
<div style={{ display: "grid", gap: "8px", marginTop: "12px" }}><button className="pmc-btn pmc-btn--primary">Send for committee sign-off</button><button className="pmc-btn pmc-btn--secondary">Request negotiation with L1</button></div></div>
<div className="pmc-panel" style={{ padding: "18px" }}><b>Sign-off</b><div style={{ display: "grid", gap: "8px", marginTop: "10px", fontSize: "14px" }}><div style={{ display: "flex", justifyContent: "space-between" }}>Procurement head<span className="pmc-pill">Pending</span></div><div style={{ display: "flex", justifyContent: "space-between" }}>Medical engineer<span className="pmc-pill">Pending</span></div><div style={{ display: "flex", justifyContent: "space-between" }}>Independent adviser<span className="pmc-pill">Pending</span></div></div></div>
</aside></div></main></div></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · L1 comparison & award</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Only qualified bids appear</b>Failed technical bids are returned unopened.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="admin"><summary>Can we negotiate with L1?</summary><p>Yes, if the tender allows it. Negotiation is recorded and the revised price replaces the original only after committee sign-off.</p></details></div>
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
