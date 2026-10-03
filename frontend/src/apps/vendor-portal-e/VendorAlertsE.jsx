import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { useVendorAlertsLive } from "@/lib/pmcELiveData";

export default function VendorAlertsE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useVendorAlertsLive({ enabled: isE });
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
    <div data-testid="vendor-alerts-e" data-pmc-e-page="vendor-alerts-e">
<header className="pmc-chrome pmc-vtop">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Supplier portal</span></a>
  <label className="pmc-search pmc-cmd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, documents…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-vtop__r">
    <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-iconbtn pmc-bell" aria-label="9 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">9</span></button>
    <button className="pmc-who" aria-haspopup="menu"><span className="pmc-avatar">EC</span><span className="pmc-who__t"><b>Emerald Corporates</b><span>PMC-SUP-000017 · KYC verified</span></span></button>
  </div>
</header><div className="pmc-app"><nav className="pmc-lnav" aria-label="Supplier"><a href="/vendor" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a><a href="/vendor/tenders"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Find tenders</a><a href="/vendor/mybids"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>My bids</a><a href="/vendor/emd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>EMD &amp; payments</a><a href="/vendor/signatures"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>Signatures</a><hr /><a href="/vendor/company"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Company &amp; KYC</a><a href="/vendor/reviews"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Reviews</a><a href="/vendor/account"><svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg>Account &amp; security</a><a href="#" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs</a><div className="pmc-desk"><b>Your PMC desk</b><div className="pmc-muted">Questions on a tender or bid?</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm" style={{ width: "100%", marginTop: "10px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a></div></nav><main className="pmc-main"><div className="sp-head"><div><div className="pmc-eyebrow">Alerts</div><h1>9 alerts · 2 need action</h1></div><div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--secondary">Mark all read</a><a href="#" className="pmc-btn pmc-btn--ghost"><svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg> Alert settings</a></div></div>
<div className="pmc-tabs" style={{ marginBottom: "12px" }}><button className="pmc-tab" aria-selected="true">All<span className="n">9</span></button><button className="pmc-tab">Needs action<span className="n">2</span></button><button className="pmc-tab">Tenders<span className="n">4</span></button><button className="pmc-tab">Payments<span className="n">2</span></button></div>
<section className="pmc-panel"><div className="al-r un"><span className="al-i" style={{ color: "var(--warning)" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg></span><div><b>EMD due in 2 days</b><span>Turnkey IVF Laboratory Setup · USD 61,380</span></div><span className="pmc-muted" style={{ fontSize: "12px" }}>2h</span><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Pay EMD</a></div><div className="al-r un"><span className="al-i" style={{ color: "var(--warning)" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg></span><div><b>Letter of award to sign</b><span>OPD Building Renovation — Block C</span></div><span className="pmc-muted" style={{ fontSize: "12px" }}>7d</span><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Review &amp; sign</a></div><div className="al-r"><span className="al-i" style={{ color: "var(--info)" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg></span><div><b>Corrigendum 1 issued</b><span>PMC-NOT-2026-0055 · clause 4.2 ISO classes</span></div><span className="pmc-muted" style={{ fontSize: "12px" }}>1d</span><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">See change</a></div><div className="al-r"><span className="al-i" style={{ color: "var(--success)" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg></span><div><b>Escrow confirmed your EMD</b><span>OPD Queue Management · INR 1,240,000</span></div><span className="pmc-muted" style={{ fontSize: "12px" }}>1d</span><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">View bid</a></div><div className="al-r"><span className="al-i" style={{ color: "var(--primary)" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg></span><div><b>3 new tenders match your KYC</b><span>Civil &amp; MEP · Kazakhstan</span></div><span className="pmc-muted" style={{ fontSize: "12px" }}>2d</span><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">See tenders</a></div></section></main></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Alerts</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Action first</b>Alerts that need you are highlighted and stay at the top until done.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details></div>
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
