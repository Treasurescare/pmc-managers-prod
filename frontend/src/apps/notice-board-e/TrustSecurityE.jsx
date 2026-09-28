import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function TrustSecurityE({ legacy: Legacy }) {
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
    <div data-testid="trust-security-e" data-pmc-e-page="trust-security-e">
<header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
  <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></a>
  <nav className="pmc-nav"><a href="#">Tenders</a><a href="#">How it works</a><a href="#">For suppliers</a><a href="#">For buyers</a><a href="#" className="is-on">Trust &amp; security</a><a href="#" data-help-open="">Help &amp; FAQs</a></nav>
  <div className="pmc-top__act"><button className="pmc-btn pmc-btn--onchrome pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-globe" /></svg> EN</button><a href="#" className="pmc-btn pmc-btn--onchrome">Sign in</a><a href="#" className="pmc-btn pmc-btn--brass">Register as supplier</a></div>
</div></header>
<section className="pmc-chrome" style={{ padding: "64px 0 72px" }}><div className="pmc-wrap" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "56px", alignItems: "center" }}>
  <div><div className="pmc-eyebrow">Trust &amp; security</div><h1 className="pmc-display" style={{ fontSize: "52px", lineHeight: "56px", margin: "10px 0 0px" }}>How we keep every tender honest</h1><p className="pmc-muted" style={{ fontSize: "18px", lineHeight: "30px", margin: "16px 0 24px" }}>Controls you can see, and a ledger anyone with audit rights can verify.</p>
  <div style={{ display: "flex", gap: "8px" }}><a href="#verify" className="pmc-btn pmc-btn--brass pmc-btn--lg"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg> Verify a record</a><a href="#" className="pmc-btn pmc-btn--onchrome pmc-btn--lg">Download security overview</a></div></div>
  <div className="pmc-panel" style={{ background: "var(--chrome-raised)", borderColor: "var(--chrome-line)", padding: "24px", color: "var(--on-chrome)" }}><div className="pmc-eyebrow">Ledger status</div><div style={{ display: "flex", alignItems: "baseline", gap: "12px", margin: "10px 0" }}><span className="pmc-figure" style={{ fontSize: "48px", lineHeight: "52px" }}>1,905</span><span className="pmc-muted">events · 0 breaks</span></div><div className="pmc-muted" style={{ fontSize: "14px" }}>Last full verification today 09:12 UTC · SHA-256 · append-only</div></div>
</div></section>
<div className="pmc-wrap" style={{ padding: "64px 0", display: "grid", gap: "48px" }}>
  <div className="tr-grid">
    <div className="pmc-panel tr-c"><span className="tr-n">01</span><h3>Sealed bidding</h3><p>Technical and commercial envelopes are sealed on upload. Nobody at PMC can open them before the deadline, and price opens only after technical scores are locked.</p></div>
    <div className="pmc-panel tr-c"><span className="tr-n">02</span><h3>Hash-chained ledger</h3><p>Every action is hashed with SHA-256 together with the previous action's hash. Altering any record breaks every link after it.</p></div>
    <div className="pmc-panel tr-c"><span className="tr-n">03</span><h3>Committees with quorum</h3><p>Evaluation needs a quorum, members score independently, and external advisers can be invited. Conflicts of interest are declared on the record.</p></div>
    <div className="pmc-panel tr-c"><span className="tr-n">04</span><h3>Escrowed EMD</h3><p>Earnest money goes to escrow with a step-by-step release trail: escrow, admin, certifier, legal, accounts.</p></div>
    <div className="pmc-panel tr-c"><span className="tr-n">05</span><h3>Strong sign-in</h3><p>Two-factor sign-in for staff, biometric sign-in on mobile, role-based access for every screen.</p></div>
    <div className="pmc-panel tr-c"><span className="tr-n">06</span><h3>Your data, your control</h3><p>Suppliers can export or delete their data. Documents are visible only to compliance and the relevant committee, and every view is logged.</p></div>
  </div>
  <section id="verify" className="pmc-card" style={{ display: "grid", gridTemplateColumns: "1fr 1fr", overflow: "hidden" }}>
    <div style={{ padding: "36px" }}><div className="pmc-eyebrow">Verify a record</div><h2 className="pmc-display" style={{ fontSize: "36px", lineHeight: "42px", margin: "8px 0 12px" }}>Check any notice, award or contract</h2><p className="pmc-muted" style={{ margin: "0 0 20px" }}>Enter a reference or ledger event number. We recompute its link to the chain and show the result.</p>
      <div style={{ display: "flex", gap: "8px" }}><label className="pmc-search" style={{ flex: "1", height: "48px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input value="PMC-AWD-2026-00025" /></label><button className="pmc-btn pmc-btn--primary pmc-btn--lg">Verify</button></div></div>
    <div style={{ padding: "36px", background: "var(--surface-sunken)", borderLeft: "1px solid var(--line)", display: "grid", gap: "12px", alignContent: "center" }}>
      <div className="pmc-callout pmc-callout--ok"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg><div><b>Record intact.</b> award.issue #1745 links correctly to #1744 and every event after it.</div></div>
      <div className="ad-code" style={{ fontFamily: "var(--font-mono)", fontSize: "12px", lineHeight: "19px", background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-sm)", padding: "12px 14px", whiteSpace: "pre" }}>event  #1745  award.issue
target PMC-AWD-2026-00025
prev   #1744  2b91…c04e
hash   #1745  f7a0…9d12   ✓ sha256(prev + payload)</div></div>
  </section>
  <section><h2 style={{ fontSize: "22px", margin: "0 0 12px" }}>Report a concern</h2><p className="pmc-muted" style={{ margin: "0 0 16px", maxWidth: "720px" }}>If you believe a tender has been compromised, tell us. Reports go to an independent compliance desk, not to the tender team.</p><a href="#" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg> Report a concern</a></section>
</div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Trust & security</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>What does ‘verify’ check?</b>It recomputes the record's SHA-256 link and every link after it; any change anywhere shows as a break.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="account"><summary>How do I keep my account secure?</summary><p>Turn on two-factor sign-in under <b>Account &rsaquo; Security</b>. On the mobile app you can also sign in with Face ID or fingerprint.</p></details></div>
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
