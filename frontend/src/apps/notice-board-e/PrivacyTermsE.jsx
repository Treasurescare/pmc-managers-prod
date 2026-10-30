import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { usePublicNav } from "@/lib/pmcEPublicNav";
import PmcSocialLinks from "@/components/PmcSocialLinks";

export default function PrivacyTermsE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
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
    <div data-testid="privacy-terms-e" data-pmc-e-page="privacy-terms-e">
<header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></a>
  <nav className="pmc-nav"><a href="#">Tenders</a><a href="#">How it works</a><a href="#">For suppliers</a><a href="#">For buyers</a><a href="#">Trust &amp; security</a><a href="#" data-help-open="">Help &amp; FAQs</a></nav>
  <div className="pmc-top__act"><button className="pmc-btn pmc-btn--onchrome pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-globe" /></svg> EN</button><a href="#" className="pmc-btn pmc-btn--onchrome">Sign in</a><a href="#" className="pmc-btn pmc-btn--brass">Register as supplier</a></div>
</div></header><div className="pmc-wrap" style={{ display: "grid", gridTemplateColumns: "240px minmax(0,760px)", gap: "56px", padding: "48px 0 72px" }}>
<nav style={{ position: "sticky", top: "96px", display: "grid", gap: "4px", alignContent: "start", fontSize: "14px" }} className="lg-nav"><a href="#" aria-current="page">Privacy notice</a><a href="#">Terms of use</a><a href="#">Supplier code of conduct</a><a href="#">Cookie notice</a><a href="#">Accessibility</a></nav>
<article><div className="pmc-eyebrow">Legal</div><h1 className="pmc-display" style={{ fontSize: "52px", lineHeight: "56px", margin: "10px 0 8px" }}>Privacy notice</h1><div className="pmc-muted" style={{ fontSize: "14px", marginBottom: "24px" }}>Version 1.0 · effective 1 Oct 2026 · <a href="#">Download PDF</a> · <a href="#">Previous versions</a></div>
<div className="pmc-callout pmc-callout--info" style={{ marginBottom: "28px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg><div><b>In short:</b> we use your data to run fair tenders and keep a verifiable record. You can export or delete it at any time, except what the law or open contracts require us to keep.</div></div>
<h2 style={{ fontSize: "22px", margin: "28px 0 8px" }}>1. What we collect</h2><p style={{ margin: "0", fontSize: "16px", lineHeight: "27px", color: "var(--ink-muted)" }}>Company details, contacts, KYC documents, bids, and sign-in and device records needed for security.</p><h2 style={{ fontSize: "22px", margin: "28px 0 8px" }}>2. Why we use it</h2><p style={{ margin: "0", fontSize: "16px", lineHeight: "27px", color: "var(--ink-muted)" }}>To verify suppliers, run tenders, evaluate bids, manage contracts, meet legal obligations and keep the audit ledger.</p><h2 style={{ fontSize: "22px", margin: "28px 0 8px" }}>3. Who can see it</h2><p style={{ margin: "0", fontSize: "16px", lineHeight: "27px", color: "var(--ink-muted)" }}>PMC compliance staff, and the evaluation committee of a tender you bid on. Every view is logged.</p><h2 style={{ fontSize: "22px", margin: "28px 0 8px" }}>4. How long we keep it</h2><p style={{ margin: "0", fontSize: "16px", lineHeight: "27px", color: "var(--ink-muted)" }}>For as long as your account is active, and afterwards only what law or the audit ledger requires, anonymised where possible.</p><h2 style={{ fontSize: "22px", margin: "28px 0 8px" }}>5. Your rights</h2><p style={{ margin: "0", fontSize: "16px", lineHeight: "27px", color: "var(--ink-muted)" }}>Access, correct, export or delete your data from Account &amp; security, or by contacting adminsupport@pmcmanagers.com.</p>
<div className="pmc-panel" style={{ marginTop: "32px", padding: "16px 20px", fontSize: "13px" }}><b>Placeholder text.</b> <span className="pmc-muted">Final wording to be supplied by PMC's legal counsel.</span></div></article></div>
<footer className="pmc-chrome" style={{ padding: "40px 0 28px", marginTop: "0" }}><div className="pmc-wrap" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
  <div className="pmc-brand"><span className="pmc-brand__n" style={{ fontSize: "20px" }}>PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></div><PmcSocialLinks />
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Privacy</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Short version first</b>Each legal page opens with a plain-language summary.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="account"><summary>How do I keep my account secure?</summary><p>Turn on two-factor sign-in under <b>Account &rsaquo; Security</b>. On the mobile app you can also sign in with Face ID or fingerprint.</p></details></div>
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
