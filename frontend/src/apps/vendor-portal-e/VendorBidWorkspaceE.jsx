import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { useVendorBidWorkspaceLive } from "@/lib/pmcELiveData";

export default function VendorBidWorkspaceE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useVendorBidWorkspaceLive({ enabled: isE, bidId: (window.location.pathname.split("/").pop() || "") });
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
    <div data-testid="vendor-bid-workspace-e" data-pmc-e-page="vendor-bid-workspace-e">
<header className="pmc-chrome pmc-vtop">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Supplier portal</span></a>
  <label className="pmc-search pmc-cmd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, documents…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-vtop__r">
    <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-iconbtn pmc-bell" aria-label="9 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">9</span></button>
    <button className="pmc-who" aria-haspopup="menu"><span className="pmc-avatar">EC</span><span className="pmc-who__t"><b>Emerald Corporates</b><span>PMC-SUP-000017 · KYC verified</span></span></button>
  </div>
</header><div className="pmc-app"><nav className="pmc-lnav" aria-label="Supplier"><a href="/vendor"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a><a href="/vendor/tenders"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Find tenders</a><a href="/vendor/mybids" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>My bids</a><a href="/vendor/emd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>EMD &amp; payments</a><a href="/vendor/signatures"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>Signatures</a><hr /><a href="/vendor/company"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Company &amp; KYC</a><a href="/vendor/reviews"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Reviews</a><a href="/vendor/account"><svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg>Account &amp; security</a><a href="#" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs</a><div className="pmc-desk"><b>Your PMC desk</b><div className="pmc-muted">Questions on a tender or bid?</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm" style={{ width: "100%", marginTop: "10px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a></div></nav><main className="pmc-main">
<div className="pmc-crumb"><a href="#">My bids</a>/<span>PMC-BID-2026-00017</span></div>
<div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-end", gap: "24px", margin: "10px 0 20px" }}>
  <div><div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "8px" }}><span className="pmc-tag">Tender</span><a className="pmc-ref" href="#">PMC-NOT-2026-0055</a><span className="pmc-pill pmc-pill--warning">Awaiting your EMD</span></div>
  <h1 className="pmc-display" style={{ fontSize: "36px", lineHeight: "42px", margin: "0" }}>Turnkey IVF Laboratory Setup — Embryology Lab &amp; Cleanroom HVAC</h1></div>
  <div className="bw-clock"><span className="pmc-eyebrow">Submission closes in</span><span className="pmc-countdown" data-in="52" style={{ fontSize: "24px", lineHeight: "32px" }}>—</span><span className="pmc-muted" style={{ fontSize: "12px" }}>30 Sep 2026, 21:48 Almaty</span></div>
</div>
<div style={{ display: "grid", gridTemplateColumns: "260px minmax(0,1fr) 300px", gap: "24px", alignItems: "start" }}>
  <nav className="pmc-steplist pmc-panel" style={{ padding: "10px", position: "sticky", top: "88px" }} aria-label="Bid steps">
    <a href="#" className="done"><span className="d">✓</span><span>Eligibility<small>KYC match · 4 of 4</small></span></a>
    <a href="#" className="done"><span className="d">✓</span><span>Technical envelope<small>Sealed 27 Sep, 14:02</small></span></a>
    <a href="#" className="done"><span className="d">✓</span><span>Commercial envelope<small>Sealed 27 Sep, 14:20</small></span></a>
    <a href="#" className="now"><span className="d">4</span><span>EMD / bank guarantee<small>Your action</small></span></a>
    <a href="#"><span className="d">5</span><span>Review, sign &amp; seal<small>After EMD is confirmed</small></span></a>
  </nav>
  <div style={{ display: "grid", gap: "16px" }}>
    <section className="pmc-panel">
      <div className="pmc-panel__head"><div><div className="pmc-eyebrow">Step 4 of 5</div><h2 className="pmc-panel__title" style={{ fontSize: "20px" }}>Pay the Earnest Money Deposit</h2></div><button className="pmc-btn pmc-btn--ghost pmc-btn--sm" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> What is EMD?</button></div>
      <div className="pmc-panel__body" style={{ display: "grid", gap: "16px" }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", padding: "16px 18px", background: "var(--surface-sunken)", borderRadius: "var(--radius-sm)" }}><div><div className="pmc-muted" style={{ fontSize: "13px" }}>EMD due · 3% of your bid of USD 2,046,000</div><div className="pmc-figure">USD 61,380</div></div><span className="pmc-pill pmc-pill--warning">Due before deadline</span></div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          <label className="pmc-radio on"><span className="o"></span><div><b>Transfer to escrow</b><div className="pmc-muted" style={{ fontSize: "13px", lineHeight: "20px", marginTop: "4px" }}>Bank transfer to the PMC escrow account. Usually confirmed within one working day.</div></div></label>
          <label className="pmc-radio"><span className="o"></span><div><b>Bank guarantee</b><div className="pmc-muted" style={{ fontSize: "13px", lineHeight: "20px", marginTop: "4px" }}>Upload a guarantee in favour of PMC Managers Limited, valid 90+ days after the deadline.</div></div></label>
        </div>
        <div className="pmc-panel" style={{ background: "var(--surface)" }}>
          <div className="pmc-copy"><span>Beneficiary</span><b>PMC Managers Limited — Escrow</b><button className="pmc-btn pmc-btn--ghost pmc-btn--sm">Copy</button></div>
          <div className="pmc-copy"><span>Account / IBAN</span><b>Shown after you confirm</b><button className="pmc-btn pmc-btn--ghost pmc-btn--sm" disabled>Copy</button></div>
          <div className="pmc-copy"><span>Payment reference (required)</span><b>PMC-BID-2026-00017</b><button className="pmc-btn pmc-btn--ghost pmc-btn--sm">Copy</button></div>
          <div className="pmc-copy"><span>Amount</span><b>USD 61,380.00</b><button className="pmc-btn pmc-btn--ghost pmc-btn--sm">Copy</button></div>
        </div>
        <div className="pmc-field"><label>Upload proof of transfer</label><div className="pmc-drop" style={{ padding: "20px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg><b style={{ color: "var(--ink)" }}>Drop the bank confirmation (PDF) or browse</b></div><span className="h">Escrow matches your payment reference; the proof speeds it up.</span></div>
        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--secondary">Save and finish later</a><a href="#" className="pmc-btn pmc-btn--primary">Submit for escrow check</a></div>
      </div>
    </section>
    <section className="pmc-panel">
      <div className="pmc-panel__head"><h2 className="pmc-panel__title">Sealed envelopes</h2><span className="pmc-pill pmc-pill--success">2 of 2 sealed</span></div>
      <div className="bw-env"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg></span><div><b>Technical envelope</b><span className="s">14 files · 212 MB · method statement, references, ISO 14644 certificates, subcontractor details</span><div className="pmc-hashline" style={{ marginTop: "6px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><code>bid.seal #1891 · 7c1e…a90b</code></div></div><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Unseal to edit</a></div>
      <div className="bw-env"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg></span><div><b>Commercial envelope</b><span className="s">BOQ.xlsx · price schedule · USD 2,046,000 total</span><div className="pmc-hashline" style={{ marginTop: "6px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><code>bid.seal #1892 · e3d4…11f7</code></div></div><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Unseal to edit</a></div>
      <div style={{ padding: "14px 20px", borderTop: "1px solid var(--line)" }} className="pmc-muted"><span style={{ fontSize: "13px" }}>Nobody at PMC can open these before the deadline. Unsealing is logged, and you must re-seal before the deadline.</span></div>
    </section>
  </div>
  <aside style={{ display: "grid", gap: "16px", position: "sticky", top: "88px" }}>
    <div className="pmc-panel" style={{ padding: "18px" }}><b style={{ fontSize: "15px" }}>Before you can seal</b>
      <div style={{ display: "grid", gap: "10px", marginTop: "12px", fontSize: "14px" }}>
        <div className="bw-ck ok"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>KYC valid for this tender</div><div className="bw-ck ok"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Technical envelope sealed</div><div className="bw-ck ok"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Commercial envelope sealed</div><div className="bw-ck"><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>EMD confirmed by escrow</div><div className="bw-ck"><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>Declarations signed</div></div></div>
    <div className="pmc-panel" style={{ padding: "18px" }}><b style={{ fontSize: "15px" }}>Tender updates</b><div className="pmc-callout pmc-callout--info" style={{ marginTop: "10px", fontSize: "13px", lineHeight: "20px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg><div><b>Corrigendum 1</b> changed clause 4.2 (ISO classes). Your technical envelope was sealed after it. ✓</div></div></div>
    <div className="pmc-panel" style={{ padding: "18px" }}><b style={{ fontSize: "15px" }}>Your team on this bid</b><div style={{ display: "grid", gap: "10px", marginTop: "12px", fontSize: "14px" }}><div style={{ display: "flex", gap: "10px", alignItems: "center" }}><span className="pmc-avatar" style={{ width: "28px", height: "28px", fontSize: "11px" }}>RK</span>Rk · Signatory</div><div style={{ display: "flex", gap: "10px", alignItems: "center" }}><span className="pmc-avatar" style={{ width: "28px", height: "28px", fontSize: "11px" }}>PM</span>Tender manager · Editor</div></div></div>
  </aside>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Bid workspace</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Sealed means sealed</b>Envelopes can't be opened by anyone before the deadline. If you unseal to edit, re-seal before it closes.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Paying EMD</b>Use the payment reference exactly as shown so escrow can match it.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details><details className="pmc-faq" data-cat="emd"><summary>What is EMD and how do I pay it?</summary><p>The Earnest Money Deposit secures your bid. Each tender sets it as a fixed amount or a percentage. Pay it from the bid tracker by transfer to escrow or by uploading a bank guarantee. Escrow confirms receipt before your bid moves on.</p></details><details className="pmc-faq" data-cat="emd"><summary>Which currencies are supported?</summary><p>Budgets and bids are shown in the tender's own currency, for example USD, KZT or INR. The tender states whether multi-currency bids are allowed.</p></details></div>
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
