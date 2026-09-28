import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function RegistrationE({ legacy: Legacy }) {
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
    <div data-testid="registration-e" data-pmc-e-page="registration-e">
<header className="pmc-chrome" style={{ borderBottom: "1px solid var(--chrome-line)" }}><div className="pmc-wrap" style={{ display: "flex", alignItems: "center", height: "64px", gap: "24px" }}>
  <a href="#" className="pmc-brand"><span className="pmc-brand__n" style={{ fontSize: "22px" }}>PMC Managers</span><span className="pmc-brand__s">Supplier registration</span></a>
  <span className="pmc-muted" style={{ marginLeft: "auto", fontSize: "13px", display: "flex", gap: "8px", alignItems: "center" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg> Saved 2 min ago · resume link sent to your email</span>
  <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button><a href="#" className="pmc-btn pmc-btn--onchrome">Save &amp; exit</a></div></header>
<div className="pmc-wrap" style={{ display: "grid", gridTemplateColumns: "280px minmax(0,1fr) 300px", gap: "32px", padding: "36px 0 72px", alignItems: "start" }}>
  <nav className="pmc-steplist" aria-label="Registration steps" style={{ position: "sticky", top: "24px" }}>
    <div className="pmc-eyebrow" style={{ margin: "0 0 8px 12px" }}>Step 4 of 5 · about 5 min left</div>
    <a href="#" className="done"><span className="d">✓</span><span>Company<small>Emerald Corporates Ltd · UK</small></span></a>
    <a href="#" className="done"><span className="d">✓</span><span>Contacts &amp; signatories<small>2 people</small></span></a>
    <a href="#" className="done"><span className="d">✓</span><span>Categories &amp; countries<small>Civil &amp; MEP, Medical supply · KZ, IN</small></span></a>
    <a href="#" className="now"><span className="d">4</span><span>KYC documents<small>3 of 5 required uploaded</small></span></a>
    <a href="#"><span className="d">5</span><span>Review &amp; submit<small>Declarations and e-signature</small></span></a>
    <div style={{ height: "6px", background: "var(--surface-sunken)", borderRadius: "3px", margin: "12px 12px 0", overflow: "hidden" }}><i style={{ display: "block", width: "70%", height: "100%", background: "var(--primary)" }}></i></div>
  </nav>
  <main>
    <h1 className="pmc-display" style={{ fontSize: "40px", lineHeight: "44px", margin: "0 0 8px" }}>KYC documents</h1>
    <p className="pmc-muted" style={{ margin: "0 0 20px", fontSize: "16px", lineHeight: "26px" }}>Based on your countries and categories, you need <b style={{ color: "var(--ink)" }}>5 required documents</b>. Upload once; they are reused on every bid you make.</p>
    <div className="pmc-drop" style={{ marginBottom: "20px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg><b style={{ color: "var(--ink)" }}>Drop files here or browse</b><span style={{ fontSize: "13px" }}>PDF, JPG or PNG up to 25 MB each. We match each file to its slot; you can re-assign it.</span></div>
    <div className="pmc-panel"><div className="pmc-docrow"><span className="i" style={{ background: "var(--success-soft)", color: "var(--success)" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg></span><div><b>Certificate of incorporation</b><span className="s">emerald-incorporation.pdf · 1.1 MB</span></div><span className="pmc-pill pmc-pill--success">Uploaded</span><button className="pmc-btn pmc-btn--ghost pmc-btn--sm">Replace</button></div><div className="pmc-docrow"><span className="i" style={{ background: "var(--success-soft)", color: "var(--success)" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg></span><div><b>Tax registration (BIN / GSTIN / VAT)</b><span className="s">tax-certificate.pdf · 640 KB</span></div><span className="pmc-pill pmc-pill--success">Uploaded</span><button className="pmc-btn pmc-btn--ghost pmc-btn--sm">Replace</button></div><div className="pmc-docrow"><span className="i" style={{ background: "var(--success-soft)", color: "var(--success)" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg></span><div><b>ISO 9001 certificate</b><span className="s">iso9001-2025.pdf · 820 KB · expires 14 Mar 2028</span></div><span className="pmc-pill pmc-pill--success">Uploaded</span><button className="pmc-btn pmc-btn--ghost pmc-btn--sm">Replace</button></div><div className="pmc-docrow"><span className="i" style=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg></span><div><b>Licence — Electrical installation (KZ)</b><span className="s">Required for Kazakhstan civil &amp; MEP works</span></div><span className="pmc-pill pmc-pill--warning">Required</span><button className="pmc-btn pmc-btn--secondary pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Upload</button></div><div className="pmc-docrow"><span className="i" style=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg></span><div><b>Licence — Plumbing &amp; firefighting (KZ)</b><span className="s">Required for Kazakhstan civil &amp; MEP works</span></div><span className="pmc-pill pmc-pill--warning">Required</span><button className="pmc-btn pmc-btn--secondary pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Upload</button></div><div className="pmc-docrow"><span className="i" style=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg></span><div><b>Bank reference letter</b><span className="s">Optional · speeds up EMD refunds</span></div><span className="pmc-pill">Optional</span><button className="pmc-btn pmc-btn--secondary pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Upload</button></div></div>
    <div className="pmc-callout pmc-callout--warn" style={{ marginTop: "16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg><div><b>No Kazakhstan licences yet?</b> You can still register. Add a licensed local partner on bids that need these segments, or upload the licences later from <b>Company &amp; KYC</b>.</div></div>
    <div style={{ display: "flex", justifyContent: "space-between", marginTop: "28px" }}><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--lg">Back</a><div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--lg">Skip optional for now</a><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--lg" aria-disabled="true">Continue to review</a></div></div>
  </main>
  <aside style={{ display: "grid", gap: "16px", position: "sticky", top: "24px" }}>
    <div className="pmc-panel" style={{ padding: "20px" }}><b style={{ fontSize: "15px" }}>Why we ask for these</b><p className="pmc-muted" style={{ fontSize: "14px", lineHeight: "22px", margin: "8px 0 0" }}>Buyers on the Kazakhstan programme must confirm every supplier's legal status and licences before award. Verified once here, you skip this on each bid.</p></div>
    <div className="pmc-panel" style={{ padding: "20px" }}><b style={{ fontSize: "15px" }}>What happens next</b><div className="pmc-timeline" style={{ marginTop: "14px" }}><div className="now"><span className="dot"></span><div><b>You submit</b><span>Today</span></div></div><div><span className="dot"></span><div><b>PMC reviews your file</b><span>You'll be told if anything is missing</span></div></div><div><span className="dot"></span><div><b>KYC approved</b><span>Matched tenders start arriving</span></div></div></div></div>
    <div className="pmc-panel" style={{ padding: "20px" }}><b style={{ fontSize: "15px" }}>Your data</b><p className="pmc-muted" style={{ fontSize: "14px", lineHeight: "22px", margin: "8px 0 0" }}>Documents are visible only to PMC compliance and evaluation committees. You can export or delete your data at any time.</p></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Registration · KYC documents</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Which licences do I need?</b>The list follows the countries and categories you chose in step 3. Change them there to update this list.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Leave and come back</b>Everything saves automatically; the resume link is in your inbox.</div></div></div>
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
