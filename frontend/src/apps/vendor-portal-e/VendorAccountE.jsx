import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { useVendorAccountLive } from "@/lib/pmcELiveData";

export default function VendorAccountE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useVendorAccountLive({ enabled: isE });
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
    <div data-testid="vendor-account-e" data-pmc-e-page="vendor-account-e">
<header className="pmc-chrome pmc-vtop">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Supplier portal</span></a>
  <label className="pmc-search pmc-cmd"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, documents…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-vtop__r">
    <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-iconbtn pmc-bell" aria-label="9 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">9</span></button>
    <button className="pmc-who" aria-haspopup="menu"><span className="pmc-avatar">EC</span><span className="pmc-who__t"><b>Emerald Corporates</b><span>PMC-SUP-000017 · KYC verified</span></span></button>
  </div>
</header><div className="pmc-app"><nav className="pmc-lnav" aria-label="Supplier"><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Home</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>Find tenders<span className="c">29</span></a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>My bids<span className="c hot">1</span></a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>EMD &amp; payments</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>Signatures<span className="c">1</span></a><hr /><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Company &amp; KYC</a><a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Reviews</a><a href="#" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-settings" /></svg>Account &amp; security</a><a href="#" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs</a><div className="pmc-desk"><b>Your PMC desk</b><div className="pmc-muted">Questions on a tender or bid?</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm" style={{ width: "100%", marginTop: "10px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a></div></nav><main className="pmc-main"><div className="sp-head"><div><div className="pmc-eyebrow">Account &amp; security</div><h1>Your account</h1></div></div>
<div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "16px" }}>
  <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">Sign-in &amp; two-factor</h2><span className="pmc-pill pmc-pill--success">Protected</span></div><div className="pmc-panel__body" style={{ display: "grid", gap: "14px", fontSize: "14px" }}>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}><div><b>Password</b><div className="pmc-muted" style={{ fontSize: "13px" }}>Changed 12 Aug 2026</div></div><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Change</a></div>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}><div><b>Authenticator app</b><div className="pmc-muted" style={{ fontSize: "13px" }}>On · required for signing and payments</div></div><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Manage</a></div>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}><div><b>Face ID / fingerprint</b><div className="pmc-muted" style={{ fontSize: "13px" }}>On for the PMC Tenders app</div></div><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Manage</a></div>
    <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}><div><b>Backup codes</b><div className="pmc-muted" style={{ fontSize: "13px" }}>8 of 10 unused</div></div><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">View</a></div></div></section>
  <section className="pmc-panel"><div className="pmc-panel__head"><h2 className="pmc-panel__title">Notifications</h2></div><div className="pmc-panel__body" style={{ display: "grid", gap: "4px" }}>
    <label className="pmc-check" style={{ justifyContent: "space-between" }}><span>New tenders matching my KYC</span><span style={{ display: "flex", gap: "16px" }}><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" checked />Portal</span><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" checked />Email</span></span></label><label className="pmc-check" style={{ justifyContent: "space-between" }}><span>Clarifications &amp; corrigenda on followed tenders</span><span style={{ display: "flex", gap: "16px" }}><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" checked />Portal</span><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" checked />Email</span></span></label><label className="pmc-check" style={{ justifyContent: "space-between" }}><span>Deadline reminders (72h, 24h, 2h)</span><span style={{ display: "flex", gap: "16px" }}><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" checked />Portal</span><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" checked />Email</span></span></label><label className="pmc-check" style={{ justifyContent: "space-between" }}><span>EMD and escrow updates</span><span style={{ display: "flex", gap: "16px" }}><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" checked />Portal</span><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" checked />Email</span></span></label><label className="pmc-check" style={{ justifyContent: "space-between" }}><span>Documents to sign</span><span style={{ display: "flex", gap: "16px" }}><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" checked />Portal</span><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" checked />Email</span></span></label><label className="pmc-check" style={{ justifyContent: "space-between" }}><span>Weekly digest</span><span style={{ display: "flex", gap: "16px" }}><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" checked />Portal</span><span style={{ display: "flex", gap: "6px", alignItems: "center", fontSize: "13px" }}><input type="checkbox" />Email</span></span></label></div></section>
</div>
<section className="pmc-panel" style={{ marginTop: "16px" }}><div className="pmc-panel__head"><h2 className="pmc-panel__title">Where you're signed in</h2><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Sign out everywhere else</a></div><table className="pmc-table"><tbody><tr><td style={{ fontWeight: "600" }}>Chrome · Windows</td><td>London, UK</td><td><span className="pmc-pill pmc-pill--brand">This device</span></td><td className="pmc-muted">now</td><td style={{ textAlign: "right" }}></td></tr><tr><td style={{ fontWeight: "600" }}>PMC Tenders app · iPhone</td><td>London, UK</td><td><span className="pmc-pill pmc-pill--brand">Face ID</span></td><td className="pmc-muted">2 h ago</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">Sign out</a></td></tr><tr><td style={{ fontWeight: "600" }}>Safari · macOS</td><td>Chennai, IN</td><td></td><td className="pmc-muted">3 days ago</td><td style={{ textAlign: "right" }}><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm">Sign out</a></td></tr></tbody></table></section>
<section className="pmc-panel" style={{ marginTop: "16px", borderColor: "var(--danger)" }}><div className="pmc-panel__head"><h2 className="pmc-panel__title" style={{ color: "var(--danger)" }}>Delete my data</h2></div><div className="pmc-panel__body" style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "24px", alignItems: "center" }}>
  <p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Deletes your company profile, documents and team. Records that must be kept for active bids, contracts or the audit ledger are retained and anonymised. You'll be asked to type your company name and confirm with two-factor.</p>
  <div style={{ display: "flex", gap: "8px" }}><a href="#" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Export first</a><a href="#" className="pmc-btn pmc-btn--danger">Delete my data…</a></div></div></section></main></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Account & security</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Two-factor protects money</b>Signing and payment actions always ask for your code.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Lost device</b>Use a backup code, then sign that device out here.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="account"><summary>How do I keep my account secure?</summary><p>Turn on two-factor sign-in under <b>Account &rsaquo; Security</b>. On the mobile app you can also sign in with Face ID or fingerprint.</p></details></div>
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
