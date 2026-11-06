import LangSwitcher from "@/apps/shared/LangSwitcher";

import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { usePublicNav } from "@/lib/pmcEPublicNav";
import { useSeo } from "@/lib/useSeo";
import PmcSocialLinks from "@/components/PmcSocialLinks";

export default function ForSuppliersE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  usePublicNav(isE);
  useSeo({ page: "suppliers" });
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
    <div data-testid="for-suppliers-e" data-pmc-e-page="for-suppliers-e">
<header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Grid</span></a>
  <nav className="pmc-nav"><a href="#">Tenders</a><a href="#">How it works</a><a href="#" className="is-on">For suppliers</a><a href="#">For buyers</a><a href="#">Trust &amp; security</a><a href="#" data-help-open="">Help &amp; FAQs</a></nav>
  <div className="pmc-top__act"><LangSwitcher dark /><a href="#" className="pmc-btn pmc-btn--onchrome">Sign in</a><a href="#" className="pmc-btn pmc-btn--brass">Register as supplier</a></div>
</div></header><section className="pmc-chrome" style={{ padding: "64px 0 72px" }}><div className="pmc-wrap" style={{ maxWidth: "1280px" }}><div className="pmc-eyebrow">For suppliers</div><h1 className="pmc-display" style={{ fontSize: "68px", lineHeight: "70px", margin: "12px 0 18px", color: "var(--on-chrome)", maxWidth: "900px" }}>Win international tenders on a grid that plays fair.</h1><p className="pmc-muted" style={{ fontSize: "18px", lineHeight: "30px", margin: "0 0 28px", maxWidth: "680px" }}>Any verified supplier, from any country, can bid on public tenders. Every bidder gets the same clarifications, the same deadline and a sealed envelope nobody can open early. After every decision, you get a debrief.</p><div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--brass pmc-btn--lg">Register as supplier</a><a href="#" className="pmc-btn pmc-btn--onchrome pmc-btn--lg">Browse open tenders</a></div></div></section>
<div className="pmc-wrap lf-sec"><div className="pmc-eyebrow">How it works</div><h2 className="lf-h">Four steps from sign-up to contract</h2><div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "16px" }}><div className="pmc-panel" style={{ padding: "24px" }}><div className="pmc-display" style={{ fontSize: "36px", color: "var(--brass-text)" }}>01</div><h3 style={{ margin: "8px 0 6px", fontSize: "17px" }}>Register once</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Company, contacts, categories and KYC documents. About 15 minutes; saves as you go.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><div className="pmc-display" style={{ fontSize: "36px", color: "var(--brass-text)" }}>02</div><h3 style={{ margin: "8px 0 6px", fontSize: "17px" }}>Get matched</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Tenders that fit your licences and categories arrive in your portal and inbox.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><div className="pmc-display" style={{ fontSize: "36px", color: "var(--brass-text)" }}>03</div><h3 style={{ margin: "8px 0 6px", fontSize: "17px" }}>Bid sealed</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Two envelopes, EMD to escrow or bank guarantee, a live tracker to the deadline.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><div className="pmc-display" style={{ fontSize: "36px", color: "var(--brass-text)" }}>04</div><h3 style={{ margin: "8px 0 6px", fontSize: "17px" }}>Sign and deliver</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Award, e-signature and contract milestones in the same place.</p></div></div></div>
<section style={{ background: "var(--surface-sunken)", borderTop: "1px solid var(--line)", borderBottom: "1px solid var(--line)" }}><div className="pmc-wrap lf-sec"><div className="pmc-eyebrow">What you get</div><h2 className="lf-h">Built so you spend time on the bid, not the portal</h2><div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "16px" }}><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-bell" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>Alerts that match you</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Only tenders your licences qualify for, plus every corrigendum on tenders you follow.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-lock" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>Sealed until the deadline</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Your price stays private until technical scores are locked.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-coin" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>EMD without chasing</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Pay to escrow or lodge a guarantee inside the bid; refunds tracked to the day.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-chart" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>A debrief every time</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Your score by criterion and your price position against L1.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-sign" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>Sign in the portal</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>DocuSign built in, including Face ID on the app.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-globe" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>Any country, any currency</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Bid in the tender's own currency, from anywhere.</p></div></div></div></section>
<div className="pmc-wrap lf-sec" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "48px", alignItems: "center" }}><div><h2 className="lf-h" style={{ marginTop: "0" }}>What do I need to register?</h2><ul style={{ margin: "0", paddingLeft: "20px", fontSize: "15px", lineHeight: "28px" }}><li>Certificate of incorporation and tax registration</li><li>Licences for the countries and categories you choose</li><li>ISO or equivalent certificates (if you have them)</li><li>An authorised signatory</li></ul><a href="#" data-help-open="" style={{ display: "inline-block", marginTop: "14px" }}>Read the KYC guide</a></div>
<div className="pmc-card" style={{ padding: "32px", textAlign: "center" }}><div className="pmc-display" style={{ fontSize: "32px", lineHeight: "36px" }}>Ready when you are</div><p className="pmc-muted">Public tenders are open to every verified supplier, whatever package you hold.</p><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--lg">Register as supplier</a></div></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · For suppliers</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Start with the KYC guide</b>It lists the documents by country and category.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="registration"><summary>How do I register as a supplier?</summary><p>Choose <b>Register as supplier</b>, enter your company details, then upload the KYC documents the form lists for your country and category. You can save and resume at any point. PMC reviews the file and you are notified when your KYC is approved.</p></details><details className="pmc-faq" data-cat="registration"><summary>Which documents does KYC need?</summary><p>The document list depends on your country and the licences your work category requires (for example, electrical or plumbing licences for Kazakhstan works packages). The registration form shows exactly which slots apply to you.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details></div>
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
