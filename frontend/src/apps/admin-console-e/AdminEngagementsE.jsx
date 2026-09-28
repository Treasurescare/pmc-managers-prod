import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function AdminEngagementsE({ legacy: Legacy }) {
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
    <div data-testid="admin-engagements-e" data-pmc-e-page="admin-engagements-e">
<div className="pmc-adm"><aside className="pmc-side" aria-label="Admin"><div className="pmc-side__brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Admin console</span></div><div className="pmc-side__group">Overview</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Dashboard</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>Audit ledger</a><div className="pmc-side__group">Procurement</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Notices<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>29</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg>Tender builder</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Corrigenda</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>BOQ & contracts</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-box" /></svg>Work packages<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>50</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>Catalog</a><div className="pmc-side__group">Market</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Vendors<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>76</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Registrations</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-eye" /></svg>Vendor intel</a><a href="#" className="pmc-side__item" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg>Engagements</a><div className="pmc-side__group">Money & compliance</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>Bidding ops<span className="pmc-side__count">10</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>Escrow / EMD</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Billing</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Evaluation</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chart" /></svg>L1 comparison</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Awards</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>DocuSign</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>Permissions</a><div className="pmc-side__group">Events</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>Events & alerts</a></aside><div>
<header className="pmc-atop"><div className="crumb">Market / <b>Engagements</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r"><a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Create</a><button className="pmc-btn pmc-btn--secondary" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button><button className="pmc-ib pmc-bell" aria-label="6 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">6</span></button><button className="pmc-ib" aria-label="AI copilot"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg></button><span className="pmc-avatar" title="adminsupport@pmcmanagers.com · 2FA on">A</span></div>
</header><main className="pmc-amain"><div className="ah"><div><div className="pmc-eyebrow">Market</div><h1>Engagements</h1><div className="pmc-muted" style={{ fontSize: "14px", marginTop: "4px" }}>Pre-bid meetings, site visits and supplier days</div></div><div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> New engagement</a></div></div><section className="pmc-panel"><table className="pmc-table"><thead><tr><th>Engagement</th><th>Where &amp; when</th><th>Attendance</th><th>Status</th><th></th></tr></thead><tbody><tr><td><div style={{ fontWeight: "600" }}>Pre-bid meeting · Turnkey IVF Laboratory</div><div className="pmc-muted" style={{ fontSize: "12px" }}><span className="pmc-ref">ENG-0041</span></div></td><td>Online · 23 Sep</td><td>14 suppliers attended</td><td><span className="pmc-pill pmc-pill--success">Minutes published</span></td><td><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Open</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Site visit · OPD Block C</div><div className="pmc-muted" style={{ fontSize: "12px" }}><span className="pmc-ref">ENG-0042</span></div></td><td>Almaty · 3 Oct</td><td>8 registered</td><td><span className="pmc-pill pmc-pill--info">Upcoming</span></td><td><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Open</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Supplier day · Kazakhstan programme</div><div className="pmc-muted" style={{ fontSize: "12px" }}><span className="pmc-ref">ENG-0043</span></div></td><td>Astana · 20 Oct</td><td>42 registered</td><td><span className="pmc-pill pmc-pill--brand">Registration open</span></td><td><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Open</a></td></tr></tbody></table></section></main></div></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Engagements</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Minutes go to every bidder</b>Publishing minutes sends them to all bidders, attended or not.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="admin"><summary>Are pre-bid answers binding?</summary><p>Only when issued as a clarification or corrigendum on the notice.</p></details></div>
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
