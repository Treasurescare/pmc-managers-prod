import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { useVendorMyBidsLive } from "@/lib/pmcELiveData";

export default function VendorMyBidsE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useVendorMyBidsLive({ enabled: isE });
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
    <div data-testid="vendor-mybids-e" data-pmc-e-page="vendor-mybids-e">
<header className="pmc-chrome pmc-vtop">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Supplier portal</span></a>
  <label className="pmc-search pmc-cmd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, documents…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-vtop__r">
    <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-iconbtn pmc-bell" aria-label="9 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">9</span></button>
    <button className="pmc-who" aria-haspopup="menu"><span className="pmc-avatar">EC</span><span className="pmc-who__t"><b>Emerald Corporates</b><span>PMC-SUP-000017 · KYC verified</span></span></button>
  </div>
</header><div className="pmc-app"><nav className="pmc-lnav" aria-label="Supplier"><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Find tenders<span className="c">29</span></a><a href="#" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>My bids<span className="c hot">1</span></a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>EMD &amp; payments</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>Signatures<span className="c">1</span></a><hr /><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Company &amp; KYC</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Reviews</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg>Account &amp; security</a><a href="#" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs</a><div className="pmc-desk"><b>Your PMC desk</b><div className="pmc-muted">Questions on a tender or bid?</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm" style={{ width: "100%", marginTop: "10px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a></div></nav><main className="pmc-main"><div className="sp-head"><div><div className="pmc-eyebrow">My bids</div><h1>Every bid, and what it needs</h1></div><a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg> Find tenders</a></div>
<div className="sp-kpis"><div><div className="l">Active</div><div className="pmc-figure">4</div><div className="s">1 needs you</div></div><div><div className="l">Win rate</div><div className="pmc-figure">50%</div><div className="s">2 of 4 decided bids</div></div><div><div className="l">Value in play</div><div className="pmc-figure">USD 2.8M</div><div className="s">+ INR 58.9M, KZT 894M</div></div><div><div className="l">EMD held</div><div className="pmc-figure">USD 76,380</div><div className="s">across 3 bids</div></div></div>
<div className="pmc-tabs" style={{ marginBottom: "16px" }}><button className="pmc-tab" aria-selected="true">Active<span className="n">4</span></button><button className="pmc-tab">Drafts<span className="n">3</span></button><button className="pmc-tab">Closed<span className="n">7</span></button><button className="pmc-tab">Withdrawn<span className="n">0</span></button></div>
<section className="pmc-panel"><table className="pmc-table"><thead><tr><th>Bid</th><th className="num">Your price</th><th>Progress</th><th>Status</th><th>Closes</th><th></th></tr></thead><tbody><tr><td><div style={{ fontWeight: "600" }}>Turnkey IVF Laboratory Setup</div><span className="pmc-ref">PMC-BID-2026-00017</span></td><td className="num" style={{ fontWeight: "600" }}>USD 2,046,000</td><td><span className="mini-track"><i className="d"></i><i className="d"></i><i className="d"></i><i className="n"></i><i className=""></i></span></td><td><span className="pmc-pill pmc-pill--warning">Awaiting your EMD</span></td><td><span className="pmc-countdown" data-in="52">—</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Pay EMD</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>OPD Queue Management & Digital Signage</div><span className="pmc-ref">PMC-BID-2026-00020</span></td><td className="num" style={{ fontWeight: "600" }}>INR 58,900,000</td><td><span className="mini-track"><i className="d"></i><i className="d"></i><i className="d"></i><i className="n"></i><i className=""></i></span></td><td><span className="pmc-pill pmc-pill--info">Escrow confirming</span></td><td><span className="pmc-countdown" data-in="83">—</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">View</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Birth Suites — Consumables & Kits</div><span className="pmc-ref">PMC-BID-2026-00016</span></td><td className="num" style={{ fontWeight: "600" }}>KZT 82,400,000</td><td><span className="mini-track"><i className="d"></i><i className="n"></i><i className=""></i><i className=""></i><i className=""></i></span></td><td><span className="pmc-pill ">Draft</span></td><td><span className="pmc-countdown" data-in="57">—</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Continue</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>OPD Building Renovation — Block C</div><span className="pmc-ref">PMC-BID-2026-00022</span></td><td className="num" style={{ fontWeight: "600" }}>KZT 812,000,000</td><td><span className="mini-track"><i className="d"></i><i className="d"></i><i className="d"></i><i className="d"></i><i className="d"></i></span></td><td><span className="pmc-pill pmc-pill--success">Awarded</span></td><td><span className="pmc-muted">Awarded 21 Sep</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Sign LOA</a></td></tr></tbody></table></section>
<h2 style={{ fontSize: "18px", margin: "32px 0 12px" }}>Recently decided</h2>
<section className="pmc-panel"><table className="pmc-table"><thead><tr><th>Bid</th><th className="num">Your price</th><th>Your rank</th><th>Outcome</th><th>Debrief</th><th></th></tr></thead><tbody><tr><td><div style={{ fontWeight: "600" }}>Modular Operation Theatres — Wave 1</div><span className="pmc-ref">PMC-BID-2026-00009</span></td><td className="num">USD 1,020,000</td><td>2 of 4</td><td><span className="pmc-pill ">Not awarded</span></td><td className="pmc-muted" style={{ fontSize: "13px" }}>Technical 78 · L2, 7% above L1</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">Debrief</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Medical gas pipeline systems</div><span className="pmc-ref">PMC-BID-2026-00005</span></td><td className="num">USD 410,000</td><td>1 of 5</td><td><span className="pmc-pill pmc-pill--success">Awarded</span></td><td className="pmc-muted" style={{ fontSize: "13px" }}>Contract 026-0009 active</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">Debrief</a></td></tr></tbody></table></section>
<div className="pmc-callout pmc-callout--info" style={{ marginTop: "16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg><div>After every decision you get a <b>debrief</b>: your technical score by criterion and your price position against L1. Use it to sharpen the next bid.</div></div></main></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · My bids</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>One action per row</b>The button always does the step that's waiting on you.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Debriefs</b>Open a decided bid to see your scores and price position.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details><details className="pmc-faq" data-cat="awards"><summary>How are contracts signed?</summary><p>Awards, purchase orders and contracts are signed with DocuSign, either inside the portal or through a DocuSign email link. Signed copies appear under <b>Signatures</b>.</p></details></div>
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
