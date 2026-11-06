import LangSwitcher from "@/apps/shared/LangSwitcher";

import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { usePublicNav } from "@/lib/pmcEPublicNav";
import { useSeo } from "@/lib/useSeo";
import GlobalPresence from "@/apps/notice-board-e/GlobalPresence";
import PmcSocialLinks from "@/components/PmcSocialLinks";

export default function AboutVisionE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  usePublicNav(isE);
  useSeo({ page: window.location.pathname.startsWith("/vision") ? "vision" : "about" });
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
    <div data-testid="about-vision-e" data-pmc-e-page="about-vision-e">
<header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Grid</span></a>
  <nav className="pmc-nav"><a href="#">Tenders</a><a href="#">How it works</a><a href="#">For suppliers</a><a href="#">For buyers</a><a href="#">Trust &amp; security</a><a href="#" data-help-open="">Help &amp; FAQs</a></nav>
  <div className="pmc-top__act"><LangSwitcher dark /><a href="#" className="pmc-btn pmc-btn--onchrome">Sign in</a><a href="#" className="pmc-btn pmc-btn--brass">Register as supplier</a></div>
</div></header>
<section className="pmc-chrome" style={{ padding: "72px 0 88px", position: "relative", overflow: "hidden" }}><div className="pmc-wrap" style={{ display: "grid", gridTemplateColumns: "1.1fr .9fr", gap: "64px", alignItems: "end" }}>
  <div><div className="pmc-eyebrow">About PMC Managers</div><h1 className="pmc-display" style={{ fontSize: "80px", lineHeight: "80px", margin: "14px 0 20px", color: "var(--on-chrome)" }}>Procurement people can <em style={{ color: "var(--brass-on-chrome)" }}>trust.</em></h1>
  <p className="pmc-muted" style={{ fontSize: "18px", lineHeight: "30px", margin: "0", maxWidth: "600px" }}>PMC Managers runs project management and procurement for large public, institutional and private programmes around the world, with offices in the United Kingdom and Malaysia and new offices opening in India, the United States and Kazakhstan. The Global Tender Grid is how those programmes buy: in the open, on the record.</p></div>
  <div className="pmc-panel" style={{ background: "var(--chrome-raised)", borderColor: "var(--chrome-line)", padding: "28px", color: "var(--on-chrome)" }}><div className="pmc-eyebrow">Our vision</div><p className="pmc-display" style={{ fontSize: "30px", lineHeight: "38px", margin: "10px 0 0" }}>“Every public tender, anywhere, run so that anyone can check how it was decided.”</p></div>
</div></section>
<div className="pmc-wrap" style={{ padding: "72px 0" }}>
  <div className="pmc-eyebrow">What we stand for</div><h2 className="pmc-display" style={{ fontSize: "44px", lineHeight: "48px", margin: "10px 0 28px" }}>Four commitments</h2>
  <div className="ab-vals"><div className="ab-v"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg><h3>Integrity by design</h3><p>Sealed envelopes, committees with quorum and an append-only ledger remove the chance to bend the process.</p></div><div className="ab-v"><svg className="pmc-ico" aria-hidden="true"><use href="#i-globe" /></svg><h3>Open to the world</h3><p>Suppliers from any country can register, qualify and bid, in the tender's own currency.</p></div><div className="ab-v"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><h3>Speed without shortcuts</h3><p>AI drafts notices from project reports and checks bids for anomalies, so people spend time on judgement.</p></div><div className="ab-v"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg><h3>Fair to every bidder</h3><p>Every clarification reaches every bidder. Every bidder sees their own score after award.</p></div></div>
</div>
<section style={{ background: "var(--surface-sunken)", borderTop: "1px solid var(--line)", borderBottom: "1px solid var(--line)", padding: "72px 0" }}><div className="pmc-wrap" style={{ display: "grid", gridTemplateColumns: ".8fr 1.2fr", gap: "56px" }}>
  <div><div className="pmc-eyebrow">What we do</div><h2 className="pmc-display" style={{ fontSize: "44px", lineHeight: "48px", margin: "10px 0 16px" }}>From project report to signed contract</h2><p className="pmc-muted" style={{ fontSize: "16px", lineHeight: "26px" }}>We act as project management consultant for the programme owner: packaging the work, running the tenders, evaluating fairly and managing contracts to completion.</p></div>
  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
    <div className="pmc-panel" style={{ padding: "22px" }}><b>Programme packaging</b><p className="pmc-muted" style={{ fontSize: "14px", lineHeight: "22px", margin: "6px 0 0" }}>Breaking each programme into clear work packages that suppliers can price and deliver.</p></div>
    <div className="pmc-panel" style={{ padding: "22px" }}><b>Tendering</b><p className="pmc-muted" style={{ fontSize: "14px", lineHeight: "22px", margin: "6px 0 0" }}>Notices, clarifications, corrigenda and sealed bidding.</p></div>
    <div className="pmc-panel" style={{ padding: "22px" }}><b>Evaluation</b><p className="pmc-muted" style={{ fontSize: "14px", lineHeight: "22px", margin: "6px 0 0" }}>Committees with quorum and independent external advisers.</p></div>
    <div className="pmc-panel" style={{ padding: "22px" }}><b>Contract management</b><p className="pmc-muted" style={{ fontSize: "14px", lineHeight: "22px", margin: "6px 0 0" }}>Awards, e-signature, milestones and payments.</p></div>
  </div></div></section>
<GlobalPresence />
<div className="pmc-wrap" style={{ padding: "72px 0", display: "grid", gridTemplateColumns: "1fr auto", gap: "32px", alignItems: "center" }}>
  <div><h2 className="pmc-display" style={{ fontSize: "40px", lineHeight: "44px", margin: "0 0 8px" }}>Work with us</h2><p className="pmc-muted" style={{ margin: "0", fontSize: "16px" }}>Suppliers: register and get matched tenders. Programme owners: talk to us about running your procurement.</p></div>
  <div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--lg">Register as supplier</a><a href="mailto:tenders@pmcmanagers.com" className="pmc-btn pmc-btn--secondary pmc-btn--lg"><svg className="pmc-ico" aria-hidden="true"><use href="#i-mail" /></svg> Contact PMC</a></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · About</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Looking for tenders?</b>Open Tenders in the top bar to see every open notice.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="registration"><summary>How do I register as a supplier?</summary><p>Choose <b>Register as supplier</b>, enter your company details, then upload the KYC documents the form lists for your country and category. You can save and resume at any point. PMC reviews the file and you are notified when your KYC is approved.</p></details><details className="pmc-faq" data-cat="registration"><summary>Which documents does KYC need?</summary><p>The document list depends on your country and the licences your work category requires (for example, electrical or plumbing licences for Kazakhstan works packages). The registration form shows exactly which slots apply to you.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details></div>
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
