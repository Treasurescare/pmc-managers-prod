import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function AwardsPublicE({ legacy: Legacy }) {
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
    <div data-testid="awards-public-e" data-pmc-e-page="awards-public-e">
<header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></a>
  <nav className="pmc-nav"><a href="#" className="is-on">Tenders</a><a href="#">How it works</a><a href="#">For suppliers</a><a href="#">For buyers</a><a href="#">Trust &amp; security</a><a href="#" data-help-open="">Help &amp; FAQs</a></nav>
  <div className="pmc-top__act"><button className="pmc-btn pmc-btn--onchrome pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-globe" /></svg> EN</button><a href="#" className="pmc-btn pmc-btn--onchrome">Sign in</a><a href="#" className="pmc-btn pmc-btn--brass">Register as supplier</a></div>
</div></header>
<section className="pmc-chrome" style={{ padding: "36px 0 40px" }}><div className="pmc-wrap">
  <div className="pmc-crumb"><a href="#">Tender notices</a>/<span>Completed &amp; awarded</span></div>
  <h1 className="pmc-display" style={{ fontSize: "52px", lineHeight: "56px", margin: "10px 0 12px" }}>Completed &amp; awarded</h1><p className="pmc-muted" style={{ fontSize: "18px", lineHeight: "30px", margin: "0", maxWidth: "720px" }}>Every award is published with the winning value, the number of bids and a verifiable ledger reference. Losing bidders see their own ranking in their portal.</p>
</div></section>
<div className="pmc-wrap" style={{ padding: "32px 0 72px", display: "grid", gap: "28px" }}>
  <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "16px" }}>
    <div className="pmc-kpi pmc-panel" style={{ padding: "18px 20px" }}><div className="pmc-eyebrow" style={{ color: "var(--ink-muted)" }}>Awarded in 2026</div><div className="pmc-figure" style={{ marginTop: "8px" }}>3</div></div>
    <div className="pmc-panel" style={{ padding: "18px 20px" }}><div className="pmc-eyebrow" style={{ color: "var(--ink-muted)" }}>Total awarded value</div><div className="pmc-figure" style={{ marginTop: "8px" }}>USD 2.85M</div></div>
    <div className="pmc-panel" style={{ padding: "18px 20px" }}><div className="pmc-eyebrow" style={{ color: "var(--ink-muted)" }}>Average bids per tender</div><div className="pmc-figure" style={{ marginTop: "8px" }}>5.0</div></div>
    <div className="pmc-panel" style={{ padding: "18px 20px" }}><div className="pmc-eyebrow" style={{ color: "var(--ink-muted)" }}>Closed without award</div><div className="pmc-figure" style={{ marginTop: "8px" }}>0</div></div>
  </div>
  <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">Recent awards</h2><div style={{ display: "flex", gap: "8px" }}><select className="pmc-input"><option>All countries</option></select><select className="pmc-input"><option>2026</option></select></div></div>
    <table className="pmc-table"><thead><tr><th>Tender</th><th>Delivery</th><th className="num">Award value</th><th className="num">Bids</th><th>Awarded</th><th>Status</th><th></th></tr></thead><tbody><tr><td><div style={{ fontWeight: "600" }}>Modular Operation Theatres (OTs) — Wave 2</div><span className="pmc-ref">PMC-NOT-2026-0016</span></td><td>Kazakhstan</td><td className="num" style={{ fontWeight: "600" }}>USD 900,000</td><td className="num">6</td><td>12 Sep 2026</td><td><span className="pmc-pill pmc-pill--success">Awarded</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Award notice</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Modular Operation Theatres (OTs) — Wave 1</div><span className="pmc-ref">PMC-NOT-2026-0015</span></td><td>Kazakhstan</td><td className="num" style={{ fontWeight: "600" }}>USD 950,000</td><td className="num">4</td><td>8 Sep 2026</td><td><span className="pmc-pill pmc-pill--success">Awarded</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Award notice</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Modular operating suites — design &amp; supply</div><span className="pmc-ref">PMC-NOT-2026-0012</span></td><td>Kazakhstan</td><td className="num" style={{ fontWeight: "600" }}>USD 1,000,000</td><td className="num">5</td><td>29 Aug 2026</td><td><span className="pmc-pill pmc-pill--success">Awarded</span></td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Award notice</a></td></tr></tbody></table></section>
  <section className="pmc-card" style={{ display: "grid", gridTemplateColumns: "1.1fr .9fr", overflow: "hidden" }}>
    <div style={{ padding: "36px" }}>
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}><span className="pmc-eyebrow">Award notice</span><span className="pmc-ref">PMC-AWD-2026-00025</span></div>
      <h2 className="pmc-display" style={{ fontSize: "36px", lineHeight: "42px", margin: "8px 0 16px" }}>Modular Operation Theatres (OTs) — Wave 2</h2>
      <dl className="pmc-kv" style={{ gridTemplateColumns: "200px 1fr", maxWidth: "560px" }}><dt>Notice</dt><dd style={{ textAlign: "left" }} className="pmc-ref">PMC-NOT-2026-0016</dd><dt>Awarded to</dt><dd style={{ textAlign: "left" }}>Supplier A (sample)</dd><dt>Award value</dt><dd style={{ textAlign: "left" }}>USD 900,000</dd><dt>Bids received</dt><dd style={{ textAlign: "left" }}>6 · 4 technically qualified</dd><dt>Basis</dt><dd style={{ textAlign: "left" }}>Lowest evaluated price (L1) among qualified bids</dd><dt>Contract</dt><dd style={{ textAlign: "left" }}>Signed by DocuSign · 14 Sep 2026</dd></dl>
      <div style={{ display: "flex", gap: "8px", marginTop: "24px" }}><a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Download award notice (PDF)</a><a href="#" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg> Verify on ledger</a></div>
    </div>
    <div style={{ background: "var(--surface-sunken)", borderLeft: "1px solid var(--line)", padding: "32px" }}>
      <b style={{ fontSize: "15px" }}>How this tender ran</b>
      <div className="pmc-timeline" style={{ marginTop: "16px" }}>
        <div className="done"><span className="dot"></span><div><b>Published</b><span>18 Aug 2026 · notice.publish #1602</span></div></div>
        <div className="done"><span className="dot"></span><div><b>Bids closed · 6 received</b><span>4 Sep 2026</span></div></div>
        <div className="done"><span className="dot"></span><div><b>Technical scores locked · 4 qualified</b><span>8 Sep 2026 · quorum 3 of 2</span></div></div>
        <div className="done"><span className="dot"></span><div><b>Commercial opened · L1 ranked</b><span>9 Sep 2026</span></div></div>
        <div className="done"><span className="dot"></span><div><b>Awarded</b><span>12 Sep 2026 · award.issue #1745</span></div></div>
        <div className="done"><span className="dot"></span><div><b>Contract signed</b><span>14 Sep 2026 · contract.sign #1761</span></div></div>
      </div>
    </div>
  </section>
</div>
<footer className="pmc-chrome" style={{ padding: "40px 0 28px", marginTop: "0" }}><div className="pmc-wrap" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
  <div className="pmc-brand"><span className="pmc-brand__n" style={{ fontSize: "20px" }}>PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></div>
  <div style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: "20px" }} className="pmc-fcol"><a href="#">Open notices</a><a href="#">Help Centre</a><a href="#">Trust &amp; security</a><a href="#">Privacy</a><span className="pmc-muted">© 2026 PMC Managers Limited</span></div>
</div></footer>

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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Completed & awarded</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Verify any award</b>“Verify on ledger” recomputes the award's chain link in your browser.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Lost a bid?</b>Your own ranking and scores are in My bids › Closed.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details><details className="pmc-faq" data-cat="emd"><summary>What is EMD and how do I pay it?</summary><p>The Earnest Money Deposit secures your bid. Each tender sets it as a fixed amount or a percentage. Pay it from the bid tracker by transfer to escrow or by uploading a bank guarantee. Escrow confirms receipt before your bid moves on.</p></details></div>
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
