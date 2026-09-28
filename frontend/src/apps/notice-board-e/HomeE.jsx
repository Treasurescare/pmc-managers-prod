import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function HomeE({ legacy: Legacy }) {
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
    <div data-testid="home-e" data-pmc-e-page="home-e">
<div className="pmc-site">
<header className="pmc-chrome pmc-top">
  <div className="pmc-wrap pmc-top__in">
    <a href="#" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></a>
    <nav className="pmc-nav"><a href="#">Tenders</a><a href="#how">How it works</a><a href="#" className="is-on">For suppliers</a><a href="#">For buyers</a><a href="#trust">Trust &amp; security</a><a href="#help" data-help-open="">Help &amp; FAQs</a></nav>
    <div className="pmc-top__act"><button className="pmc-btn pmc-btn--onchrome pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-globe" /></svg> EN</button><a href="#" className="pmc-btn pmc-btn--onchrome">Sign in</a><a href="#" className="pmc-btn pmc-btn--brass">Register as supplier</a></div>
  </div>
</header>

<section className="pmc-chrome pmc-hero">
  <svg className="pmc-seal" viewBox="0 0 400 400" aria-hidden="true"><defs><path id="ring" d="M200,200 m-160,0 a160,160 0 1,1 320,0 a160,160 0 1,1 -320,0" /></defs>
    <circle cx="200" cy="200" r="188" className="s1" /><circle cx="200" cy="200" r="132" className="s1" />
    <text className="st"><textPath href="#ring">SEALED · TIME-STAMPED · SHA-256 CHAINED · VERIFIABLE · SEALED · TIME-STAMPED · SHA-256 CHAINED · VERIFIABLE ·</textPath></text></svg>
  <div className="pmc-wrap pmc-hero__in">
    <div>
      <a href="#" className="pmc-livechip"><span className="dot"></span>29 tenders open for bids now <svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></a>
      <h1 className="pmc-display pmc-hero__h">Tenders you<br />can <em>prove.</em></h1>
      <p className="pmc-hero__p">Publish, clarify, receive sealed bids, evaluate and award on one platform. Every action is time-stamped and chained to an audit ledger, so every decision can be shown.</p>
      <form className="pmc-hero__search">
        <label className="pmc-search" style={{ flex: "1", height: "52px", background: "var(--surface)", borderColor: "var(--surface)" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search by keyword, buyer or reference no." style={{ color: "var(--ink)" }} /></label>
        <select className="pmc-input" style={{ height: "52px", width: "170px" }} aria-label="Country"><option>All countries</option><option>Kazakhstan</option><option>India</option></select>
        <button className="pmc-btn pmc-btn--brass pmc-btn--lg" style={{ height: "52px" }}>Find tenders</button>
      </form>
      <div style={{ display: "flex", gap: "8px", alignItems: "center", flexWrap: "wrap", marginTop: "14px" }}><span className="pmc-muted" style={{ fontSize: "13px" }}>Popular:</span><a className="pmc-chip" href="#">Closing this week</a><a className="pmc-chip" href="#">Civil works &amp; MEP</a><a className="pmc-chip" href="#">Medical equipment</a><a className="pmc-chip" href="#">IT &amp; digital health</a></div>
    </div>
    <div className="pmc-live">
      <div className="pmc-live__h"><span className="pmc-eyebrow">Live board · closing first</span><span className="pmc-livedot">Live</span></div>
      <a href="#" className="pmc-live__row"><div><div className="pmc-ref">PMC-NOT-2026-0055 · Kazakhstan</div><div className="pmc-live__t">Turnkey IVF Laboratory Setup — Embryology Lab, Cryopreservation & Cleanroom HVAC</div></div><span className="pmc-countdown" data-in="52">—</span></a><a href="#" className="pmc-live__row"><div><div className="pmc-ref">PMC-NOT-2026-0054 · Kazakhstan</div><div className="pmc-live__t">Birth Suites — Linen, Consumables & Newborn Care Kits (Annual Rate Contract)</div></div><span className="pmc-countdown" data-in="57">—</span></a><a href="#" className="pmc-live__row"><div><div className="pmc-ref">PMC-NOT-2026-0038 · India</div><div className="pmc-live__t">Supply & Installation of OPD Queue Management & Digital Signage System</div></div><span className="pmc-countdown" data-in="83">—</span></a><a href="#" className="pmc-live__row"><div><div className="pmc-ref">PMC-NOT-2026-0037 · Kazakhstan</div><div className="pmc-live__t">Outpatient Department (OPD) Building Renovation & MEP Upgrade — Block C</div></div><span className="pmc-countdown" data-in="270">—</span></a>
      <a href="#" className="pmc-live__all">See all 29 open notices <svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></a>
    </div>
  </div>
</section>

<section className="pmc-stats pmc-wrap" aria-label="Platform in numbers">
  <div><div className="pmc-figure">29</div><div className="pmc-muted">notices open for bids</div></div>
  <div><div className="pmc-figure">76</div><div className="pmc-muted">approved suppliers</div></div>
  <div><div className="pmc-figure">50</div><div className="pmc-muted">work packages in the Kazakhstan programme</div></div>
  <div><div className="pmc-figure">1,905</div><div className="pmc-muted">actions on the audit ledger, none altered</div></div>
</section>

<section className="pmc-wrap" style={{ padding: "72px 0 0" }}>
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", marginBottom: "24px" }}>
    <div><div className="pmc-eyebrow">Closing soon</div><h2 className="pmc-display" style={{ fontSize: "40px", lineHeight: "44px", margin: "8px 0 0" }}>Open for bids this week</h2></div>
    <div style={{ display: "flex", gap: "8px" }}><button className="pmc-chip" aria-pressed="true">All</button><button className="pmc-chip">Tender</button><button className="pmc-chip">RFP</button><button className="pmc-chip">RFQ</button><a href="#" className="pmc-btn pmc-btn--secondary" style={{ marginLeft: "8px" }}>Browse all notices <svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></a></div>
  </div>
  <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "20px" }}><article className="pmc-tender">
  <div className="pmc-tender__top"><span className="pmc-tag">TENDER</span><span className="pmc-ref">PMC-NOT-2026-0055</span><span style={{ marginLeft: "auto" }} className="pmc-countdown" data-in="52">—</span></div>
  <h3 className="pmc-tender__title">Turnkey IVF Laboratory Setup — Embryology Lab, Cryopreservation & Cleanroom HVAC</h3>
  <dl className="pmc-tender__meta" style={{ margin: "0" }}><div className="is-budget"><dt>Indicative budget</dt><dd>USD 2,100,000</dd></div><div><dt>Delivery</dt><dd>Kazakhstan</dd></div><div><dt>Category</dt><dd style={{ fontWeight: "500" }}>Civil Works & MEP</dd></div></dl>
  <div className="pmc-tender__foot"><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ paddingLeft: "0" }}>View notice <svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></a><span className="pmc-pill pmc-pill--info">Corrigendum 1</span></div>
</article><article className="pmc-tender">
  <div className="pmc-tender__top"><span className="pmc-tag">RFQ</span><span className="pmc-ref">PMC-NOT-2026-0054</span><span style={{ marginLeft: "auto" }} className="pmc-countdown" data-in="57">—</span></div>
  <h3 className="pmc-tender__title">Birth Suites — Linen, Consumables & Newborn Care Kits (Annual Rate Contract)</h3>
  <dl className="pmc-tender__meta" style={{ margin: "0" }}><div className="is-budget"><dt>Indicative budget</dt><dd>KZT 88,000,000</dd></div><div><dt>Delivery</dt><dd>Kazakhstan</dd></div><div><dt>Category</dt><dd style={{ fontWeight: "500" }}>Consumables & Implants</dd></div></dl>
  <div className="pmc-tender__foot"><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ paddingLeft: "0" }}>View notice <svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></a></div>
</article><article className="pmc-tender">
  <div className="pmc-tender__top"><span className="pmc-tag">RFP</span><span className="pmc-ref">PMC-NOT-2026-0038</span><span style={{ marginLeft: "auto" }} className="pmc-countdown" data-in="83">—</span></div>
  <h3 className="pmc-tender__title">Supply & Installation of OPD Queue Management & Digital Signage System</h3>
  <dl className="pmc-tender__meta" style={{ margin: "0" }}><div className="is-budget"><dt>Indicative budget</dt><dd>INR 62,000,000</dd></div><div><dt>Delivery</dt><dd>India</dd></div><div><dt>Category</dt><dd style={{ fontWeight: "500" }}>IT & Digital Health</dd></div></dl>
  <div className="pmc-tender__foot"><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ paddingLeft: "0" }}>View notice <svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></a></div>
</article><article className="pmc-tender">
  <div className="pmc-tender__top"><span className="pmc-tag">TENDER</span><span className="pmc-ref">PMC-NOT-2026-0037</span><span style={{ marginLeft: "auto" }} className="pmc-countdown" data-in="270">—</span></div>
  <h3 className="pmc-tender__title">Outpatient Department (OPD) Building Renovation & MEP Upgrade — Block C</h3>
  <dl className="pmc-tender__meta" style={{ margin: "0" }}><div className="is-budget"><dt>Indicative budget</dt><dd>KZT 850,000,000</dd></div><div><dt>Delivery</dt><dd>Kazakhstan</dd></div><div><dt>Category</dt><dd style={{ fontWeight: "500" }}>Civil Works & MEP</dd></div></dl>
  <div className="pmc-tender__foot"><a href="#" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ paddingLeft: "0" }}>View notice <svg className="pmc-ico" aria-hidden="true"><use href="#i-arrow" /></svg></a></div>
</article></div>
</section>

<div id="how"><section className="pmc-wrap" style={{ padding: "88px 0 40px" }}>
  <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "48px", alignItems: "end", marginBottom: "36px" }}>
    <div><div className="pmc-eyebrow">How it works</div><h2 className="pmc-display" style={{ fontSize: "52px", lineHeight: "56px", margin: "10px 0 0" }}>From draft to signed contract,<br />on one sealed record.</h2></div>
    <p style={{ margin: "0", color: "var(--ink-muted)", fontSize: "17px", lineHeight: "28px" }}>Seven stages, one platform. Pick a stage to see what happens there and what proof it leaves behind.</p>
  </div>
  <div className="pmc-stages" role="tablist"><button className="pmc-stage" role="tab" aria-selected="false" data-stage="0"><span className="pmc-stage__n">I</span><span className="pmc-stage__l">Draft</span></button><button className="pmc-stage" role="tab" aria-selected="false" data-stage="1"><span className="pmc-stage__n">II</span><span className="pmc-stage__l">Publish</span></button><button className="pmc-stage" role="tab" aria-selected="false" data-stage="2"><span className="pmc-stage__n">III</span><span className="pmc-stage__l">Clarify</span></button><button className="pmc-stage" role="tab" aria-selected="true" data-stage="3"><span className="pmc-stage__n">IV</span><span className="pmc-stage__l">Bid</span></button><button className="pmc-stage" role="tab" aria-selected="false" data-stage="4"><span className="pmc-stage__n">V</span><span className="pmc-stage__l">Evaluate</span></button><button className="pmc-stage" role="tab" aria-selected="false" data-stage="5"><span className="pmc-stage__n">VI</span><span className="pmc-stage__l">Compare</span></button><button className="pmc-stage" role="tab" aria-selected="false" data-stage="6"><span className="pmc-stage__n">VII</span><span className="pmc-stage__l">Award</span></button></div>
  <div className="pmc-card" style={{ display: "grid", gridTemplateColumns: "1.1fr .9fr", gap: "0", marginTop: "20px", overflow: "hidden" }}>
    <div style={{ padding: "40px" }}><div className="pmc-stagepanel" data-panel="0" hidden>
  <div className="pmc-eyebrow">Stage I · Draft</div>
  <h3 className="pmc-display" style={{ fontSize: "36px", lineHeight: "42px", margin: "8px 0 12px" }}>AI tender builder</h3>
  <p style={{ margin: "0 0 20px", color: "var(--ink-muted)", fontSize: "16px", lineHeight: "26px", maxWidth: "520px" }}>Upload a DPR and the builder drafts the notice, covers, fees and EMD in minutes. Start from master templates or clone a past tender. Every draft is versioned.</p>
  <div className="pmc-proof"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><span>Written to the ledger as</span><code className="pmc-ref" style={{ color: "var(--ink)" }}>Version history · v2</code></div>
</div><div className="pmc-stagepanel" data-panel="1" hidden>
  <div className="pmc-eyebrow">Stage II · Publish</div>
  <h3 className="pmc-display" style={{ fontSize: "36px", lineHeight: "42px", margin: "8px 0 12px" }}>Global notice board</h3>
  <p style={{ margin: "0 0 20px", color: "var(--ink-muted)", fontSize: "16px", lineHeight: "26px", maxWidth: "520px" }}>One click publishes to the public board with a reference number, delivery country and deadline. Suppliers whose KYC matches are alerted at once.</p>
  <div className="pmc-proof"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><span>Written to the ledger as</span><code className="pmc-ref" style={{ color: "var(--ink)" }}>notice.publish · #1872</code></div>
</div><div className="pmc-stagepanel" data-panel="2" hidden>
  <div className="pmc-eyebrow">Stage III · Clarify</div>
  <h3 className="pmc-display" style={{ fontSize: "36px", lineHeight: "42px", margin: "8px 0 12px" }}>Clarifications & corrigenda</h3>
  <p style={{ margin: "0 0 20px", color: "var(--ink-muted)", fontSize: "16px", lineHeight: "26px", maxWidth: "520px" }}>Suppliers ask questions in the portal; answers and corrigenda go to every bidder with an effective date, so no one bids on stale terms.</p>
  <div className="pmc-proof"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><span>Written to the ledger as</span><code className="pmc-ref" style={{ color: "var(--ink)" }}>corrigendum.issue · #1880</code></div>
</div><div className="pmc-stagepanel" data-panel="3">
  <div className="pmc-eyebrow">Stage IV · Bid</div>
  <h3 className="pmc-display" style={{ fontSize: "36px", lineHeight: "42px", margin: "8px 0 12px" }}>Sealed two-envelope bids</h3>
  <p style={{ margin: "0 0 20px", color: "var(--ink-muted)", fontSize: "16px", lineHeight: "26px", maxWidth: "520px" }}>Technical and commercial envelopes are sealed until the deadline. EMD is paid to escrow or lodged as a bank guarantee inside the bid.</p>
  <div className="pmc-proof"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><span>Written to the ledger as</span><code className="pmc-ref" style={{ color: "var(--ink)" }}>bid.seal · #1891</code></div>
</div><div className="pmc-stagepanel" data-panel="4" hidden>
  <div className="pmc-eyebrow">Stage V · Evaluate</div>
  <h3 className="pmc-display" style={{ fontSize: "36px", lineHeight: "42px", margin: "8px 0 12px" }}>Committees with quorum</h3>
  <p style={{ margin: "0 0 20px", color: "var(--ink-muted)", fontSize: "16px", lineHeight: "26px", maxWidth: "520px" }}>Form a committee, invite independent external evaluators, and score technically before any price is opened. The AI anomaly check flags outlier bids.</p>
  <div className="pmc-proof"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><span>Written to the ledger as</span><code className="pmc-ref" style={{ color: "var(--ink)" }}>committee.form · #1895</code></div>
</div><div className="pmc-stagepanel" data-panel="5" hidden>
  <div className="pmc-eyebrow">Stage VI · Compare</div>
  <h3 className="pmc-display" style={{ fontSize: "36px", lineHeight: "42px", margin: "8px 0 12px" }}>L1 commercial comparison</h3>
  <p style={{ margin: "0 0 20px", color: "var(--ink-muted)", fontSize: "16px", lineHeight: "26px", maxWidth: "520px" }}>Commercial envelopes open side by side with the lowest evaluated bid ranked first, in each bid's own currency.</p>
  <div className="pmc-proof"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><span>Written to the ledger as</span><code className="pmc-ref" style={{ color: "var(--ink)" }}>envelope.open · #1899</code></div>
</div><div className="pmc-stagepanel" data-panel="6" hidden>
  <div className="pmc-eyebrow">Stage VII · Award</div>
  <h3 className="pmc-display" style={{ fontSize: "36px", lineHeight: "42px", margin: "8px 0 12px" }}>Award & e-signature</h3>
  <p style={{ margin: "0 0 20px", color: "var(--ink-muted)", fontSize: "16px", lineHeight: "26px", maxWidth: "520px" }}>Award letters, POs and contracts go out for DocuSign signature, in the portal or by email. Contracts and milestones stay tracked after award.</p>
  <div className="pmc-proof"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><span>Written to the ledger as</span><code className="pmc-ref" style={{ color: "var(--ink)" }}>contract.sign · #1905</code></div>
</div></div>
    <div style={{ background: "var(--surface-sunken)", borderLeft: "1px solid var(--line)", padding: "32px", display: "flex", flexDirection: "column", justifyContent: "center", gap: "10px" }} aria-hidden="true">
      <div className="pmc-eyebrow" style={{ color: "var(--ink-muted)" }}>Bid PMC-BID-2026-00020</div>
      <div className="pmc-mini"><span className="d ok">✓</span>Eligibility <em>Done</em></div>
      <div className="pmc-mini"><span className="d ok">✓</span>Technical envelope sealed <em>Done</em></div>
      <div className="pmc-mini"><span className="d ok">✓</span>Commercial envelope sealed <em>Done</em></div>
      <div className="pmc-mini now"><span className="d">IV</span>EMD in escrow <em>Awaiting escrow</em></div>
      <div className="pmc-mini"><span className="d">V</span>Review, sign &amp; seal <em>Next</em></div>
    </div>
  </div>
</section></div>

<section className="pmc-wrap" style={{ padding: "48px 0 88px" }}>
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", gap: "24px", marginBottom: "28px" }}>
    <div><div className="pmc-eyebrow">Built for both sides of the table</div><h2 className="pmc-display" style={{ fontSize: "52px", lineHeight: "56px", margin: "10px 0 0" }}>Less paperwork. More proof.</h2></div>
    <div className="pmc-seg" role="tablist"><button role="tab" aria-selected="true" data-aud="s">For suppliers</button><button role="tab" aria-selected="false" data-aud="b">For buyers &amp; PMC teams</button></div>
  </div>
  <div className="pmc-feats" data-audp="s"><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg></div><h3>One KYC, every tender</h3><p>Register once. Your approved profile and licences are reused on every bid, and tenders that match them come to you.</p></div><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg></div><h3>Alerts that match you</h3><p>New notices, clarifications and corrigenda for your categories reach you in the portal and by email.</p></div><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg></div><h3>Sealed until the deadline</h3><p>Technical and commercial envelopes stay sealed until the deadline. Nobody sees your price early.</p></div><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg></div><h3>EMD without the chase</h3><p>Pay to escrow or lodge a bank guarantee inside the bid, and see receipt confirmed on the tracker.</p></div><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg></div><h3>Sign where you bid</h3><p>Award letters, POs and contracts are signed with DocuSign inside the portal.</p></div><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-eye" /></svg></div><h3>Always know where you stand</h3><p>A five-step tracker and a live countdown on every bid. No calls needed to find out what is next.</p></div></div>
  <div className="pmc-feats" data-audp="b" hidden><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg></div><h3>AI tender builder</h3><p>Generate a complete notice from a DPR, or clone from master templates and BOQs. Versioned, printable, bilingual.</p></div><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg></div><h3>Committees with quorum</h3><p>Internal members plus invited external advisers, quorum rules, and a full record of who scored what.</p></div><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chart" /></svg></div><h3>L1 comparison</h3><p>Commercial bids ranked side by side once technical scoring is locked.</p></div><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg></div><h3>AI bid anomaly check</h3><p>Flags outlier prices and unusual patterns before you award.</p></div><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg></div><h3>Escrow, billing & contracts</h3><p>EMD escrow, billing, awards, contracts and milestones in one pipeline.</p></div><div className="pmc-feat"><div className="pmc-feat__i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg></div><h3>Hash-chained audit ledger</h3><p>Every action is SHA-256 chained to the one before. Verify the whole chain in one click.</p></div></div>
</section>

<section id="trust" className="pmc-chrome" style={{ padding: "88px 0" }}>
  <div className="pmc-wrap" style={{ display: "grid", gridTemplateColumns: ".8fr 1.2fr", gap: "64px", alignItems: "center" }}>
    <div>
      <div className="pmc-eyebrow">Trust &amp; security</div>
      <h2 className="pmc-display" style={{ fontSize: "52px", lineHeight: "56px", margin: "10px 0 16px" }}>Change one record and the chain breaks.</h2>
      <p className="pmc-muted" style={{ fontSize: "17px", lineHeight: "28px", margin: "0 0 28px" }}>Each action is hashed with SHA-256 together with the hash of the action before it. Anyone with audit rights can re-verify the whole ledger in one click.</p>
      <ul className="pmc-trust">
        <li><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg>Two-factor sign-in for staff; Face ID or fingerprint on mobile</li>
        <li><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Role-based access for admins, staff, committees and suppliers</li>
        <li><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>EMD held in escrow, with a step-by-step release trail</li>
        <li><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>DocuSign e-signature for awards, POs and contracts</li>
        <li><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>Suppliers can export or delete their data on request</li>
      </ul>
    </div>
    <div>
      <div className="pmc-chain"><div className="pmc-block"><div className="pmc-ref">#1901</div><div style={{ fontWeight: "600", fontSize: "14px" }}>contract.create</div><div className="pmc-ref">contract:026-0015</div><div className="pmc-hash">a073daa591aa…</div></div><div className="pmc-chainlink" aria-hidden="true"></div><div className="pmc-block"><div className="pmc-ref">#1902</div><div style={{ fontWeight: "600", fontSize: "14px" }}>staff.login</div><div className="pmc-ref">admin_user:11774096</div><div className="pmc-hash">ffbc139cfc78…</div></div><div className="pmc-chainlink" aria-hidden="true"></div><div className="pmc-block"><div className="pmc-ref">#1903</div><div style={{ fontWeight: "600", fontSize: "14px" }}>vendor.login</div><div className="pmc-ref">vendor:64943c36</div><div className="pmc-hash">3e724c7a456a…</div></div><div className="pmc-chainlink" aria-hidden="true"></div><div className="pmc-block"><div className="pmc-ref">#1904</div><div style={{ fontWeight: "600", fontSize: "14px" }}>staff.login</div><div className="pmc-ref">admin_user:11774096</div><div className="pmc-hash">b082d43c664b…</div></div><div className="pmc-chainlink" aria-hidden="true"></div><div className="pmc-block"><div className="pmc-ref">#1905</div><div style={{ fontWeight: "600", fontSize: "14px" }}>staff.login</div><div className="pmc-ref">admin_user:11774096</div><div className="pmc-hash">98f1a4880023…</div></div></div>
      <div style={{ display: "flex", alignItems: "center", gap: "16px", marginTop: "24px" }}><span className="pmc-verified"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg> Chain verified · 1,905 of 1,905 records intact</span><span className="pmc-ref">SHA-256 · append-only</span></div>
    </div>
  </div>
</section>

<section className="pmc-wrap" style={{ padding: "88px 0" }}>
  <div style={{ display: "grid", gridTemplateColumns: ".9fr 1.1fr", gap: "56px", alignItems: "start" }}>
    <div>
      <div className="pmc-eyebrow">Programme spotlight</div>
      <h2 className="pmc-display" style={{ fontSize: "48px", lineHeight: "52px", margin: "10px 0 16px" }}>Kazakhstan Integrated Development Programme</h2>
      <p className="pmc-muted" style={{ fontSize: "17px", lineHeight: "28px", margin: "0 0 24px" }}>Modular medical, education, hostel and utilities packages, published for global supply. Suppliers from any country can register, qualify and bid.</p>
      <div style={{ display: "flex", gap: "12px" }}><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--lg">See programme tenders</a><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--lg">Download the brief</a></div>
    </div>
    <div className="pmc-cats"><a href="#" className="pmc-cat"><svg className="pmc-ico" aria-hidden="true"><use href="#i-box" /></svg><div><h3>Modular medical</h3><p>Hospitals, OPD blocks, IVF and cleanroom labs, medical equipment and consumables.</p></div><svg className="pmc-ico pmc-cat__go" aria-hidden="true"><use href="#i-arrow" /></svg></a><a href="#" className="pmc-cat"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg><div><h3>Education</h3><p>University academic packages, digital learning and campus fit-out.</p></div><svg className="pmc-ico pmc-cat__go" aria-hidden="true"><use href="#i-arrow" /></svg></a><a href="#" className="pmc-cat"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg><div><h3>Hostels & residential</h3><p>Student and staff hostels, modular residential blocks.</p></div><svg className="pmc-ico pmc-cat__go" aria-hidden="true"><use href="#i-arrow" /></svg></a><a href="#" className="pmc-cat"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg><div><h3>Utilities & infrastructure</h3><p>Power, water, networks and site infrastructure.</p></div><svg className="pmc-ico pmc-cat__go" aria-hidden="true"><use href="#i-arrow" /></svg></a></div>
  </div>
</section>

<section className="pmc-start">
  <div className="pmc-wrap">
    <div style={{ textAlign: "center", maxWidth: "720px", margin: "0 auto 40px" }}><div className="pmc-eyebrow">For suppliers</div><h2 className="pmc-display" style={{ fontSize: "48px", lineHeight: "52px", margin: "10px 0 0" }}>Ready to bid in three steps</h2></div>
    <ol className="pmc-steps">
      <li><span className="n">1</span><h3>Register &amp; complete KYC</h3><p>Company details and the documents your country and category need. Save and come back any time.</p></li>
      <li><span className="n">2</span><h3>Get matched tenders</h3><p>Once approved, notices that fit your licences and categories come to your portal and inbox.</p></li>
      <li><span className="n">3</span><h3>Bid sealed, track live</h3><p>Submit both envelopes, pay EMD, and follow every step to signature.</p></li>
    </ol>
    <div style={{ display: "flex", justifyContent: "center", gap: "12px", marginTop: "36px" }}><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--lg">Register as supplier</a><button className="pmc-btn pmc-btn--secondary pmc-btn--lg" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-play" /></svg> Take the 2-minute tour</button></div>
  </div>
</section>

<section id="help" className="pmc-wrap" style={{ padding: "88px 0" }}>
  <div style={{ display: "grid", gridTemplateColumns: ".8fr 1.2fr", gap: "64px" }}>
    <div>
      <div className="pmc-eyebrow">Help &amp; FAQs</div>
      <h2 className="pmc-display" style={{ fontSize: "48px", lineHeight: "52px", margin: "10px 0 16px" }}>Answers first, calls last.</h2>
      <p className="pmc-muted" style={{ margin: "0 0 24px", fontSize: "16px", lineHeight: "26px" }}>Search the most asked questions, or open help from any screen with the <b>Help</b> button or the <span className="pmc-kbd">?</span> key.</p>
      <div className="pmc-contact">
        <a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg><div><b>Help Centre</b><span>Guides for suppliers and buyers</span></div></a>
        <a href="#"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg><div><b>Raise a ticket</b><span>Tracked in your portal</span></div></a>
        <a href="mailto:tenders@pmcmanagers.com"><svg className="pmc-ico" aria-hidden="true"><use href="#i-mail" /></svg><div><b>tenders@pmcmanagers.com</b><span>Tender and bid questions</span></div></a>
      </div>
    </div>
    <div>
      <label className="pmc-search" style={{ height: "52px", marginBottom: "8px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input data-faq-q="homefaq" placeholder="Type a question, e.g. “withdraw my bid”" /></label>
      <div id="homefaq"><details className="pmc-faq" data-cat="registration" open><summary>How do I register as a supplier?</summary><p>Choose <b>Register as supplier</b>, enter your company details, then upload the KYC documents the form lists for your country and category. You can save and resume at any point. PMC reviews the file and you are notified when your KYC is approved.</p></details><details className="pmc-faq" data-cat="registration"><summary>Which documents does KYC need?</summary><p>The document list depends on your country and the licences your work category requires (for example, electrical or plumbing licences for Kazakhstan works packages). The registration form shows exactly which slots apply to you.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details><details className="pmc-faq" data-cat="emd"><summary>What is EMD and how do I pay it?</summary><p>The Earnest Money Deposit secures your bid. Each tender sets it as a fixed amount or a percentage. Pay it from the bid tracker by transfer to escrow or by uploading a bank guarantee. Escrow confirms receipt before your bid moves on.</p></details></div>
      <p id="homefaq-empty" hidden className="pmc-muted">Nothing matches yet. Try the Help Centre or raise a ticket.</p>
    </div>
  </div>
</section>

<footer className="pmc-chrome" style={{ padding: "56px 0 32px" }}>
  <div className="pmc-wrap">
    <div style={{ display: "grid", gridTemplateColumns: "1.4fr 1fr 1fr 1fr 1fr", gap: "32px", paddingBottom: "40px", borderBottom: "1px solid var(--chrome-line)" }}>
      <div><div className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></div><p className="pmc-muted" style={{ margin: "16px 0 0", fontSize: "14px", lineHeight: "22px", maxWidth: "300px" }}>e-Tender platform for admins, staff and suppliers. Bid, evaluate, award — from any device.</p></div>
      <div className="pmc-fcol"><b>Tenders</b><a href="#">Open notices</a><a href="#">Completed</a><a href="#">Corrigenda</a><a href="#">Programme</a></div>
      <div className="pmc-fcol"><b>Suppliers</b><a href="#">Register</a><a href="#">Sign in</a><a href="#">KYC guide</a><a href="#">EMD &amp; escrow</a></div>
      <div className="pmc-fcol"><b>Company</b><a href="#">About us</a><a href="#">Vision</a><a href="#">Trust &amp; security</a><a href="#">Contact</a></div>
      <div className="pmc-fcol"><b>Help</b><a href="#">Help Centre</a><a href="#">FAQs</a><a href="#">Raise a ticket</a><a href="#">Privacy</a></div>
    </div>
    <div style={{ display: "flex", justifyContent: "space-between", paddingTop: "24px", fontSize: "13px" }} className="pmc-muted"><span>© 2026 PMC Managers Limited</span><span>Install the app: add PMC Tenders to your home screen</span></div>
  </div>
</footer>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Homepage</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Find a tender fast</b>Search by keyword or reference number, or pick a popular category under the search bar.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>New supplier?</b>Register once; your KYC is reused on every bid.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="registration"><summary>How do I register as a supplier?</summary><p>Choose <b>Register as supplier</b>, enter your company details, then upload the KYC documents the form lists for your country and category. You can save and resume at any point. PMC reviews the file and you are notified when your KYC is approved.</p></details><details className="pmc-faq" data-cat="registration"><summary>Which documents does KYC need?</summary><p>The document list depends on your country and the licences your work category requires (for example, electrical or plumbing licences for Kazakhstan works packages). The registration form shows exactly which slots apply to you.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details><details className="pmc-faq" data-cat="emd"><summary>What is EMD and how do I pay it?</summary><p>The Earnest Money Deposit secures your bid. Each tender sets it as a fixed amount or a percentage. Pay it from the bid tracker by transfer to escrow or by uploading a bank guarantee. Escrow confirms receipt before your bid moves on.</p></details></div>
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
