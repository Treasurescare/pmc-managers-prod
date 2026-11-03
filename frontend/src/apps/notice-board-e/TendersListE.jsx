import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { usePublicLiveData } from "@/lib/pmcELiveData";
import { usePublicNav } from "@/lib/pmcEPublicNav";
import PmcSocialLinks from "@/components/PmcSocialLinks";

export default function TendersListE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  usePublicLiveData({ enabled: isE });
  usePublicNav(isE);
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
    <div data-testid="tenders-list-e" data-pmc-e-page="tenders-list-e">
<header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Grid</span></a>
  <nav className="pmc-nav"><a href="#" className="is-on">Tenders</a><a href="#">How it works</a><a href="#">For suppliers</a><a href="#">For buyers</a><a href="#">Trust &amp; security</a><a href="#" data-help-open="">Help &amp; FAQs</a></nav>
  <div className="pmc-top__act"><button className="pmc-btn pmc-btn--onchrome pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-globe" /></svg> EN</button><a href="#" className="pmc-btn pmc-btn--onchrome">Sign in</a><a href="#" className="pmc-btn pmc-btn--brass">Register as supplier</a></div>
</div></header>
<section className="pmc-chrome" style={{ padding: "36px 0 32px" }}><div className="pmc-wrap">
  <div className="pmc-crumb"><a href="#">Home</a>/<span>Tender notices</span></div>
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", margin: "10px 0 20px" }}><h1 className="pmc-display" style={{ fontSize: "52px", lineHeight: "56px", margin: "0" }}>Tender notices</h1><span className="pmc-muted">—</span></div>
  <form style={{ display: "flex", gap: "8px", padding: "8px", background: "var(--chrome-raised)", border: "1px solid var(--chrome-line)", borderRadius: "var(--radius-md)" }}>
    <label className="pmc-search" style={{ flex: "1", height: "48px", background: "var(--surface)", borderColor: "var(--surface)" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input defaultValue="" placeholder="Search tenders, refs or categories" style={{ color: "var(--ink)" }} /></label>
    <button className="pmc-btn pmc-btn--brass pmc-btn--lg">Search</button></form>
</div></section>
<div className="pmc-wrap" style={{ display: "grid", gridTemplateColumns: "272px 1fr", gap: "32px", padding: "32px 0 72px" }}>
  <aside className="tl-filters" aria-label="Filters">
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}><b style={{ fontSize: "15px" }}>Filters</b><a href="#" style={{ fontSize: "13px" }}>Clear all</a></div>
    <fieldset><legend>Status</legend><label className="pmc-check"><input type="radio" name="s" defaultChecked />Open for bids<span className="c">0</span></label><label className="pmc-check"><input type="radio" name="s" />Closing this week<span className="c">0</span></label><label className="pmc-check"><input type="radio" name="s" />Closed<span className="c">0</span></label><label className="pmc-check"><input type="radio" name="s" />Awarded<span className="c">0</span></label></fieldset>
    <fieldset><legend>Notice type</legend><label className="pmc-check"><input type="checkbox" defaultChecked />Tender<span className="c">0</span></label><label className="pmc-check"><input type="checkbox" defaultChecked />RFP<span className="c">0</span></label><label className="pmc-check"><input type="checkbox" defaultChecked />RFQ<span className="c">0</span></label></fieldset>
    <fieldset><legend>Delivery country</legend></fieldset>
    <fieldset><legend>Category</legend></fieldset>
    <fieldset><legend>Indicative budget (USD equiv.)</legend><div style={{ display: "flex", gap: "8px" }}><input className="pmc-input" style={{ width: "100%" }} placeholder="Min" /><input className="pmc-input" style={{ width: "100%" }} placeholder="Max" /></div></fieldset>
    <div className="pmc-panel" style={{ padding: "16px", background: "var(--primary-soft)", borderColor: "var(--primary-soft)" }}><b style={{ fontSize: "14px" }}>Get alerts for this search</b><p className="pmc-muted" style={{ fontSize: "13px", lineHeight: "20px", margin: "4px 0 10px" }}>We'll email you when a matching notice is published or amended.</p><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm" style={{ width: "100%" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg> Save search &amp; alert me</a></div>
  </aside>
  <section>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "12px" }}>
      <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}><span style={{ fontSize: "14px" }}><b>0 results</b></span><span className="pmc-chip">Tender ×</span><span className="pmc-chip">RFP ×</span><span className="pmc-chip">RFQ ×</span></div>
      <div style={{ display: "flex", gap: "8px", alignItems: "center" }}><span className="pmc-muted" style={{ fontSize: "13px" }}>Sort</span><select className="pmc-input"><option>Closing first</option><option>Newest</option><option>Highest budget</option></select></div>
    </div>
    <div className="pmc-panel"><article className="tl-row">
  <div className="tl-main"><div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap" }}><span className="pmc-tag">TENDER</span><span className="pmc-ref"></span><span className="pmc-pill pmc-pill--info" style={{ display: "none" }}>Corrigendum 1</span><span className="pmc-pill pmc-pill--brand" style={{ display: "none" }}>New</span></div>
  <h3><a href="#"></a></h3><div className="pmc-muted" style={{ fontSize: "13px" }}></div></div>
  <div className="tl-num"><div className="l">Indicative budget</div><div className="v">—</div></div>
  <div className="tl-num"><div className="l">Closing</div><div className="v"><span className="pmc-countdown" data-in="0">—</span></div></div>
  <div className="tl-num"><div className="l">EMD</div><div className="v">—</div></div>
  <div className="tl-act"><button className="pmc-ib" aria-label="Follow"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg></button><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">View</a></div>
</article></div>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginTop: "16px" }}><span className="pmc-muted" style={{ fontSize: "13px" }}>No results</span><div style={{ display: "flex", gap: "6px" }}><button className="pmc-btn pmc-btn--secondary pmc-btn--sm" disabled>Previous</button><button className="pmc-btn pmc-btn--primary pmc-btn--sm">1</button><button className="pmc-btn pmc-btn--secondary pmc-btn--sm" disabled>Next</button></div></div>
  </section>
</div>
<footer className="pmc-chrome" style={{ padding: "40px 0 28px", marginTop: "0" }}><div className="pmc-wrap" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
  <div className="pmc-brand"><span className="pmc-brand__n" style={{ fontSize: "20px" }}>PMC Managers</span><span className="pmc-brand__s">Global Tender Grid</span></div><PmcSocialLinks />
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Tender notices</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Search by reference</b>Type a number like PMC-NOT-2026-… to jump straight to it.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Save a search</b>Get an email whenever a matching notice is published or amended.</div></div></div>
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
