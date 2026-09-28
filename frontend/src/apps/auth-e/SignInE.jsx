import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function SignInE({ legacy: Legacy }) {
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
  return (
    <div data-testid="sign-in-e" data-pmc-e-page="sign-in-e">
<div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) minmax(0,1fr)", minHeight: "100vh" }}>
<section className="pmc-chrome" style={{ position: "relative", overflow: "hidden", padding: "48px 64px", display: "flex", flexDirection: "column" }}>
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></a>
  <svg viewBox="0 0 400 400" style={{ position: "absolute", right: "-140px", top: "120px", width: "560px", height: "560px", opacity: ".55" }} aria-hidden="true"><circle cx="200" cy="200" r="188" fill="none" stroke="var(--chrome-line)" /><circle cx="200" cy="200" r="140" fill="none" stroke="var(--brass-on-chrome)" /><circle cx="200" cy="200" r="92" fill="none" stroke="var(--chrome-line)" /></svg>
  <div style={{ marginTop: "auto", position: "relative", maxWidth: "520px" }}>
    <div className="pmc-eyebrow">Welcome back</div>
    <h1 className="pmc-display" style={{ fontSize: "64px", lineHeight: "64px", margin: "12px 0 16px", color: "var(--on-chrome)" }}>Pick up exactly <em style={{ color: "var(--brass-on-chrome)" }}>where you left off.</em></h1>
    <p className="pmc-muted" style={{ fontSize: "17px", lineHeight: "28px", margin: "0 0 28px" }}>Your drafts, sealed envelopes and deadlines are waiting. Every sign-in is recorded on the audit ledger.</p>
    <div style={{ display: "grid", gap: "10px", fontSize: "14px" }}><div style={{ display: "flex", gap: "10px", alignItems: "center" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>Two-factor sign-in for every staff account</div><div style={{ display: "flex", gap: "10px", alignItems: "center" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Face ID or fingerprint on the mobile app</div><div style={{ display: "flex", gap: "10px", alignItems: "center" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>Sign-in events chained to the ledger</div></div>
  </div>
</section>
<section style={{ display: "grid", placeItems: "center", padding: "48px" }}>
  <div style={{ width: "440px", maxWidth: "100%" }}>
    <h2 style={{ fontSize: "28px", lineHeight: "34px", margin: "0 0 6px" }}>Sign in</h2><p className="pmc-muted" style={{ margin: "0 0 24px" }}>New supplier? <a href="#">Register in about 15 minutes</a></p>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><label className="pmc-radio on" style={{ padding: "14px 16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg><div><b>Supplier</b><div className="pmc-muted" style={{ fontSize: "13px" }}>Bid, pay EMD, sign contracts</div></div></label><label className="pmc-radio" style={{ padding: "14px 16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg><div><b>PMC staff</b><div className="pmc-muted" style={{ fontSize: "13px" }}>Tender desk, evaluation, escrow</div></div></label><label className="pmc-radio" style={{ padding: "14px 16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg><div><b>Administrator</b><div className="pmc-muted" style={{ fontSize: "13px" }}>Configuration and audit</div></div></label></div>
    <div style={{ display: "grid", gap: "14px" }}>
      <div className="pmc-field"><label>Work email</label><input className="pmc-input" placeholder="name@company.com" style={{ height: "44px" }} /></div>
      <div className="pmc-field"><div style={{ display: "flex", justifyContent: "space-between" }}><label>Password</label><a href="#" style={{ fontSize: "13px" }}>Forgot password?</a></div><input className="pmc-input" type="password" value="••••••••••••" style={{ height: "44px" }} /></div>
      <label className="pmc-check" style={{ padding: "0" }}><input type="checkbox" checked />Keep me signed in on this device for 12 hours</label>
      <button className="pmc-btn pmc-btn--primary pmc-btn--lg" style={{ width: "100%" }}>Continue</button>
    </div>
    <div className="pmc-panel" style={{ marginTop: "24px", padding: "18px" }}>
      <div className="pmc-eyebrow" style={{ color: "var(--ink-muted)" }}>Step 2 of 2 · verify it's you</div>
      <div style={{ fontWeight: "600", margin: "6px 0 12px" }}>Enter the 6-digit code from your authenticator app</div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(6,1fr)", gap: "8px" }}><input className="pmc-input" value="4" style={{ height: "52px", width: "100%", minWidth: "0", padding: "0", textAlign: "center", fontFamily: "var(--font-mono)", fontSize: "22px" }} /><input className="pmc-input" value="8" style={{ height: "52px", width: "100%", minWidth: "0", padding: "0", textAlign: "center", fontFamily: "var(--font-mono)", fontSize: "22px" }} /><input className="pmc-input" value="2" style={{ height: "52px", width: "100%", minWidth: "0", padding: "0", textAlign: "center", fontFamily: "var(--font-mono)", fontSize: "22px" }} /><input className="pmc-input" value="9" style={{ height: "52px", width: "100%", minWidth: "0", padding: "0", textAlign: "center", fontFamily: "var(--font-mono)", fontSize: "22px" }} /><input className="pmc-input" value=" " style={{ height: "52px", width: "100%", minWidth: "0", padding: "0", textAlign: "center", fontFamily: "var(--font-mono)", fontSize: "22px" }} /><input className="pmc-input" value=" " style={{ height: "52px", width: "100%", minWidth: "0", padding: "0", textAlign: "center", fontFamily: "var(--font-mono)", fontSize: "22px" }} /></div>
      <div className="pmc-muted" style={{ fontSize: "13px", marginTop: "10px" }}>Lost your device? <a href="#">Use a backup code</a> or <a href="#">contact adminsupport@pmcmanagers.com</a></div>
    </div>
    <div className="pmc-muted" style={{ fontSize: "12px", marginTop: "24px", display: "flex", justifyContent: "space-between" }}><span>© 2026 PMC Managers Limited</span><span><a href="#" data-help-open="">Help</a> · <a href="#">Privacy</a></span></div>
  </div>
</section></div>

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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Sign in</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Choose your role first</b>Suppliers, PMC staff and administrators each land in their own workspace.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Locked out?</b>After 5 failed attempts the account locks for 15 minutes; contact adminsupport@pmcmanagers.com to unlock sooner.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="registration"><summary>How do I register as a supplier?</summary><p>Choose <b>Register as supplier</b>, enter your company details, then upload the KYC documents the form lists for your country and category. You can save and resume at any point. PMC reviews the file and you are notified when your KYC is approved.</p></details><details className="pmc-faq" data-cat="registration"><summary>Which documents does KYC need?</summary><p>The document list depends on your country and the licences your work category requires (for example, electrical or plumbing licences for Kazakhstan works packages). The registration form shows exactly which slots apply to you.</p></details><details className="pmc-faq" data-cat="account"><summary>How do I keep my account secure?</summary><p>Turn on two-factor sign-in under <b>Account &rsaquo; Security</b>. On the mobile app you can also sign in with Face ID or fingerprint.</p></details></div>
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
