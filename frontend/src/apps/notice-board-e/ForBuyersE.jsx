import LangSwitcher from "@/apps/shared/LangSwitcher";

import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { usePublicNav } from "@/lib/pmcEPublicNav";
import { useSeo } from "@/lib/useSeo";
import PmcSocialLinks from "@/components/PmcSocialLinks";

export default function ForBuyersE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  usePublicNav(isE);
  useSeo({ page: "buyers" });
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
    <div data-testid="for-buyers-e" data-pmc-e-page="for-buyers-e">
<header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Grid</span></a>
  <nav className="pmc-nav"><a href="#">Tenders</a><a href="#">How it works</a><a href="#">For suppliers</a><a href="#" className="is-on">For buyers</a><a href="#">Trust &amp; security</a><a href="#" data-help-open="">Help &amp; FAQs</a></nav>
  <div className="pmc-top__act"><LangSwitcher dark /><a href="#" className="pmc-btn pmc-btn--onchrome">Sign in</a><a href="#" className="pmc-btn pmc-btn--brass">Register as supplier</a></div>
</div></header><section className="pmc-chrome" style={{ padding: "64px 0 72px" }}><div className="pmc-wrap" style={{ maxWidth: "1280px" }}><div className="pmc-eyebrow">For buyers &amp; programme owners</div><h1 className="pmc-display" style={{ fontSize: "68px", lineHeight: "70px", margin: "12px 0 18px", color: "var(--on-chrome)", maxWidth: "900px" }}>Run procurement you can defend line by line.</h1><p className="pmc-muted" style={{ fontSize: "18px", lineHeight: "30px", margin: "0 0 28px", maxWidth: "680px" }}>From a detailed project report to a signed contract, with every step sealed, time-stamped and verifiable by your auditors.</p><div style={{ display: "flex", gap: "8px" }}><a href="mailto:tenders@pmcmanagers.com" className="pmc-btn pmc-btn--brass pmc-btn--lg">Talk to PMC</a><a href="#" className="pmc-btn pmc-btn--onchrome pmc-btn--lg">See how it works</a></div></div></section>
<div className="pmc-wrap lf-sec"><div className="pmc-eyebrow">The platform</div><h2 className="lf-h">Everything between the DPR and the last milestone</h2><div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "16px" }}><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-spark" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>AI tender builder</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Draft a complete notice from a DPR, with every field linked to its source page.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-users" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>Committees with quorum</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Independent scoring, external advisers, conflicts declared on record.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-chart" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>L1 and anomaly checks</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Qualified bids ranked against the estimate; outliers flagged before award.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-coin" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>Escrowed EMD</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Six-step release trail from escrow to accounts.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-layers" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>Contracts &amp; milestones</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>Payments released only on certified milestones.</p></div><div className="pmc-panel" style={{ padding: "24px" }}><svg className="pmc-ico lf-i" aria-hidden="true"><use href="#i-link" /></svg><h3 style={{ margin: "14px 0 6px", fontSize: "17px" }}>Audit ledger</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>SHA-256 hash chain over every action, verifiable in one click.</p></div></div></div>
<section className="pmc-chrome" data-testid="buyers-how"><div className="pmc-wrap lf-sec"><div className="pmc-eyebrow">How a tender runs</div><h2 className="lf-h" style={{ color: "var(--on-chrome)" }}>Seven stages, one sealed record</h2><div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "20px" }}>{[["01", "Draft", "Upload the project report; the builder drafts the notice, criteria, fees and EMD."], ["02", "Publish", "Choose public or private. Public tenders are open to every verified supplier."], ["03", "Clarify & bid", "Answers and corrigenda reach every bidder; bids stay sealed to the deadline."], ["04", "Evaluate & award", "Committees score first, prices open second, award is e-signed and tracked."]].map(([n, t, d]) => (<div key={n}><div className="pmc-figure" style={{ fontSize: "40px", lineHeight: "44px" }}>{n}</div><div style={{ fontWeight: 600, margin: "6px 0 4px" }}>{t}</div><div className="pmc-muted" style={{ fontSize: "14px", lineHeight: "22px" }}>{d}</div></div>))}</div></div></section>
<div className="pmc-wrap lf-sec"><div className="pmc-eyebrow">Who it is for</div><h2 className="lf-h">Built for programmes that must answer to someone</h2><div style={{ display: "grid", gridTemplateColumns: "repeat(3,1fr)", gap: "16px" }}>{[["Governments & public bodies", "Open, auditable procurement that lenders and auditors can verify."], ["Development & infrastructure programmes", "Many work packages, many countries, one record of every decision."], ["Private companies & EPC contractors", "Private tenders to invited suppliers, run on the same sealed, audited process."]].map(([t, d]) => (<div key={t} className="pmc-panel" style={{ padding: "24px" }}><h3 style={{ margin: "0 0 6px", fontSize: "17px" }}>{t}</h3><p className="pmc-muted" style={{ margin: "0", fontSize: "14px", lineHeight: "22px" }}>{d}</p></div>))}</div><p style={{ marginTop: "20px" }}><a href="/contact" className="pmc-btn pmc-btn--secondary" data-testid="buyers-contact-link">Talk to the tender desk</a></p></div>
<div className="pmc-wrap lf-sec" style={{ textAlign: "center" }}><h2 className="lf-h">Bring your programme</h2><p className="pmc-muted" style={{ margin: "-8px 0 20px" }}>Tell us about your packages and timeline; we'll show you the platform on your own data.</p><a href="mailto:tenders@pmcmanagers.com" className="pmc-btn pmc-btn--primary pmc-btn--lg"><svg className="pmc-ico" aria-hidden="true"><use href="#i-mail" /></svg> tenders@pmcmanagers.com</a></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · For buyers</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>See the controls</b>Trust &amp; security lists every control in plain words.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details></div>
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
