import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function VendorEmdE({ legacy: Legacy }) {
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
    <div data-testid="vendor-emd-e" data-pmc-e-page="vendor-emd-e">
<header className="pmc-chrome pmc-vtop">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Supplier portal</span></a>
  <label className="pmc-search pmc-cmd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, documents…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-vtop__r">
    <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-iconbtn pmc-bell" aria-label="9 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">9</span></button>
    <button className="pmc-who" aria-haspopup="menu"><span className="pmc-avatar">EC</span><span className="pmc-who__t"><b>Emerald Corporates</b><span>PMC-SUP-000017 · KYC verified</span></span></button>
  </div>
</header><div className="pmc-app"><nav className="pmc-lnav" aria-label="Supplier"><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Find tenders<span className="c">29</span></a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>My bids<span className="c hot">1</span></a><a href="#" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>EMD &amp; payments</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>Signatures<span className="c">1</span></a><hr /><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Company &amp; KYC</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Reviews</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg>Account &amp; security</a><a href="#" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs</a><div className="pmc-desk"><b>Your PMC desk</b><div className="pmc-muted">Questions on a tender or bid?</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm" style={{ width: "100%", marginTop: "10px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a></div></nav><main className="pmc-main"><div className="sp-head"><div><div className="pmc-eyebrow">EMD &amp; payments</div><h1>Deposits, guarantees and refunds</h1></div><div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Statement (PDF)</a><a href="#" className="pmc-btn pmc-btn--primary">Pay EMD</a></div></div>
<div className="sp-kpis"><div><div className="l">Due now</div><div className="pmc-figure" style={{ color: "var(--warning)" }}>USD 61,380</div><div className="s">1 bid · closes in <span className="pmc-countdown" data-in="52">—</span></div></div><div><div className="l">Held in escrow</div><div className="pmc-figure">3 deposits</div><div className="s">USD 0 · INR 1.24M · KZT 24.4M</div></div><div><div className="l">Bank guarantees</div><div className="pmc-figure">1</div><div className="s">Next expiry 28 Dec 2026</div></div><div><div className="l">Refunded this year</div><div className="pmc-figure">USD 30,600</div><div className="s">1 refund · avg 7 days</div></div></div>
<section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">All deposits</h2><div style={{ display: "flex", gap: "8px" }}><select className="pmc-input"><option>All statuses</option></select><select className="pmc-input"><option>All currencies</option></select></div></div>
<table className="pmc-table"><thead><tr><th>Bid</th><th className="num">EMD</th><th>Method</th><th>Status</th><th>Detail</th><th></th></tr></thead><tbody><tr><td><div style={{ fontWeight: "600" }}>Turnkey IVF Laboratory Setup</div><span className="pmc-ref">PMC-BID-2026-00017</span></td><td className="num" style={{ fontWeight: "600" }}>USD 61,380</td><td>—</td><td><span className="pmc-pill pmc-pill--warning">Due</span></td><td className="pmc-muted" style={{ fontSize: "13px" }}>Pay by 30 Sep</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Pay EMD</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>OPD Queue Management</div><span className="pmc-ref">PMC-BID-2026-00020</span></td><td className="num" style={{ fontWeight: "600" }}>INR 1,240,000</td><td>Escrow transfer</td><td><span className="pmc-pill pmc-pill--info">Escrow confirming</span></td><td className="pmc-muted" style={{ fontSize: "13px" }}>Received 27 Sep</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">Details</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Birth Suites — Consumables</div><span className="pmc-ref">PMC-BID-2026-00016</span></td><td className="num" style={{ fontWeight: "600" }}>KZT 1,760,000</td><td>Bank guarantee</td><td><span className="pmc-pill pmc-pill--info">Held</span></td><td className="pmc-muted" style={{ fontSize: "13px" }}>BG expires 28 Dec 2026</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">Details</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>OPD Building Renovation</div><span className="pmc-ref">PMC-BID-2026-00022</span></td><td className="num" style={{ fontWeight: "600" }}>KZT 24,360,000</td><td>Escrow transfer</td><td><span className="pmc-pill pmc-pill--brand">Converting to security deposit</span></td><td className="pmc-muted" style={{ fontSize: "13px" }}>On contract signature</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">Details</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Modular OTs — Wave 1</div><span className="pmc-ref">PMC-BID-2026-00009</span></td><td className="num" style={{ fontWeight: "600" }}>USD 30,600</td><td>Escrow transfer</td><td><span className="pmc-pill pmc-pill--success">Refunded</span></td><td className="pmc-muted" style={{ fontSize: "13px" }}>Paid 16 Sep · ref RF-00412</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">Details</a></td></tr></tbody></table></section>
<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px", marginTop: "16px" }}>
  <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">How release works</h2></div><div className="pmc-panel__body"><div className="pmc-timeline">
    <div className="done"><span className="dot"></span><div><b>Escrow confirms receipt</b><span>Your bid moves to sign &amp; seal</span></div></div>
    <div className="done"><span className="dot"></span><div><b>Admin, certifier, legal, accounts clear</b><span>Each step is on the ledger</span></div></div>
    <div><span className="dot"></span><div><b>Not awarded → refunded</b><span>To your refund account after the award</span></div></div>
    <div><span className="dot"></span><div><b>Awarded → security deposit</b><span>Converted on contract signature</span></div></div></div></div></section>
  <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">Refund account</h2><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">Change</a></div><div className="pmc-panel__body"><dl className="pmc-kv"><dt>Bank</dt><dd>On file · verified</dd><dt>Account</dt><dd className="pmc-ref" style={{ color: "var(--ink)" }}>•••• 4417</dd><dt>Currency</dt><dd>USD, INR, KZT</dd><dt>Verified</dt><dd>12 Aug 2026</dd></dl><div className="pmc-muted" style={{ fontSize: "12px", marginTop: "12px" }}>Changing the refund account needs the signatory's approval and two-factor confirmation.</div></div></section>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · EMD & payments</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Use the payment reference</b>Escrow matches deposits by the bid reference; without it confirmation is slower.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Guarantee expiring?</b>Extend it before the date shown or the bid may be disqualified.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="emd"><summary>What is EMD and how do I pay it?</summary><p>The Earnest Money Deposit secures your bid. Each tender sets it as a fixed amount or a percentage. Pay it from the bid tracker by transfer to escrow or by uploading a bank guarantee. Escrow confirms receipt before your bid moves on.</p></details><details className="pmc-faq" data-cat="emd"><summary>Which currencies are supported?</summary><p>Budgets and bids are shown in the tender's own currency, for example USD, KZT or INR. The tender states whether multi-currency bids are allowed.</p></details></div>
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
