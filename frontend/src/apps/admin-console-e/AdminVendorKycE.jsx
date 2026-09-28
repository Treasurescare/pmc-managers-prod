import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function AdminVendorKycE({ legacy: Legacy }) {
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
    <div data-testid="admin-vendor-kyc-e" data-pmc-e-page="admin-vendor-kyc-e">
<div className="pmc-adm"><aside className="pmc-side" aria-label="Admin"><div className="pmc-side__brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Admin console</span></div><div className="pmc-side__group">Overview</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Dashboard</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>Audit ledger</a><div className="pmc-side__group">Procurement</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Notices<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>29</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg>Tender builder</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Corrigenda</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>BOQ & contracts</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-box" /></svg>Work packages<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>50</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>Catalog</a><div className="pmc-side__group">Market</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Vendors<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>76</span></a><a href="#" className="pmc-side__item" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Registrations</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-eye" /></svg>Vendor intel</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg>Engagements</a><div className="pmc-side__group">Money & compliance</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>Bidding ops<span className="pmc-side__count">10</span></a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>Escrow / EMD</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Billing</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Evaluation</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chart" /></svg>L1 comparison</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Awards</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>DocuSign</a><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>Permissions</a><div className="pmc-side__group">Events</div><a href="#" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>Events & alerts</a></aside><div>
<header className="pmc-atop"><div className="crumb">Market / Registrations / <b>PMC-SUP-000031</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r"><a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Create</a><button className="pmc-btn pmc-btn--secondary" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button><button className="pmc-ib pmc-bell" aria-label="6 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">6</span></button><button className="pmc-ib" aria-label="AI copilot"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg></button><span className="pmc-avatar" title="adminsupport@pmcmanagers.com · 2FA on">A</span></div>
</header><main className="pmc-amain">
<div className="pmc-crumb"><a href="#">Vendors</a>/<a href="#">Registrations</a>/<span>PMC-SUP-000031</span></div>
<div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", margin: "8px 0 20px" }}>
  <div><div style={{ display: "flex", gap: "8px", marginBottom: "8px" }}><span className="pmc-pill pmc-pill--warning">KYC in review</span><span className="pmc-pill pmc-pill--warning">WL · watch-list</span></div><h1 className="pmc-display" style={{ fontSize: "36px", lineHeight: "42px", margin: "0" }}>Sample Supplier LLP</h1><div className="pmc-muted" style={{ fontSize: "14px", marginTop: "4px" }}>PMC-SUP-000031 · Kazakhstan · Civil &amp; MEP · submitted 26 Sep 2026</div></div>
  <div style={{ display: "flex", gap: "8px" }}><button className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Message supplier</button><button className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-eye" /></svg> Vendor intel</button></div></div>
<div style={{ display: "grid", gridTemplateColumns: "340px minmax(0,1fr) 280px", gap: "24px", alignItems: "start" }}>
  <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">Documents</h2><span className="pmc-muted" style={{ fontSize: "13px" }}>3 of 6 approved</span></div><div><a href="#" className="vr-doc"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg></span><div><b>Certificate of incorporation</b><span>Matches company name and number</span></div><span className="pmc-pill pmc-pill--success">Approved</span></a><a href="#" className="vr-doc"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg></span><div><b>Tax registration</b><span>Valid · checked 11 Aug</span></div><span className="pmc-pill pmc-pill--success">Approved</span></a><a href="#" className="vr-doc"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg></span><div><b>ISO 9001 certificate</b><span>Expires 14 Mar 2028</span></div><span className="pmc-pill pmc-pill--success">Approved</span></a><a href="#" className="vr-doc on"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg></span><div><b>Licence — Electrical installation (KZ)</b><span>KZ-EL-2025-04418 · expires 12 Aug 2027</span></div><span className="pmc-pill pmc-pill--info">Reviewing</span></a><a href="#" className="vr-doc"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg></span><div><b>Licence — Mechanical works (KZ)</b><span>Expires 21 Oct 2026</span></div><span className="pmc-pill">To review</span></a><a href="#" className="vr-doc"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg></span><div><b>Bank reference letter</b><span>Optional</span></div><span className="pmc-pill">To review</span></a></div></section>
  <section className="pmc-panel">
    <div className="pmc-panel__head"><div><b>Licence — Electrical installation (KZ)</b><div className="pmc-muted" style={{ fontSize: "12px" }}>licence-electrical.pdf · 2 pages · uploaded 26 Sep</div></div><div style={{ display: "flex", gap: "6px" }}><button className="pmc-btn pmc-btn--ghost pmc-btn--sm">Open full size</button></div></div>
    <div className="pmc-panel__body" style={{ display: "grid", gridTemplateColumns: "1fr 240px", gap: "20px" }}>
      <div className="ad-preview"><div className="ad-page"><i style={{ width: "40%", height: "10px", background: "var(--line-strong)" }}></i><i></i><i style={{ width: "80%" }}></i><i style={{ width: "90%" }}></i><i style={{ width: "60%" }}></i><i style={{ marginTop: "14px" }}></i><i style={{ width: "70%" }}></i><i style={{ width: "85%" }}></i><i style={{ width: "50%" }}></i></div></div>
      <div style={{ display: "grid", gap: "14px", alignContent: "start" }}>
        <div className="pmc-eyebrow" style={{ color: "var(--ink-muted)" }}>Check against form</div>
        <dl className="pmc-kv" style={{ gridTemplateColumns: "1fr auto" }}><dt>Holder name</dt><dd><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg> Match</dd><dt>Licence number</dt><dd><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg> Match</dd><dt>Category</dt><dd><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg> Electrical</dd><dt>Expiry</dt><dd>12 Aug 2027</dd></dl>
        <div className="pmc-field"><label>Reviewer note</label><textarea className="pmc-input" style={{ height: "80px", padding: "10px" }}>Verified against issuing authority register.</textarea></div>
        <div style={{ display: "grid", gap: "8px" }}><button className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg> Approve document</button><button className="pmc-btn pmc-btn--secondary">Request re-upload</button></div>
      </div>
    </div>
  </section>
  <aside style={{ display: "grid", gap: "16px", position: "sticky", top: "88px" }}>
    <div className="pmc-panel" style={{ padding: "18px" }}><b style={{ fontSize: "15px" }}>Why watch-list?</b><p className="pmc-muted" style={{ fontSize: "13px", lineHeight: "20px", margin: "8px 0 0" }}>Flagged by Vendor intel: a director is shared with PMC-SUP-000007 (blacklisted). Confirm ownership before approval.</p><a href="#" style={{ fontSize: "13px" }}>See linked records</a></div>
    <div className="pmc-panel" style={{ padding: "18px" }}><b style={{ fontSize: "15px" }}>Decision</b><div style={{ display: "grid", gap: "8px", marginTop: "12px" }}><button className="pmc-btn pmc-btn--primary" aria-disabled="true">Approve KYC</button><button className="pmc-btn pmc-btn--secondary">Request changes</button><button className="pmc-btn pmc-btn--danger">Reject…</button></div><div className="pmc-muted" style={{ fontSize: "12px", marginTop: "8px" }}>Approve is available once all required documents are approved. Every decision needs a reason and is written to the ledger.</div></div>
    <div className="pmc-panel" style={{ padding: "18px" }}><b style={{ fontSize: "15px" }}>Activity</b><div className="pmc-timeline" style={{ marginTop: "12px" }}><div className="done"><span className="dot"></span><div><b>Registration submitted</b><span>26 Sep · registration.submit #1874</span></div></div><div className="done"><span className="dot"></span><div><b>3 documents approved</b><span>27 Sep · compliance desk</span></div></div><div className="now"><span className="dot"></span><div><b>In review</b><span>Now · you</span></div></div></div></div>
  </aside>
</div></main></div></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Vendor KYC review</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>One document at a time</b>Approve or request a re-upload per document; the supplier sees exactly what to fix.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Watch-list is a prompt, not a verdict</b>Check the linked records, then decide with a reason.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="admin"><summary>What do BL and WL mean?</summary><p>BL is blacklisted (cannot bid). WL is watch-list: allowed, with elevated scrutiny.</p></details><details className="pmc-faq" data-cat="admin"><summary>Can a supplier bid while KYC is in review?</summary><p>No. Bidding opens when KYC is approved; the supplier can prepare drafts meanwhile.</p></details></div>
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
