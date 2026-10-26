import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function MobilePublicE({ legacy: Legacy }) {
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
    <div data-testid="mobile-public-e" data-pmc-e-page="mobile-public-e">
<div className="mw"><div><div className="phone"><div className="scr"><div className="sb chrome-top"><span>9:41</span><span style={{ fontSize: "12px" }}>●●● 5G ▮</span></div><div className="chrome-top" style={{ padding: "6px 16px 22px", flex: "none" }}><div className="mrow"><div><div style={{ fontFamily: "var(--font-display)", fontSize: "20px", fontWeight: "600" }}>PMC Managers</div><div className="pmc-eyebrow" style={{ fontSize: "10px" }}>Global Tender Board</div></div><span style={{ fontSize: "22px" }}>☰</span></div>
<div className="pmc-display" style={{ fontSize: "44px", lineHeight: "44px", margin: "22px 0 12px" }}>Tenders you can <em style={{ color: "var(--brass-on-chrome)" }}>prove.</em></div>
<p style={{ margin: "0 0 16px", color: "var(--on-chrome-muted)", fontSize: "15px", lineHeight: "23px" }}>Sealed bids, time-stamped decisions, one platform.</p>
<label className="pmc-search" style={{ height: "48px", background: "var(--surface)", borderColor: "var(--surface)" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Keyword or reference" style={{ color: "var(--ink)" }} /></label>
<div style={{ display: "flex", gap: "6px", marginTop: "10px", overflow: "hidden" }}><span className="pmc-chip" style={{ whiteSpace: "nowrap" }}>Closing this week</span><span className="pmc-chip" style={{ whiteSpace: "nowrap" }}>Civil works</span><span className="pmc-chip" style={{ whiteSpace: "nowrap" }}>Medical</span></div></div>
<div className="mbody" style={{ paddingTop: "16px" }}><div className="mrow"><b>Closing soon</b><a href="#" style={{ fontSize: "13px" }}>View all</a></div>
<a href="#" className="pmc-btn pmc-btn--primary mbtn">Register as supplier</a></div><span className="mfab" style={{ bottom: "22px" }}>?</span></div></div><div className="cap">Public home<span>Search-first hero, closing soon, register</span></div></div><div><div className="phone"><div className="scr"><div className="sb"><span>9:41</span><span style={{ fontSize: "12px" }}>●●● 5G ▮</span></div><div className="mtop"><div className="t"><b>Tender notices</b><small>Live board</small></div><button className="pmc-btn pmc-btn--secondary pmc-btn--sm">Filters</button></div>
<div style={{ padding: "0 16px 10px", flex: "none" }}><label className="pmc-search" style={{ height: "44px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Keyword or reference" /></label></div>
<div style={{ display: "flex", gap: "6px", padding: "0 16px 12px", flex: "none", overflow: "hidden" }}><span className="pmc-chip" aria-pressed="true" style={{ whiteSpace: "nowrap" }}>Open</span><span className="pmc-chip" style={{ whiteSpace: "nowrap" }}>Tender</span><span className="pmc-chip" style={{ whiteSpace: "nowrap" }}>RFP</span><span className="pmc-chip" style={{ whiteSpace: "nowrap" }}>RFQ</span></div>
<div className="mbody"></div><nav className="tab"><a href="#" className=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a><a href="#" className="on"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Tenders</a><a href="#" className=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>Bids</a><a href="#" className=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg>Alerts</a><a href="#" className=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Account</a></nav></div></div><div className="cap">Tender notices<span>Search, filter chips, compact cards</span></div></div><div><div className="phone"><div className="scr"><div className="sb chrome-top"><span>9:41</span><span style={{ fontSize: "12px" }}>●●● 5G ▮</span></div><div className="chrome-top" style={{ padding: "24px 20px 28px", flex: "none" }}><div style={{ fontFamily: "var(--font-display)", fontSize: "22px", fontWeight: "600" }}>PMC Managers</div><div className="pmc-display" style={{ fontSize: "34px", lineHeight: "38px", marginTop: "22px" }}>Welcome back.</div></div>
<div className="mbody" style={{ paddingTop: "20px" }}>
<div className="pmc-seg" style={{ display: "grid", gridTemplateColumns: "1fr 1fr 1fr" }}><button aria-selected="true" style={{ padding: "10px 4px" }}>Supplier</button><button aria-selected="false" style={{ padding: "10px 4px" }}>Staff</button><button aria-selected="false" style={{ padding: "10px 4px" }}>Admin</button></div>
<button className="pmc-btn pmc-btn--primary mbtn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-eye" /></svg> Sign in with Face ID</button>
<div style={{ textAlign: "center", fontSize: "13px" }} className="pmc-muted">or use email</div>
<input className="pmc-input" placeholder="Work email" style={{ height: "48px", width: "100%" }} />
<input className="pmc-input" type="password" defaultValue="••••••••" readOnly style={{ height: "48px", width: "100%" }} />
<button className="pmc-btn pmc-btn--secondary mbtn">Continue</button>
<div style={{ textAlign: "center", fontSize: "13px" }}><a href="#">Forgot password?</a> · <a href="#">Register</a></div></div></div></div><div className="cap">Sign in<span>Biometric first, email as fallback</span></div></div><div><div className="phone"><div className="scr"><div className="sb"><span>9:41</span><span style={{ fontSize: "12px" }}>●●● 5G ▮</span></div><div className="mtop"><div className="t"><b>Alerts</b><small>You're all caught up</small></div><a href="#" style={{ fontSize: "13px" }}>Mark all read</a></div>
<div className="mbody"></div><nav className="tab"><a href="#" className=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a><a href="#" className=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Tenders</a><a href="#" className=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>Bids</a><a href="#" className="on"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg>Alerts</a><a href="#" className=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Account</a></nav></div></div><div className="cap">Alerts<span>Action alerts first, one tap to the step</span></div></div></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Mobile — public</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Help on mobile</b>The round ? button opens this panel on every screen.</div></div></div>
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
