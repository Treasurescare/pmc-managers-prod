import { useEffect } from "react";
import { Link, useParams } from "react-router-dom";
import { toast } from "sonner";
import { useUiTheme } from "@/context/UiThemeContext";
import { useNoticeDetailLive } from "@/lib/pmcELiveData";
import useAuthSession from "@/lib/useAuthSession";
import { adminApi, staffApi, vendorApi } from "@/lib/api";

export default function NoticeDetailE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const { noticeRef } = useParams();
  useNoticeDetailLive({ enabled: isE, noticeRef });
  // v52bk — detect current session so the hero chrome can switch from
  // "Sign in / Register as supplier" to the authed avatar + dashboard chip.
  const { role, me, dashboardPath, loading } = useAuthSession();
  const authed = Boolean(role);
  const initial = (me?.name || me?.email || role || "?").slice(0, 1).toUpperCase();
  const signOut = async () => {
    try { await adminApi.logout(); } catch { /* ignore */ }
    try { await staffApi.logout(); } catch { /* ignore */ }
    try { await vendorApi.logout(); } catch { /* ignore */ }
    toast.success("Signed out");
    window.location.href = "/login";
  };
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
    <div data-testid="notice-detail-e" data-pmc-e-page="notice-detail-e">
<header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
  <Link to="/" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></Link>
  <nav className="pmc-nav">
    <Link to="/tenders/live" className="is-on">Tenders</Link>
    <Link to="/suppliers">For suppliers</Link>
    <Link to="/buyers">For buyers</Link>
    <Link to="/trust">Trust &amp; security</Link>
    <Link to="/help">Help &amp; FAQs</Link>
  </nav>
  <div className="pmc-top__act">
    <button className="pmc-btn pmc-btn--onchrome pmc-btn--sm">
      <svg className="pmc-ico" aria-hidden="true"><use href="#i-globe" /></svg> EN
    </button>
    {loading ? null : authed ? (
      <>
        <Link to={dashboardPath} className="pmc-btn pmc-btn--onchrome" data-testid="notice-topbar-dashboard"
              style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
          <span aria-hidden="true" style={{
            width: 24, height: 24, borderRadius: "50%", background: "var(--brass-on-chrome, #D2B46A)",
            color: "var(--chrome-ink, #0E1C14)", display: "inline-flex", alignItems: "center",
            justifyContent: "center", fontSize: 11, fontWeight: 700,
          }}>{initial}</span>
          Dashboard
        </Link>
        <button onClick={signOut} className="pmc-btn pmc-btn--onchrome" data-testid="notice-topbar-signout">
          Sign out
        </button>
      </>
    ) : (
      <>
        <Link to="/login" className="pmc-btn pmc-btn--onchrome" data-testid="notice-topbar-signin">Sign in</Link>
        <Link to="/register" className="pmc-btn pmc-btn--brass" data-testid="notice-topbar-register">Register as supplier</Link>
      </>
    )}
  </div>
</div></header>
<section className="pmc-chrome" style={{ padding: "28px 0 32px" }}><div className="pmc-wrap">
  <div className="pmc-crumb"><Link to="/tenders/live">Tender notices</Link>/<Link to="/tenders/live">Civil Works &amp; MEP</Link>/<span>PMC-NOT-2026-0055</span></div>
  <div style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: "40px", alignItems: "end", margin: "16px 0 24px" }}>
    <div><div style={{ display: "flex", gap: "8px", alignItems: "center", marginBottom: "12px" }}><span className="pmc-tag" style={{ borderColor: "var(--chrome-line)", color: "var(--on-chrome)" }}>Tender</span><span className="pmc-ref">PMC-NOT-2026-0055</span><span className="pmc-pill pmc-pill--info">Corrigendum 1 · 26 Sep</span><span className="pmc-pill pmc-pill--success">Open for bids</span></div>
      <h1 className="pmc-display" style={{ fontSize: "48px", lineHeight: "52px", margin: "0", maxWidth: "900px" }}>Turnkey IVF Laboratory Setup — Embryology Lab, Cryopreservation &amp; Cleanroom HVAC</h1></div>
    <div style={{ display: "flex", gap: "8px" }}>
      <button className="pmc-btn pmc-btn--onchrome"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg> Follow</button>
      <Link to={authed ? "#" : "/register"} className="pmc-btn pmc-btn--onchrome" data-testid="notice-download-pack"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Download pack</Link>
      <Link to={authed && role === "vendor" ? `/vendor/workspace/new?notice=${noticeRef}` : (authed ? dashboardPath : "/register")} className="pmc-btn pmc-btn--brass pmc-btn--lg" data-testid="notice-start-bid">Start bid</Link>
    </div>
  </div>
  <dl className="pmc-facts" style={{ margin: "0" }}><div><dt>Indicative budget</dt><dd>USD 2,100,000</dd></div><div><dt>EMD</dt><dd>3% of bid value</dd></div><div><dt>Tender fee</dt><dd>None</dd></div><div><dt>Delivery</dt><dd>Kazakhstan</dd></div><div><dt>Form of contract</dt><dd>Turnkey · lump sum</dd></div><div><dt>Closes in</dt><dd><span className="pmc-countdown" data-in="52" style={{ color: "var(--brass-on-chrome)", fontSize: "15px" }}>—</span></dd></div></dl>
</div></section>
<div className="pmc-wrap" style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 360px", gap: "32px", padding: "28px 0 72px", alignItems: "start" }}>
  <div>
    <div className="pmc-tabs" role="tablist" style={{ marginBottom: "24px" }}><button className="pmc-tab" aria-selected="true">Overview</button><button className="pmc-tab">Eligibility</button><button className="pmc-tab">Documents<span className="n">5</span></button><button className="pmc-tab">Clarifications<span className="n">2</span></button><button className="pmc-tab">Corrigenda<span className="n">1</span></button></div>
    <section className="dt-sec"><h2>Scope</h2><p>Turnkey design and build of an ISO Class 5/7 embryology laboratory for the Kazakhstan Medical Township, including cleanroom HVAC, cryopreservation storage and full embryology workstation fit-out. The contractor delivers design, supply, installation, validation and a 24-month defects liability period.</p>
      <div className="dt-scope"><div><svg className="pmc-ico" aria-hidden="true"><use href="#i-box" /></svg><b>Embryology lab</b><span>IVF workstations, ISO Class 5 chambers, lab furniture</span></div><div><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg><b>Cleanroom HVAC</b><span>ISO 14644 validation, HEPA filtration, pressure cascades</span></div><div><svg className="pmc-ico" aria-hidden="true"><use href="#i-shield" /></svg><b>Cryopreservation</b><span>LN2 storage, monitoring and alarms</span></div><div><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg><b>Commissioning</b><span>IQ/OQ/PQ validation, training, handover</span></div></div></section>
    <section className="dt-sec"><h2>Who can bid</h2><ul className="dt-list"><li><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg><span>Registered supplier with approved KYC on the PMC Tender Board</span></li><li><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg><span>At least two completed cleanroom or laboratory projects of USD 1M+ in the last five years</span></li><li><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg><span>Licences for the Kazakhstan work segments: <b>Electrical installation</b>, <b>Mechanical works</b>, <b>Plumbing &amp; firefighting</b> (or a licensed local partner)</span></li><li><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg><span>ISO 9001 certification</span></li></ul>
      {!authed && (
        <div className="pmc-callout pmc-callout--info" style={{ marginTop: "16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg><div>Registered suppliers see a <b>KYC match check</b> here before starting a bid. <Link to="/login">Sign in</Link> to check yours.</div></div>
      )}</section>
    <section className="dt-sec"><h2>Documents</h2><div className="pmc-panel"><div className="pmc-docrow"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg></span><div><b>Notice Inviting Tender (NIT)</b><span className="s">PDF · 1.2 MB · v2 after corrigendum 1</span></div><span></span><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Download</a></div><div className="pmc-docrow"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg></span><div><b>Scope of work & technical specifications</b><span className="s">PDF · 4.8 MB</span></div><span></span><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Download</a></div><div className="pmc-docrow"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg></span><div><b>Bill of quantities (BOQ)</b><span className="s">XLSX · 320 KB · fill and upload in the commercial envelope</span></div><span></span><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Download</a></div><div className="pmc-docrow"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg></span><div><b>Drawings — embryology lab & cleanroom layout</b><span className="s">ZIP · 38 MB</span></div><span></span><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Download</a></div><div className="pmc-docrow"><span className="i"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg></span><div><b>Draft contract & special conditions</b><span className="s">PDF · 900 KB</span></div><span></span><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Download</a></div></div></section>
    <section className="dt-sec"><h2>Clarifications</h2><div className="dt-qa"><b><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Can the cleanroom HVAC be subcontracted to a specialist?</b><p>Yes. Name the subcontractor in the technical envelope and include their ISO 14644 references. The main bidder remains responsible.</p><span className="pmc-ref">Answered 25 Sep 2026 · sent to all bidders</span></div><div className="dt-qa"><b><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Is the ISO Class 5 requirement for the full embryology lab or only the workstations?</b><p>ISO Class 5 applies at the workstations and IVF chambers; the surrounding lab is ISO Class 7. See corrigendum 1, clause 4.2.</p><span className="pmc-ref">Answered 24 Sep 2026 · sent to all bidders</span></div><a href="#" className="pmc-btn pmc-btn--secondary" style={{ marginTop: "8px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Ask a question</a><span className="pmc-muted" style={{ fontSize: "13px", marginLeft: "12px" }}>Questions close 27 Sep 2026. Answers go to every bidder.</span></section>
  </div>
  <aside style={{ display: "grid", gap: "16px", position: "sticky", top: "96px" }}>
    <div className="pmc-card" style={{ padding: "22px" }}>
      <div className="pmc-eyebrow">Submission closes</div>
      <div className="pmc-countdown" data-in="52" style={{ fontSize: "28px", lineHeight: "36px", margin: "6px 0 2px" }}>—</div>
      <div className="pmc-muted" style={{ fontSize: "13px" }}>30 Sep 2026, 21:48 Almaty time</div>
      <hr style={{ border: "0", borderTop: "1px solid var(--line)", margin: "16px 0" }} />
      <dl className="pmc-kv"><dt>Covers</dt><dd>3 sealed envelopes</dd><dt>Withdrawal</dt><dd>Allowed before deadline</dd><dt>Multi-currency bids</dt><dd>No · USD only</dd><dt>Two-stage bidding</dt><dd>No</dd></dl>
      <Link to={authed && role === "vendor" ? `/vendor/workspace/new?notice=${noticeRef}` : (authed ? dashboardPath : "/register")} className="pmc-btn pmc-btn--primary pmc-btn--lg" style={{ width: "100%", marginTop: "18px" }} data-testid="notice-aside-start-bid">Start bid</Link>
      {!authed && (
        <div className="pmc-muted" style={{ fontSize: "12px", textAlign: "center", marginTop: "8px" }}>New supplier? <Link to="/register">Register first</Link> — about 15 minutes</div>
      )}
    </div>
    <div className="pmc-panel" style={{ padding: "20px" }}><b style={{ fontSize: "15px" }}>Key dates</b><div className="pmc-timeline" style={{ marginTop: "14px" }}>
      <div className="done"><span className="dot"></span><div><b>Published</b><span>21 Sep 2026</span></div></div>
      <div className="done"><span className="dot"></span><div><b>Corrigendum 1</b><span>26 Sep 2026 · clause 4.2 ISO classes</span></div></div>
      <div className="done"><span className="dot"></span><div><b>Clarifications close</b><span>27 Sep 2026</span></div></div>
      <div className="now"><span className="dot"></span><div><b>Bid submission closes</b><span>30 Sep 2026, 21:48</span></div></div>
      <div><span className="dot"></span><div><b>Technical envelopes open</b><span>1 Oct 2026 · committee only</span></div></div>
      <div><span className="dot"></span><div><b>Commercial opening &amp; L1</b><span>After technical scores are locked</span></div></div></div></div>
    <div className="pmc-panel" style={{ padding: "16px 20px" }}><div className="pmc-hashline"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><span>Notice sealed on the ledger · <code>notice.publish #1872</code></span></div><div className="pmc-hashline" style={{ marginTop: "6px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg><span>Corrigendum 1 · <code>corrigendum.issue #1880</code></span></div></div>
  </aside>
</div>
<footer className="pmc-chrome" style={{ padding: "40px 0 28px", marginTop: "0" }}><div className="pmc-wrap" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
  <div className="pmc-brand"><span className="pmc-brand__n" style={{ fontSize: "20px" }}>PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></div>
  <div style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: "20px" }} className="pmc-fcol"><Link to="/tenders/live">Open notices</Link><Link to="/help">Help Centre</Link><Link to="/trust">Trust &amp; security</Link><Link to="/privacy">Privacy</Link><span className="pmc-muted">© 2026 PMC Managers Limited</span></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Tender detail</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Download the full pack</b>One ZIP with every document at its latest version.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Ask before the clarification deadline</b>Answers are shared with all bidders.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Follow this tender</b>You'll be alerted to corrigenda and deadline changes.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="bidding"><summary>How are sealed bids kept confidential?</summary><p>Bids are submitted in separate technical and commercial envelopes. Envelopes open only after the submission deadline, and only for the evaluation committee. Every open, view and decision is written to a SHA-256 hash-chained audit ledger.</p></details><details className="pmc-faq" data-cat="bidding"><summary>Can I change or withdraw my bid?</summary><p>If the tender allows withdrawal, you can withdraw or resubmit before the submission deadline from <b>My bids</b>. The tender page states whether withdrawal is allowed.</p></details><details className="pmc-faq" data-cat="bidding"><summary>How will I hear about a corrigendum?</summary><p>When a tender you follow or have bid on is amended, you get an alert in the portal and by email, and the change is shown on the tender page with its effective date.</p></details><details className="pmc-faq" data-cat="emd"><summary>What is EMD and how do I pay it?</summary><p>The Earnest Money Deposit secures your bid. Each tender sets it as a fixed amount or a percentage. Pay it from the bid tracker by transfer to escrow or by uploading a bank guarantee. Escrow confirms receipt before your bid moves on.</p></details><details className="pmc-faq" data-cat="emd"><summary>Which currencies are supported?</summary><p>Budgets and bids are shown in the tender's own currency, for example USD, KZT or INR. The tender states whether multi-currency bids are allowed.</p></details><details className="pmc-faq" data-cat="awards"><summary>How are contracts signed?</summary><p>Awards, purchase orders and contracts are signed with DocuSign, either inside the portal or through a DocuSign email link. Signed copies appear under <b>Signatures</b>.</p></details></div>
    <p data-help-empty="" hidden style={{ color: "var(--ink-muted)", fontSize: "14px" }}>No answer matches yet. Raise a ticket below and the PMC desk will reply.</p>
    <Link to="/help" className="pmc-btn pmc-btn--secondary" style={{ width: "100%", marginTop: "16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Open the full Help Centre</Link>
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
