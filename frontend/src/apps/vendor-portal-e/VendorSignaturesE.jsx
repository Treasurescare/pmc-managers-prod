import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { useVendorSignaturesLive } from "@/lib/pmcELiveData";

export default function VendorSignaturesE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useVendorSignaturesLive({ enabled: isE });
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
    <div data-testid="vendor-signatures-e" data-pmc-e-page="vendor-signatures-e">
<header className="pmc-chrome pmc-vtop">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Supplier portal</span></a>
  <label className="pmc-search pmc-cmd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, documents…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-vtop__r">
    <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-iconbtn pmc-bell" aria-label="9 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">9</span></button>
    <button className="pmc-who" aria-haspopup="menu"><span className="pmc-avatar">EC</span><span className="pmc-who__t"><b>Emerald Corporates</b><span>PMC-SUP-000017 · KYC verified</span></span></button>
  </div>
</header><div className="pmc-app"><nav className="pmc-lnav" aria-label="Supplier"><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Find tenders<span className="c">29</span></a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>My bids<span className="c hot">1</span></a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>EMD &amp; payments</a><a href="#" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>Signatures<span className="c">1</span></a><hr /><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Company &amp; KYC</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Reviews</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg>Account &amp; security</a><a href="#" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs</a><div className="pmc-desk"><b>Your PMC desk</b><div className="pmc-muted">Questions on a tender or bid?</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm" style={{ width: "100%", marginTop: "10px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a></div></nav><main className="pmc-main"><div className="sp-head"><div><div className="pmc-eyebrow">Signatures</div><h1>Documents to sign</h1></div></div>
<div className="pmc-next" style={{ gridTemplateColumns: "auto 1fr auto" }}><div className="pmc-next__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg></div><div><div className="pmc-eyebrow">Needs your signature</div><h2>Letter of award · OPD Building Renovation — Block C</h2><div className="pmc-muted" style={{ fontSize: "14px" }}>KZT 812,000,000 · 12 pages · signing with DocuSign inside the portal takes about 2 minutes.</div></div><div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--secondary">Preview</a><a href="#" className="pmc-btn pmc-btn--primary">Review &amp; sign</a></div></div>
<section className="pmc-panel"><table className="pmc-table"><thead><tr><th>Document</th><th>Status</th><th>Detail</th><th></th></tr></thead><tbody><tr><td><div style={{ fontWeight: "600" }}>Letter of award · OPD Building Renovation — Block C</div><span className="pmc-ref">PMC-AWD-2026-00027</span></td><td><span className="pmc-pill pmc-pill--warning">Awaiting your signature</span></td><td className="pmc-muted" style={{ fontSize: "13px" }}>Sent 21 Sep · expires in 9 days</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Review &amp; sign</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Contract · OPD Building Renovation — Block C</div><span className="pmc-ref">PMC-AWD-2026-00027</span></td><td><span className="pmc-pill pmc-pill--info">Waiting for PMC</span></td><td className="pmc-muted" style={{ fontSize: "13px" }}>After your LOA signature</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">View</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Purchase order · Medical gas pipeline systems</div><span className="pmc-ref">PMC-AWD-2026-00019</span></td><td><span className="pmc-pill pmc-pill--success">Completed</span></td><td className="pmc-muted" style={{ fontSize: "13px" }}>Signed 19 Sep · both parties</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Download</a></td></tr></tbody></table></section>
<section className="pmc-panel" style={{ marginTop: "16px", display: "grid", gridTemplateColumns: "1.3fr .7fr", overflow: "hidden" }}>
  <div style={{ padding: "20px 24px", borderRight: "1px solid var(--line)" }}>
    <b style={{ fontSize: "15px" }}>Signing preview</b>
    <div style={{ marginTop: "14px", background: "var(--surface-sunken)", border: "1px solid var(--line)", borderRadius: "var(--radius-md)", height: "320px", display: "grid", placeItems: "center" }}>
      <div style={{ width: "60%", height: "280px", background: "var(--surface)", boxShadow: "var(--shadow-pop)", padding: "22px", display: "grid", gap: "9px", alignContent: "start", position: "relative" }}>
        <i style={{ display: "block", height: "10px", width: "45%", background: "var(--line-strong)", borderRadius: "3px" }}></i><i style={{ display: "block", height: "6px", background: "var(--line)", borderRadius: "3px" }}></i><i style={{ display: "block", height: "6px", background: "var(--line)", borderRadius: "3px" }}></i><i style={{ display: "block", height: "6px", background: "var(--line)", borderRadius: "3px" }}></i><i style={{ display: "block", height: "6px", background: "var(--line)", borderRadius: "3px" }}></i><i style={{ display: "block", height: "6px", background: "var(--line)", borderRadius: "3px" }}></i><i style={{ display: "block", height: "6px", background: "var(--line)", borderRadius: "3px" }}></i><i style={{ display: "block", height: "6px", background: "var(--line)", borderRadius: "3px" }}></i><i style={{ display: "block", height: "6px", background: "var(--line)", borderRadius: "3px" }}></i><i style={{ display: "block", height: "6px", background: "var(--line)", borderRadius: "3px" }}></i>
        <div style={{ position: "absolute", left: "22px", right: "22px", bottom: "24px", display: "flex", justifyContent: "space-between", alignItems: "end" }}><div style={{ border: "2px dashed var(--brass)", borderRadius: "var(--radius-sm)", padding: "8px 14px", fontSize: "12px", fontWeight: "700", color: "var(--brass-text)", background: "var(--warning-soft)" }}>SIGN HERE</div><div style={{ border: "2px dashed var(--line-strong)", borderRadius: "var(--radius-sm)", padding: "8px 14px", fontSize: "12px", color: "var(--ink-muted)" }}>Date</div></div>
      </div></div></div>
  <div style={{ padding: "20px 24px", display: "grid", gap: "12px", alignContent: "start" }}><b style={{ fontSize: "15px" }}>Who signs</b>
    <div className="ad-member" style={{ display: "flex", gap: "10px", alignItems: "center", fontSize: "14px" }}><span className="pmc-avatar" style={{ width: "28px", height: "28px", fontSize: "11px" }}>RK</span><div style={{ flex: "1" }}>Rk<div className="pmc-muted" style={{ fontSize: "12px" }}>Signatory · Emerald Corporates</div></div><span className="pmc-pill pmc-pill--warning">You</span></div>
    <div className="ad-member" style={{ display: "flex", gap: "10px", alignItems: "center", fontSize: "14px" }}><span className="pmc-avatar" style={{ width: "28px", height: "28px", fontSize: "11px" }}>PH</span><div style={{ flex: "1" }}>Procurement head<div className="pmc-muted" style={{ fontSize: "12px" }}>PMC Managers</div></div><span className="pmc-pill">Next</span></div>
    <div className="pmc-muted" style={{ fontSize: "12px", lineHeight: "18px" }}>Prefer email? <a href="#">Send me the DocuSign link instead.</a> The signed PDF and certificate of completion appear here and on the ledger.</div></div>
</section></main></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Signatures</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Sign in the portal</b>Embedded DocuSign: no separate account needed.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Order matters</b>You sign first; PMC countersigns and the contract activates.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="awards"><summary>How are contracts signed?</summary><p>Awards, purchase orders and contracts are signed with DocuSign, either inside the portal or through a DocuSign email link. Signed copies appear under <b>Signatures</b>.</p></details></div>
    <p data-help-empty="" hidden style={{ color: "var(--ink-muted)", fontSize: "14px" }}>No answer matches yet. Raise a ticket below and the PMC desk will reply.</p>
    <a href="/help" className="pmc-btn pmc-btn--secondary" style={{ width: "100%", marginTop: "16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Open the full Help Centre</a>
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
