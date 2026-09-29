import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function HelpArticleE({ legacy: Legacy }) {
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
    <div data-testid="help-article-e" data-pmc-e-page="help-article-e">
<header className="pmc-chrome" style={{ borderBottom: "1px solid var(--chrome-line)" }}><div className="pmc-wrap" style={{ display: "flex", alignItems: "center", height: "64px", gap: "24px" }}>
  <a href="#" className="pmc-brand"><span className="pmc-brand__n" style={{ fontSize: "22px" }}>PMC Managers</span><span className="pmc-brand__s">Help Centre</span></a>
  <label className="pmc-search" style={{ flex: "0 1 480px", marginLeft: "24px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search help" /></label>
  <div style={{ marginLeft: "auto", display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--onchrome">Back to tender board</a><a href="#" className="pmc-btn pmc-btn--brass">Sign in</a></div></div></header>
<div className="pmc-wrap" style={{ display: "grid", gridTemplateColumns: "240px minmax(0,720px) 1fr", gap: "48px", padding: "36px 0 72px", alignItems: "start" }}>
  <nav style={{ position: "sticky", top: "24px", display: "grid", gap: "2px", fontSize: "14px" }} className="ha-nav"><div className="pmc-eyebrow" style={{ marginBottom: "8px" }}>EMD &amp; payments</div><a href="#">What is EMD?</a><a href="#">Paying EMD to escrow</a><a href="#" aria-current="page">Paying EMD by bank guarantee</a><a href="#">When EMD is refunded</a><a href="#">EMD exemptions</a><a href="#">Billing &amp; invoices</a><a href="#">Currencies</a></nav>
  <article className="ha">
    <div className="pmc-crumb"><a href="#">Help Centre</a>/<a href="#">EMD &amp; payments</a></div>
    <h1 className="pmc-display" style={{ fontSize: "48px", lineHeight: "52px", margin: "12px 0 10px" }}>Paying EMD by bank guarantee</h1>
    <div className="pmc-muted" style={{ fontSize: "14px", display: "flex", gap: "16px", marginBottom: "28px" }}><span><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg> 3 min read</span><span>For suppliers</span><span>Updated 26 Sep 2026</span></div>
    <p className="lead">If a tender accepts bank guarantees, you can lodge one instead of transferring the Earnest Money Deposit. The guarantee is checked by escrow before your bid moves to <b>Review, sign &amp; seal</b>.</p>
    <div className="pmc-callout pmc-callout--info"><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg><div>Check the tender first: the <b>EMD</b> row on the tender page says whether bank guarantees are accepted and the amount or percentage required.</div></div>
    <h2>Before you start</h2>
    <ul><li>Your bid's technical and commercial envelopes are sealed.</li><li>You know the EMD amount. For a percentage EMD, it is calculated from your bid and shown on the tracker.</li><li>Your bank has issued the guarantee in favour of <b>PMC Managers Limited</b>, valid for at least 90 days after the submission deadline.</li></ul>
    <h2>Steps</h2>
    <ol className="ha-steps">
      <li><div><b>Open the bid.</b> Go to <b>My bids</b> and choose the bid. Step 4, <b>EMD / bank guarantee</b>, is highlighted.</div></li>
      <li><div><b>Choose “Bank guarantee”.</b> The amount, beneficiary and minimum validity are filled in for you.</div></li>
      <li><div><b>Enter the guarantee details.</b> Issuing bank, guarantee number, amount and expiry date.</div></li>
      <li><div><b>Upload the signed guarantee.</b> A PDF scan of the original, all pages.</div></li>
      <li><div><b>Submit for escrow check.</b> Your tracker shows <span className="pmc-pill pmc-pill--info">Escrow confirming</span> until the escrow agent confirms, then moves on.</div></li>
    </ol>
    <div className="pmc-callout pmc-callout--warn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg><div>Lodge the guarantee <b>before</b> the submission deadline. A bid without confirmed EMD cannot be sealed.</div></div>
    <h2>If escrow rejects the guarantee</h2>
    <p>You'll get an alert with the reason, for example an expiry date that is too early. Fix it and re-upload from the same step; your envelopes stay sealed.</p>
    <div className="ha-fb"><b>Did this answer your question?</b><div style={{ display: "flex", gap: "8px" }}><button className="pmc-btn pmc-btn--secondary pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg> Yes</button><button className="pmc-btn pmc-btn--secondary pmc-btn--sm">No, I still need help</button></div></div>
  </article>
  <aside style={{ display: "grid", gap: "16px", position: "sticky", top: "24px" }}>
    <div className="pmc-panel" style={{ padding: "18px" }}><div className="pmc-eyebrow" style={{ color: "var(--ink-muted)", marginBottom: "10px" }}>On this page</div><div style={{ display: "grid", gap: "8px", fontSize: "14px" }}><a href="#">Before you start</a><a href="#">Steps</a><a href="#">If escrow rejects the guarantee</a></div></div>
    <a href="#" className="pmc-panel" style={{ padding: "18px", display: "flex", gap: "12px", alignItems: "center", color: "var(--ink)", textDecoration: "none" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-play" /></svg><div><b style={{ display: "block", fontSize: "14px" }}>Watch: 2-minute tour</b><span className="pmc-muted" style={{ fontSize: "13px" }}>Bank guarantee, start to finish</span></div></a>
    <div className="pmc-panel" style={{ padding: "18px" }}><b style={{ fontSize: "14px" }}>Still stuck?</b><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm" style={{ width: "100%", marginTop: "10px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a></div>
  </aside>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Help article</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Press ? anywhere</b>Opens help without leaving the page you're on.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="emd"><summary>What is EMD and how do I pay it?</summary><p>The Earnest Money Deposit secures your bid. Each tender sets it as a fixed amount or a percentage. Pay it from the bid tracker by transfer to escrow or by uploading a bank guarantee. Escrow confirms receipt before your bid moves on.</p></details><details className="pmc-faq" data-cat="emd"><summary>Which currencies are supported?</summary><p>Budgets and bids are shown in the tender's own currency, for example USD, KZT or INR. The tender states whether multi-currency bids are allowed.</p></details></div>
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
