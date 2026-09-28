import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function ContactE({ legacy: Legacy }) {
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
    <div data-testid="contact-e" data-pmc-e-page="contact-e">
<header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></a>
  <nav className="pmc-nav"><a href="#">Tenders</a><a href="#">How it works</a><a href="#">For suppliers</a><a href="#">For buyers</a><a href="#">Trust &amp; security</a><a href="#" data-help-open="">Help &amp; FAQs</a></nav>
  <div className="pmc-top__act"><button className="pmc-btn pmc-btn--onchrome pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-globe" /></svg> EN</button><a href="#" className="pmc-btn pmc-btn--onchrome">Sign in</a><a href="#" className="pmc-btn pmc-btn--brass">Register as supplier</a></div>
</div></header><section className="pmc-chrome" style={{ padding: "48px 0 56px" }}><div className="pmc-wrap"><div className="pmc-eyebrow">Contact</div><h1 className="pmc-display" style={{ fontSize: "56px", lineHeight: "60px", margin: "10px 0 0", color: "var(--on-chrome)" }}>Talk to the right desk</h1></div></section>
<div className="pmc-wrap" style={{ padding: "40px 0 72px", display: "grid", gridTemplateColumns: "1fr 1fr", gap: "32px", alignItems: "start" }}>
<div style={{ display: "grid", gap: "12px" }}><div className="pmc-panel" style={{ padding: "20px", display: "grid", gridTemplateColumns: "40px 1fr", gap: "14px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-gavel" /></svg><div><b style={{ fontSize: "16px" }}>Tenders &amp; bids</b><div className="pmc-muted" style={{ fontSize: "14px", margin: "2px 0 6px" }}>Questions on a notice, clarifications, deadlines</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a></div></div><div className="pmc-panel" style={{ padding: "20px", display: "grid", gridTemplateColumns: "40px 1fr", gap: "14px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-lock" /></svg><div><b style={{ fontSize: "16px" }}>Account &amp; access</b><div className="pmc-muted" style={{ fontSize: "14px", margin: "2px 0 6px" }}>Sign-in, two-factor, locked accounts</div><a href="mailto:adminsupport@pmcmanagers.com">adminsupport@pmcmanagers.com</a></div></div><div className="pmc-panel" style={{ padding: "20px", display: "grid", gridTemplateColumns: "40px 1fr", gap: "14px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-chat" /></svg><div><b style={{ fontSize: "16px" }}>Signed-in users</b><div className="pmc-muted" style={{ fontSize: "14px", margin: "2px 0 6px" }}>Tickets are tracked in your portal</div><a href="#">Raise a ticket</a></div></div><div className="pmc-panel" style={{ padding: "20px", display: "grid", gridTemplateColumns: "40px 1fr", gap: "14px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-flag" /></svg><div><b style={{ fontSize: "16px" }}>Report a concern</b><div className="pmc-muted" style={{ fontSize: "14px", margin: "2px 0 6px" }}>Goes to an independent compliance desk</div><a href="#">Report a concern</a></div></div></div>
<form className="pmc-card" style={{ padding: "28px", display: "grid", gap: "14px" }}><h2 style={{ margin: "0", fontSize: "20px" }}>Send a message</h2>
<div className="pmc-field"><label>Topic</label><select className="pmc-input"><option>A specific tender</option><option>Registration &amp; KYC</option><option>Becoming a buyer</option><option>Something else</option></select></div>
<div className="pmc-field"><label>Tender reference (optional)</label><input className="pmc-input" placeholder="PMC-NOT-2026-…" /></div>
<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}><div className="pmc-field"><label>Name</label><input className="pmc-input" /></div><div className="pmc-field"><label>Work email</label><input className="pmc-input" /></div></div>
<div className="pmc-field"><label>Message</label><textarea className="pmc-input" style={{ height: "120px", padding: "10px" }}></textarea></div>
<div className="pmc-callout pmc-callout--info" style={{ fontSize: "13px", lineHeight: "20px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg><div>Questions about a tender's content are answered as clarifications to all bidders, not privately.</div></div>
<button className="pmc-btn pmc-btn--primary pmc-btn--lg">Send message</button></form></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Contact</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Search first</b>Most questions are answered in the Help Centre.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="registration"><summary>How do I register as a supplier?</summary><p>Choose <b>Register as supplier</b>, enter your company details, then upload the KYC documents the form lists for your country and category. You can save and resume at any point. PMC reviews the file and you are notified when your KYC is approved.</p></details><details className="pmc-faq" data-cat="registration"><summary>Which documents does KYC need?</summary><p>The document list depends on your country and the licences your work category requires (for example, electrical or plumbing licences for Kazakhstan works packages). The registration form shows exactly which slots apply to you.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details></div>
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
