import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function VendorHomeE({ legacy: Legacy }) {
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
    <div data-testid="vendor-home-e" data-pmc-e-page="vendor-home-e">
<header className="pmc-chrome pmc-vtop">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Supplier portal</span></a>
  <label className="pmc-search pmc-cmd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, documents…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-vtop__r">
    <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-iconbtn pmc-bell" aria-label="9 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">9</span></button>
    <button className="pmc-who" aria-haspopup="menu"><span className="pmc-avatar">EC</span><span className="pmc-who__t"><b>Emerald Corporates</b><span>PMC-SUP-000017 · KYC verified</span></span></button>
  </div>
</header>
<div className="pmc-app">
<nav className="pmc-lnav" aria-label="Supplier">
  <a href="#" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a>
  <a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Find tenders<span className="c">29</span></a>
  <a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>My bids<span className="c hot">1</span></a>
  <a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>EMD &amp; payments</a>
  <a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>Signatures<span className="c">1</span></a>
  <hr />
  <a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Company &amp; KYC</a>
  <a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Reviews</a>
  <a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg>Account &amp; security</a>
  <a href="#" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs</a>
  <div className="pmc-desk"><b>Your PMC desk</b><div className="pmc-muted">Questions on a tender or bid?</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm" style={{ width: "100%", marginTop: "10px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a></div>
</nav>
<main className="pmc-main">
  <div className="pmc-hi">
    <div><div className="pmc-eyebrow">Monday, 28 September 2026</div><h1>Good morning, Emerald Corporates</h1></div>
    <div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Continue draft</a><a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg> Find tenders</a></div>
  </div>

  <section className="pmc-next" aria-label="Do this next">
    <div className="pmc-next__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg></div>
    <div><div className="pmc-eyebrow">Do this next · 1 of 1</div><h2>Pay EMD for Turnkey IVF Laboratory Setup</h2><div className="pmc-muted" style={{ fontSize: "14px" }}>USD 61,380 (3% of your bid) to escrow, or upload a bank guarantee. Your bid can't move to sign &amp; seal until it's received. Closes in <span className="pmc-countdown" data-in="52">—</span>.</div></div>
    <div style={{ display: "flex", gap: "8px", alignItems: "center" }}><button className="pmc-btn pmc-btn--ghost" data-help-open="">What is EMD?</button><a href="#" className="pmc-btn pmc-btn--secondary">Upload bank guarantee</a><a href="#" className="pmc-btn pmc-btn--primary">Pay EMD</a></div>
  </section>

  <div className="pmc-kpis">
    <div className="pmc-kpi"><div className="l">Active bids</div><div className="pmc-figure">4</div><div className="s">1 needs you · 1 awarded</div></div>
    <div className="pmc-kpi"><div className="l">Closing this week</div><div className="pmc-figure">3</div><div className="s">of the tenders you follow</div></div>
    <div className="pmc-kpi"><div className="l">Matched to your KYC</div><div className="pmc-figure">12</div><div className="s">of 29 open notices</div></div>
    <div className="pmc-kpi"><div className="l">KYC status</div><div style={{ margin: "12px 0 10px" }}><span className="pmc-pill pmc-pill--success">Verified</span></div><div className="s">Licences on file: Civil works, MEP, Medical supply</div></div>
  </div>

  <section className="pmc-panel" style={{ marginBottom: "32px" }}>
    <div className="pmc-panel__head"><h2 className="pmc-panel__title">Your bids</h2><div className="pmc-tabs" style={{ border: "0" }}><button className="pmc-tab" aria-selected="true">Active<span className="n">4</span></button><button className="pmc-tab">Closed<span className="n">7</span></button></div></div>
    <div className="pmc-bidrow">
  <div><div style={{ display: "flex", gap: "8px", alignItems: "center" }}><span className="pmc-ref">PMC-BID-2026-00017</span><span className="pmc-pill pmc-pill--warning">Awaiting your EMD</span></div><h3>Turnkey IVF Laboratory Setup — Embryology Lab & Cleanroom HVAC</h3><div className="pmc-muted" style={{ fontSize: "13px" }}>Your bid <b style={{ color: "var(--ink)" }}>USD 2,046,000</b> · closes <span className="pmc-countdown" data-in="52">—</span></div></div>
  <div><div className="pmc-track"><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Eligibility</span></div><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Technical</span></div><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Commercial</span></div><div className="pmc-track__step is-now"><span className="pmc-track__dot">4</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>EMD</span></div><div className="pmc-track__step "><span className="pmc-track__dot">5</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Sign & seal</span></div></div></div>
  <div className="act"><a href="#" className="pmc-btn pmc-btn--primary">Pay EMD</a><span className="pmc-muted" style={{ fontSize: "12px", lineHeight: "16px" }}>USD 61,380 due · 3% of bid</span></div>
</div><div className="pmc-bidrow">
  <div><div style={{ display: "flex", gap: "8px", alignItems: "center" }}><span className="pmc-ref">PMC-BID-2026-00020</span><span className="pmc-pill pmc-pill--info">Escrow confirming</span></div><h3>Supply & Installation of OPD Queue Management & Digital Signage</h3><div className="pmc-muted" style={{ fontSize: "13px" }}>Your bid <b style={{ color: "var(--ink)" }}>INR 58,900,000</b> · closes <span className="pmc-countdown" data-in="83">—</span></div></div>
  <div><div className="pmc-track"><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Eligibility</span></div><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Technical</span></div><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Commercial</span></div><div className="pmc-track__step is-now"><span className="pmc-track__dot">4</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>EMD</span></div><div className="pmc-track__step "><span className="pmc-track__dot">5</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Sign & seal</span></div></div></div>
  <div className="act"><a href="#" className="pmc-btn pmc-btn--secondary">View bid</a><span className="pmc-muted" style={{ fontSize: "12px", lineHeight: "16px" }}>INR 1,240,000 paid · escrow confirming</span></div>
</div><div className="pmc-bidrow">
  <div><div style={{ display: "flex", gap: "8px", alignItems: "center" }}><span className="pmc-ref">PMC-BID-2026-00016</span><span className="pmc-pill">Draft</span></div><h3>Birth Suites — Linen, Consumables & Newborn Care Kits</h3><div className="pmc-muted" style={{ fontSize: "13px" }}>Your bid <b style={{ color: "var(--ink)" }}>KZT 82,400,000</b> · closes <span className="pmc-countdown" data-in="57">—</span></div></div>
  <div><div className="pmc-track"><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Eligibility</span></div><div className="pmc-track__step is-now"><span className="pmc-track__dot">2</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Technical</span></div><div className="pmc-track__step "><span className="pmc-track__dot">3</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Commercial</span></div><div className="pmc-track__step "><span className="pmc-track__dot">4</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>EMD</span></div><div className="pmc-track__step "><span className="pmc-track__dot">5</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Sign & seal</span></div></div></div>
  <div className="act"><a href="#" className="pmc-btn pmc-btn--secondary">Continue draft</a><span className="pmc-muted" style={{ fontSize: "12px", lineHeight: "16px" }}>Technical envelope 70% complete</span></div>
</div><div className="pmc-bidrow">
  <div><div style={{ display: "flex", gap: "8px", alignItems: "center" }}><span className="pmc-ref">PMC-BID-2026-00022</span><span className="pmc-pill pmc-pill--success">Awarded</span></div><h3>OPD Building Renovation & MEP Upgrade — Block C</h3><div className="pmc-muted" style={{ fontSize: "13px" }}>Your bid <b style={{ color: "var(--ink)" }}>KZT 812,000,000</b> · awarded 21 Sep 2026</div></div>
  <div><div className="pmc-track"><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Eligibility</span></div><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Technical</span></div><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Commercial</span></div><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>EMD</span></div><div className="pmc-track__step is-done"><span className="pmc-track__dot">✓</span><span className="pmc-track__label" style={{ fontSize: "12px" }}>Sign & seal</span></div></div></div>
  <div className="act"><a href="#" className="pmc-btn pmc-btn--secondary">View contract</a><span className="pmc-muted" style={{ fontSize: "12px", lineHeight: "16px" }}>Awarded · sign the LOA</span></div>
</div>
  </section>

  <section>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end" }}><div><h2 style={{ margin: "0", fontSize: "22px", lineHeight: "28px" }}>Tenders for you</h2><div className="pmc-muted" style={{ fontSize: "14px" }}>Open notices that match your licences and categories, closing first.</div></div><a href="#">See all 29 open notices</a></div>
    <div className="pmc-filter">
      <label className="pmc-search" style={{ flex: "1", minWidth: "240px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Keyword or reference no." /></label>
      <select className="pmc-input" aria-label="Category"><option>All categories</option></select>
      <select className="pmc-input" aria-label="Country"><option>All countries</option></select>
      <select className="pmc-input" aria-label="Value"><option>Any value</option></select>
      <select className="pmc-input" aria-label="Sort"><option>Closing first</option><option>Newest</option><option>Highest value</option></select>
      <button className="pmc-toggle" aria-pressed="true"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg> Matched to my KYC</button>
    </div>
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
</article></div>
  </section>
</main>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Supplier home</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Your next step is pinned at the top</b>“Do this next” always shows the one action that unblocks a bid.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Paying EMD</b>Pay to escrow or upload a bank guarantee from the bid tracker. Escrow confirms receipt within the tender's timeline.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Can't see a tender?</b>Turn off “Matched to my KYC” to see every open notice.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details><details className="pmc-faq" data-cat="emd"><summary>What is EMD and how do I pay it?</summary><p>The Earnest Money Deposit secures your bid. Each tender sets it as a fixed amount or a percentage. Pay it from the bid tracker by transfer to escrow or by uploading a bank guarantee. Escrow confirms receipt before your bid moves on.</p></details><details className="pmc-faq" data-cat="emd"><summary>Which currencies are supported?</summary><p>Budgets and bids are shown in the tender's own currency, for example USD, KZT or INR. The tender states whether multi-currency bids are allowed.</p></details><details className="pmc-faq" data-cat="awards"><summary>How are contracts signed?</summary><p>Awards, purchase orders and contracts are signed with DocuSign, either inside the portal or through a DocuSign email link. Signed copies appear under <b>Signatures</b>.</p></details></div>
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
