import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { useVendorReviewsLive } from "@/lib/pmcELiveData";

export default function VendorReviewsE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useVendorReviewsLive({ enabled: isE });
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
    <div data-testid="vendor-reviews-e" data-pmc-e-page="vendor-reviews-e">
<header className="pmc-chrome pmc-vtop">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Supplier portal</span></a>
  <label className="pmc-search pmc-cmd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, documents…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-vtop__r">
    <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-iconbtn pmc-bell" aria-label="9 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">9</span></button>
    <button className="pmc-who" aria-haspopup="menu"><span className="pmc-avatar">EC</span><span className="pmc-who__t"><b>Emerald Corporates</b><span>PMC-SUP-000017 · KYC verified</span></span></button>
  </div>
</header><div className="pmc-app"><nav className="pmc-lnav" aria-label="Supplier"><a href="/vendor"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a><a href="/vendor/tenders"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Find tenders<span className="c">29</span></a><a href="/vendor/mybids"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>My bids<span className="c hot">1</span></a><a href="/vendor/emd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>EMD &amp; payments</a><a href="/vendor/signatures"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>Signatures<span className="c">1</span></a><hr /><a href="/vendor/company"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Company &amp; KYC</a><a href="/vendor/reviews" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Reviews</a><a href="/vendor/account"><svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg>Account &amp; security</a><a href="#" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs</a><div className="pmc-desk"><b>Your PMC desk</b><div className="pmc-muted">Questions on a tender or bid?</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm" style={{ width: "100%", marginTop: "10px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a></div></nav><main className="pmc-main"><div className="sp-head"><div><div className="pmc-eyebrow">Reviews</div><h1>Your reputation on the board</h1></div></div>
<div style={{ display: "grid", gridTemplateColumns: "320px minmax(0,1fr)", gap: "24px", alignItems: "start" }}>
<div className="pmc-panel" style={{ padding: "24px", textAlign: "center" }}><div className="pmc-figure" style={{ fontSize: "56px", lineHeight: "60px" }}>80</div><div style={{ fontWeight: "600" }}>Good</div><div className="pmc-muted" style={{ fontSize: "13px", marginBottom: "16px" }}>from 2 buyer reviews</div>
<div style={{ display: "grid", gridTemplateColumns: "110px 1fr 28px", gap: "10px", alignItems: "center", fontSize: "13px", marginTop: "8px", textAlign: "left" }}><span>Quality</span><span className="bar"><i style={{ width: "84%" }}></i></span><b>84</b></div><div style={{ display: "grid", gridTemplateColumns: "110px 1fr 28px", gap: "10px", alignItems: "center", fontSize: "13px", marginTop: "8px", textAlign: "left" }}><span>On time</span><span className="bar"><i style={{ width: "76%" }}></i></span><b>76</b></div><div style={{ display: "grid", gridTemplateColumns: "110px 1fr 28px", gap: "10px", alignItems: "center", fontSize: "13px", marginTop: "8px", textAlign: "left" }}><span>Documentation</span><span className="bar"><i style={{ width: "82%" }}></i></span><b>82</b></div><div style={{ display: "grid", gridTemplateColumns: "110px 1fr 28px", gap: "10px", alignItems: "center", fontSize: "13px", marginTop: "8px", textAlign: "left" }}><span>Communication</span><span className="bar"><i style={{ width: "78%" }}></i></span><b>78</b></div></div>
<div style={{ display: "grid", gap: "16px" }}><section className="pmc-panel" style={{ padding: "20px" }}><div style={{ display: "flex", justifyContent: "space-between" }}><div><b>Medical gas pipeline systems</b><div className="pmc-ref">Contract 026-0009</div></div><span className="pmc-pill pmc-pill--success">82 · Good</span></div><p style={{ margin: "12px 0 0", fontSize: "14px", lineHeight: "22px", color: "var(--ink-muted)" }}>“Installation met specification; handover documents complete. One milestone slipped by 6 days, communicated early.”</p><div className="pmc-muted" style={{ fontSize: "12px", marginTop: "10px" }}>PMC contracts team · 20 Sep 2026 · <a href="#">Reply</a></div></section><section className="pmc-panel" style={{ padding: "20px" }}><div style={{ display: "flex", justifyContent: "space-between" }}><div><b>Modular OTs — Wave 1</b><div className="pmc-ref">Debrief</div></div><span className="pmc-pill pmc-pill--success">78 · Good</span></div><p style={{ margin: "12px 0 0", fontSize: "14px", lineHeight: "22px", color: "var(--ink-muted)" }}>“Strong method statement; price was not competitive against L1.”</p><div className="pmc-muted" style={{ fontSize: "12px", marginTop: "10px" }}>Evaluation committee · 9 Sep 2026 · <a href="#">Reply</a></div></section>
<div className="pmc-callout pmc-callout--info"><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg><div>Reviews come from buyers after contracts and evaluations, and are moderated before publishing. You can reply once to each.</div></div></div></div></main></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Reviews</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>One reply each</b>Keep it factual; replies are moderated too.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="registration"><summary>How do I register as a supplier?</summary><p>Choose <b>Register as supplier</b>, enter your company details, then upload the KYC documents the form lists for your country and category. You can save and resume at any point. PMC reviews the file and you are notified when your KYC is approved.</p></details><details className="pmc-faq" data-cat="registration"><summary>Which documents does KYC need?</summary><p>The document list depends on your country and the licences your work category requires (for example, electrical or plumbing licences for Kazakhstan works packages). The registration form shows exactly which slots apply to you.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details></div>
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
