import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { useVendorCompanyLive } from "@/lib/pmcELiveData";

export default function VendorCompanyKycE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useVendorCompanyLive({ enabled: isE });
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
    <div data-testid="vendor-company-kyc-e" data-pmc-e-page="vendor-company-kyc-e">
<header className="pmc-chrome pmc-vtop">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Supplier portal</span></a>
  <label className="pmc-search pmc-cmd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, documents…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-vtop__r">
    <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-iconbtn pmc-bell" aria-label="9 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">9</span></button>
    <button className="pmc-who" aria-haspopup="menu"><span className="pmc-avatar">EC</span><span className="pmc-who__t"><b>Emerald Corporates</b><span>PMC-SUP-000017 · KYC verified</span></span></button>
  </div>
</header><div className="pmc-app"><nav className="pmc-lnav" aria-label="Supplier"><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Find tenders<span className="c">29</span></a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>My bids<span className="c hot">1</span></a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>EMD &amp; payments</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>Signatures<span className="c">1</span></a><hr /><a href="#" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Company &amp; KYC</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Reviews</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg>Account &amp; security</a><a href="#" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs</a><div className="pmc-desk"><b>Your PMC desk</b><div className="pmc-muted">Questions on a tender or bid?</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm" style={{ width: "100%", marginTop: "10px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a></div></nav><main className="pmc-main">
<div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", marginBottom: "20px" }}><div><div className="pmc-eyebrow">Company &amp; KYC</div><h1 className="pmc-display" style={{ fontSize: "40px", lineHeight: "44px", margin: "6px 0 0" }}>Emerald Corporates</h1></div><a href="#" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Download KYC pack</a></div>
<div className="ck-head pmc-panel">
  <div><span className="l">KYC status</span><span className="pmc-pill pmc-pill--success">Verified</span><span className="s">Approved 12 Aug 2026 · review due Aug 2027</span></div>
  <div><span className="l">Supplier ID</span><b className="pmc-ref" style={{ color: "var(--ink)", fontSize: "14px" }}>PMC-SUP-000017</b><span className="s">Registered UK · Company no. on file</span></div>
  <div><span className="l">Rating</span><b style={{ fontSize: "18px" }}>Good · 80</b><span className="s">From 2 buyer reviews</span></div>
  <div><span className="l">Categories</span><b style={{ fontSize: "14px" }}>Civil &amp; MEP · Medical supply</b><span className="s">Delivery: Kazakhstan, India</span></div>
</div>
<div className="pmc-callout pmc-callout--warn" style={{ margin: "16px 0" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg><div><b>1 licence expires soon and 1 is missing.</b> Tenders that need them will show “KYC gap” until you update. <a href="#">Fix now</a></div></div>
<div className="pmc-tabs" style={{ marginBottom: "16px" }}><button className="pmc-tab" aria-selected="true">Licences &amp; certificates</button><button className="pmc-tab">Company documents<span className="n">6</span></button><button className="pmc-tab">Team &amp; roles<span className="n">4</span></button><button className="pmc-tab">Bank accounts<span className="n">1</span></button><button className="pmc-tab">Reviews<span className="n">2</span></button></div>
<section className="pmc-panel"><table className="pmc-table"><thead><tr><th>Licence</th><th>Country</th><th>Number</th><th>Expires</th><th>Status</th><th></th></tr></thead><tbody><tr><td style={{ fontWeight: "600" }}>Electrical installation</td><td>KZ</td><td className="pmc-ref">KZ-EL-2025-04418</td><td>12 Aug 2027</td><td><span className="pmc-pill pmc-pill--success">Valid</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">View</a></td></tr><tr><td style={{ fontWeight: "600" }}>Mechanical works</td><td>KZ</td><td className="pmc-ref">KZ-MW-2024-19002</td><td>21 Oct 2026</td><td><span className="pmc-pill pmc-pill--warning">Expires in 23 days</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Upload renewal</a></td></tr><tr><td style={{ fontWeight: "600" }}>Plumbing &amp; firefighting</td><td>KZ</td><td className="pmc-ref">Not on file</td><td>—</td><td><span className="pmc-pill pmc-pill--danger">Missing</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Add licence</a></td></tr><tr><td style={{ fontWeight: "600" }}>ISO 9001:2015</td><td>Global</td><td className="pmc-ref">QMS-88213</td><td>14 Mar 2028</td><td><span className="pmc-pill pmc-pill--success">Valid</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">View</a></td></tr><tr><td style={{ fontWeight: "600" }}>Medical devices distribution</td><td>IN</td><td className="pmc-ref">MD-DL-2023-7711</td><td>30 Jun 2027</td><td><span className="pmc-pill pmc-pill--success">Valid</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">View</a></td></tr></tbody></table></section>
<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginTop: "16px" }}>
  <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">Team &amp; roles</h2><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Invite</a></div>
    <table className="pmc-table"><tbody><tr><td><b>Rk</b></td><td>Owner · Signatory</td><td><span className="pmc-pill pmc-pill--success">2FA on</span></td></tr><tr><td><b>Tender manager</b></td><td>Editor</td><td><span className="pmc-pill pmc-pill--success">2FA on</span></td></tr><tr><td><b>Finance</b></td><td>EMD &amp; payments</td><td><span className="pmc-pill pmc-pill--warning">2FA off</span></td></tr><tr><td><b>Engineer</b></td><td>Technical envelope only</td><td><span className="pmc-pill pmc-pill--success">2FA on</span></td></tr></tbody></table></section>
  <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">Privacy &amp; data</h2></div><div className="pmc-panel__body" style={{ display: "grid", gap: "12px", fontSize: "14px" }}>
    <p className="pmc-muted" style={{ margin: "0", lineHeight: "22px" }}>Your documents are visible only to PMC compliance and the evaluation committees of tenders you bid on. Every view is logged on the ledger.</p>
    <div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Export my data</a><a href="#" className="pmc-btn pmc-btn--danger">Delete my data…</a></div>
    <span className="pmc-muted" style={{ fontSize: "12px" }}>Deletion asks you to confirm and cannot remove records that must be kept for active bids or contracts.</span></div></section>
</div></main></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Company & KYC</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Keep licences current</b>Expiring licences block matching on tenders that need them. Upload renewals here.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Give people only what they need</b>An engineer can edit the technical envelope without seeing prices.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="registration"><summary>How do I register as a supplier?</summary><p>Choose <b>Register as supplier</b>, enter your company details, then upload the KYC documents the form lists for your country and category. You can save and resume at any point. PMC reviews the file and you are notified when your KYC is approved.</p></details><details className="pmc-faq" data-cat="registration"><summary>Which documents does KYC need?</summary><p>The document list depends on your country and the licences your work category requires (for example, electrical or plumbing licences for Kazakhstan works packages). The registration form shows exactly which slots apply to you.</p></details><details className="pmc-faq" data-cat="account"><summary>How do I keep my account secure?</summary><p>Turn on two-factor sign-in under <b>Account &rsaquo; Security</b>. On the mobile app you can also sign in with Face ID or fingerprint.</p></details></div>
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
