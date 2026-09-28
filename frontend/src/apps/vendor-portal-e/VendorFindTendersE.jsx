import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { useVendorFindTendersLive } from "@/lib/pmcELiveData";

export default function VendorFindTendersE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useVendorFindTendersLive({ enabled: isE });
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
    <div data-testid="vendor-find-tenders-e" data-pmc-e-page="vendor-find-tenders-e">
<header className="pmc-chrome pmc-vtop">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Supplier portal</span></a>
  <label className="pmc-search pmc-cmd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, documents…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-vtop__r">
    <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-iconbtn pmc-bell" aria-label="9 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">9</span></button>
    <button className="pmc-who" aria-haspopup="menu"><span className="pmc-avatar">EC</span><span className="pmc-who__t"><b>Emerald Corporates</b><span>PMC-SUP-000017 · KYC verified</span></span></button>
  </div>
</header><div className="pmc-app"><nav className="pmc-lnav" aria-label="Supplier"><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a><a href="#" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Find tenders<span className="c">29</span></a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>My bids<span className="c hot">1</span></a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>EMD &amp; payments</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>Signatures<span className="c">1</span></a><hr /><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Company &amp; KYC</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Reviews</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg>Account &amp; security</a><a href="#" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs</a><div className="pmc-desk"><b>Your PMC desk</b><div className="pmc-muted">Questions on a tender or bid?</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm" style={{ width: "100%", marginTop: "10px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a></div></nav><main className="pmc-main"><div className="sp-head"><div><div className="pmc-eyebrow">Find tenders</div><h1>12 tenders match your KYC</h1></div><div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg> Saved searches · 2</a></div></div>
<div className="pmc-filter" style={{ margin: "0 0 12px" }}><label className="pmc-search" style={{ flex: "1" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Keyword or reference" /></label><select className="pmc-input"><option>All categories</option></select><select className="pmc-input"><option>All countries</option></select><select className="pmc-input"><option>Closing first</option></select><button className="pmc-toggle" aria-pressed="true"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg> Matched to my KYC</button></div>
<div className="pmc-callout pmc-callout--warn" style={{ marginBottom: "16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg><div><b>2 more tenders</b> need a Plumbing &amp; firefighting licence (KZ). <a href="#">Add the licence</a> or bid with a licensed partner.</div></div>
<div className="pmc-grid3"><article className="pmc-tender">
  <div className="pmc-tender__top"><span className="pmc-tag">TENDER</span><span className="pmc-ref">PMC-NOT-2026-0055</span><span style={{ marginLeft: "auto" }} className="pmc-countdown" data-in="52">—</span></div>
  <h3 className="pmc-tender__title">Turnkey IVF Laboratory Setup — Embryology Lab, Cryopreservation & Cleanroom HVAC</h3>
  <dl className="pmc-tender__meta" style={{ margin: "0" }}><div className="is-budget"><dt>Indicative budget</dt><dd>USD 2,100,000</dd></div><div><dt>EMD</dt><dd style={{ fontWeight: "500" }}>3% of bid</dd></div><div><dt>Delivery</dt><dd style={{ fontWeight: "500" }}>Kazakhstan · Civil Works & MEP</dd></div></dl>
  <div className="pmc-tender__foot"><span className="pmc-pill pmc-pill--brand">Bid submitted</span><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Track</a></div>
</article><article className="pmc-tender">
  <div className="pmc-tender__top"><span className="pmc-tag">TENDER</span><span className="pmc-ref">PMC-NOT-2026-0037</span><span style={{ marginLeft: "auto" }} className="pmc-countdown" data-in="270">—</span></div>
  <h3 className="pmc-tender__title">Outpatient Department (OPD) Building Renovation & MEP Upgrade — Block C</h3>
  <dl className="pmc-tender__meta" style={{ margin: "0" }}><div className="is-budget"><dt>Indicative budget</dt><dd>KZT 850,000,000</dd></div><div><dt>EMD</dt><dd style={{ fontWeight: "500" }}>3% of bid</dd></div><div><dt>Delivery</dt><dd style={{ fontWeight: "500" }}>Kazakhstan · Civil Works & MEP</dd></div></dl>
  <div className="pmc-tender__foot"><span className="pmc-match"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Matches your KYC</span><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Start bid</a></div>
</article><article className="pmc-tender">
  <div className="pmc-tender__top"><span className="pmc-tag">RFP</span><span className="pmc-ref">PMC-NOT-2026-0038</span><span style={{ marginLeft: "auto" }} className="pmc-countdown" data-in="83">—</span></div>
  <h3 className="pmc-tender__title">Supply & Installation of OPD Queue Management & Digital Signage System</h3>
  <dl className="pmc-tender__meta" style={{ margin: "0" }}><div className="is-budget"><dt>Indicative budget</dt><dd>INR 62,000,000</dd></div><div><dt>EMD</dt><dd style={{ fontWeight: "500" }}>2% of bid</dd></div><div><dt>Delivery</dt><dd style={{ fontWeight: "500" }}>India · IT & Digital Health</dd></div></dl>
  <div className="pmc-tender__foot"><span className="pmc-pill pmc-pill--brand">Bid submitted</span><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Track</a></div>
</article><article className="pmc-tender">
  <div className="pmc-tender__top"><span className="pmc-tag">RFQ</span><span className="pmc-ref">PMC-NOT-2026-0054</span><span style={{ marginLeft: "auto" }} className="pmc-countdown" data-in="57">—</span></div>
  <h3 className="pmc-tender__title">Birth Suites — Linen, Consumables & Newborn Care Kits (Annual Rate Contract)</h3>
  <dl className="pmc-tender__meta" style={{ margin: "0" }}><div className="is-budget"><dt>Indicative budget</dt><dd>KZT 88,000,000</dd></div><div><dt>EMD</dt><dd style={{ fontWeight: "500" }}>Fixed KZT 1,760,000</dd></div><div><dt>Delivery</dt><dd style={{ fontWeight: "500" }}>Kazakhstan · Consumables & Implants</dd></div></dl>
  <div className="pmc-tender__foot"><span className="pmc-pill">Draft saved</span><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Continue draft</a></div>
</article><article className="pmc-tender">
  <div className="pmc-tender__top"><span className="pmc-tag">TENDER</span><span className="pmc-ref">PMC-NOT-2026-0036</span><span style={{ marginLeft: "auto" }} className="pmc-countdown" data-in="1400">—</span></div>
  <h3 className="pmc-tender__title">Supply of 400 Laptops for Faculty & Administration</h3>
  <dl className="pmc-tender__meta" style={{ margin: "0" }}><div className="is-budget"><dt>Indicative budget</dt><dd>USD 1,200,000</dd></div><div><dt>EMD</dt><dd style={{ fontWeight: "500" }}>2% of bid</dd></div><div><dt>Delivery</dt><dd style={{ fontWeight: "500" }}>Kazakhstan · IT & Digital Health</dd></div></dl>
  <div className="pmc-tender__foot"><span className="pmc-match"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Matches your KYC</span><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Start bid</a></div>
</article><article className="pmc-tender">
  <div className="pmc-tender__top"><span className="pmc-tag">TENDER</span><span className="pmc-ref">PMC-NOT-2026-0031</span><span style={{ marginLeft: "auto" }} className="pmc-countdown" data-in="620">—</span></div>
  <h3 className="pmc-tender__title">Modular Student Hostel Blocks — Design, Supply & Install</h3>
  <dl className="pmc-tender__meta" style={{ margin: "0" }}><div className="is-budget"><dt>Indicative budget</dt><dd>USD 18,500,000</dd></div><div><dt>EMD</dt><dd style={{ fontWeight: "500" }}>2% of bid</dd></div><div><dt>Delivery</dt><dd style={{ fontWeight: "500" }}>Kazakhstan · Hostels & residential</dd></div></dl>
  <div className="pmc-tender__foot"><span className="pmc-match"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Matches your KYC</span><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Start bid</a></div>
</article></div></main></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Find tenders</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>See everything</b>Turn off Matched to my KYC to see all open notices.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details></div>
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
