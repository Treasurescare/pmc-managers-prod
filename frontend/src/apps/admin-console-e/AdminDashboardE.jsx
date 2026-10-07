import { useUiTheme } from "@/context/UiThemeContext";
import { useAdminDashboardLive } from "@/lib/pmcELiveData";
import AdminAvatarMenu from "./AdminAvatarMenu";
import EscrowInstitutionsKPI from "./EscrowInstitutionsKPI";
import "./admin-dashboard.css";

const STAGES = [
  ["I", "Draft"], ["II", "Published"], ["III", "Clarifications"],
  ["IV", "Bidding"], ["V", "Technical eval"], ["VI", "Commercial eval"], ["VII", "Awarded"],
];
// I–IV are notice stages → filtered notices list; V–VII are bid stages → bidding ops
const STAGE_HREFS = [
  "/admin/e/notices?status=draft", "/admin/e/notices?status=published",
  "/admin/e/notices?status=published", "/admin/e/notices?status=closing",
  "/admin/e/bidding", "/admin/e/bidding", "/admin/e/bidding",
];

// Admin dashboard v2 — layout ported from the supplied E-Admin-Dashboard
// redesign into the light Option E theme. Every section is wired to real
// data by useAdminDashboardLive (notices, bids, vendors, audit events).
export default function AdminDashboardE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useAdminDashboardLive({ enabled: isE });
  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="admin-dashboard-e" data-pmc-e-page="admin-dashboard-e">
<div className="pmc-adm">
<aside className="pmc-side" aria-label="Admin"><div className="pmc-side__brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Admin console</span></div><div className="pmc-side__group">Overview</div><a href="/admin/e/dashboard" className="pmc-side__item" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Dashboard</a><a href="/admin/e/audit" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>Audit ledger</a><div className="pmc-side__group">Procurement</div><a href="/admin/e/notices" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Notices<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>0</span></a><a href="/admin/e/tender-builder" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg>Tender builder</a><a href="/admin/e/corrigenda" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Corrigenda</a><a href="/admin/e/boq" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>BOQ & contracts</a><a href="/admin/e/work-packages" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-box" /></svg>Work packages<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>0</span></a><a href="/admin/e/catalog" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>Catalog</a><div className="pmc-side__group">Market</div><a href="/admin/e/vendors" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Vendors<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>0</span></a><a href="/admin/e/registrations" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Registrations</a><a href="/admin/e/vendor-intel" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-eye" /></svg>Vendor intel</a><a href="/admin/e/engagements" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg>Engagements</a><div className="pmc-side__group">Money & compliance</div><a href="/admin/e/bidding" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>Bidding ops<span className="pmc-side__count">0</span></a><a href="/admin/e/escrow" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>Escrow / EMD</a><a href="/admin/e/billing" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Billing</a><a href="/admin/e/evaluation" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Evaluation</a><a href="/admin/e/l1-award" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chart" /></svg>L1 comparison</a><a href="/admin/e/awards" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Awards</a><a href="/admin/e/docusign" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>DocuSign</a><a href="/admin/e/permissions" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>Permissions</a><div className="pmc-side__group">Events</div><a href="/admin/e/events" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>Events & alerts</a></aside>
<div>
<header className="pmc-atop">
  <div className="crumb">Overview / <b>Dashboard</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" data-testid="dash-search-input" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r">
    <a href="/admin/e/tender-builder" className="pmc-btn pmc-btn--primary" data-testid="dash-create-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Create</a>
    <button className="pmc-btn pmc-btn--secondary" data-help-open="" data-testid="dash-help-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
    <button className="pmc-ib pmc-bell" aria-label="Alerts" data-testid="dash-bell-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">0</span></button>
    <AdminAvatarMenu />
  </div>
</header>
<main className="pmc-amain">
  <div className="adh">
    <div><div className="adh__eyebrow">All departments · <span data-dash-date>—</span></div><h1>Procurement overview</h1></div>
    <div style={{ display: "flex", gap: "8px" }}>
      <a href="/admin/e/audit" className="pmc-btn pmc-btn--secondary" data-testid="dash-export-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Export audit report</a>
      <a href="/admin/e/tender-builder" className="pmc-btn pmc-btn--primary" data-testid="dash-new-tender-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> New tender</a>
    </div>
  </div>

  <section className="ad-attn" aria-label="Needs attention" data-testid="dash-attention">
    <div className="ad-attn__tag">ATTENTION</div>
    <a href="/admin/e/notices?status=closing" data-testid="dash-attn-closing"><span><span className="n" data-attn="closing">0</span> tenders close this week</span><span className="arr" aria-hidden="true">→</span></a>
    <a href="/admin/e/notices?status=draft" data-testid="dash-attn-approvals"><span><span className="n" data-attn="approvals">0</span> drafts awaiting approval</span><span className="arr" aria-hidden="true">→</span></a>
    <a href="/admin/e/bidding" data-testid="dash-attn-emd"><span><span className="n" data-attn="emd">0</span> bids awaiting EMD</span><span className="arr" aria-hidden="true">→</span></a>
    <EscrowInstitutionsKPI />
  </section>

  <section className="pmc-panel" style={{ overflow: "hidden" }} data-testid="dash-pipeline-panel">
    <div className="pmc-panel__head"><h2 className="pmc-panel__title">Tender pipeline</h2><span className="pmc-muted" style={{ fontSize: "12px" }}><span data-dash-active>0</span> active · live counts by stage</span></div>
    <div className="ad-pipe" data-testid="dash-pipeline">
      {STAGES.map(([rn, label], i) => (
        <a key={rn} href={STAGE_HREFS[i]} data-stage={i} data-testid={`dash-stage-${i}`}>
          <span className="rn">{rn}</span>
          <span className="vb" aria-hidden="true"><i style={{ height: "4%" }}></i></span>
          <span className="c">0</span>
          <span className="l">{label}</span>
          <span className="l2"></span>
        </a>
      ))}
    </div>
  </section>

  <div className="pmc-kpis">
    <div className="pmc-kpi"><div className="l">EMD collected</div><div className="pmc-figure">—</div><div className="s">…</div></div>
    <div className="pmc-kpi"><div className="l">Active contracts</div><div className="pmc-figure">—</div><div className="s">milestones tracked</div></div>
    <div className="pmc-kpi"><div className="l">Bids in pipeline</div><div className="pmc-figure">—</div><div className="s">…</div></div>
    <div className="pmc-kpi"><div className="l">Approved vendors</div><div className="pmc-figure">—</div><div className="s">…</div></div>
  </div>

  <div className="ad-cols">
    <div className="pmc-stack">
      <section className="pmc-panel" style={{ overflow: "hidden" }} data-testid="dash-bids-panel">
        <div className="pmc-panel__head"><h2 className="pmc-panel__title">Bids waiting on a step</h2><a href="/admin/e/bidding">Open bidding ops</a></div>
        <table className="pmc-table"><thead><tr><th style={{ width: "34%" }}>Bid · vendor</th><th className="num">Price</th><th>Status</th><th>Next step</th><th></th></tr></thead>
        <tbody id="dash-bids-rows"><tr><td colSpan={5} style={{ padding: "24px", textAlign: "center", color: "var(--ink-muted)" }}>Loading…</td></tr></tbody></table>
      </section>

      <section className="pmc-panel ad-cw" style={{ overflow: "hidden" }} data-testid="dash-closing-panel">
        <div className="pmc-panel__head"><h2 className="ad-sech" style={{ margin: 0 }}>Closing this week · <span data-cw-count>0</span></h2><a href="/admin/e/notices">All tenders →</a></div>
        <table className="pmc-table"><thead><tr><th>Tender</th><th className="num" style={{ width: "110px" }}>Bids sealed</th><th className="num" style={{ width: "130px" }}>Clarifications</th><th className="num" style={{ width: "130px" }}>Closes in</th></tr></thead>
        <tbody id="dash-closing-rows"><tr><td colSpan={4} style={{ padding: "24px", textAlign: "center", color: "var(--ink-muted)" }}>Loading…</td></tr></tbody></table>
      </section>
    </div>

    <div className="pmc-stack">
      <section className="pmc-panel" style={{ overflow: "hidden" }} data-testid="dash-approvals-panel">
        <div className="pmc-panel__head"><h2 className="ad-sech" style={{ margin: 0 }}>Approvals queue</h2><span className="pmc-pill pmc-pill--warning" data-appr-pill>0</span></div>
        <ol className="ad-appr" id="dash-approvals"><li className="ad-appr__empty">Loading…</li></ol>
        <a href="/admin/e/notices" style={{ display: "flex", alignItems: "center", justifyContent: "center", gap: "8px", height: "48px", fontSize: "14px", fontWeight: "600", borderTop: "1px solid var(--line)" }} data-testid="dash-approvals-all">Open full queue →</a>
      </section>

      <section className="pmc-panel" style={{ overflow: "hidden" }} data-testid="dash-audit-panel">
        <div className="pmc-panel__head"><h2 className="ad-sech" style={{ margin: 0, display: "flex", alignItems: "center" }}><span className="ad-live" aria-hidden="true"></span>Audit stream</h2><a href="/admin/e/audit" style={{ fontFamily: "var(--font-mono)", fontSize: "11px", letterSpacing: ".1em" }}>EXPORT</a></div>
        <ol className="ad-audit" id="dash-audit"><li><time>—</time><span className="s">Loading…</span></li></ol>
        <div className="ad-audit__foot">Immutable · hash-chained entries · verified on the audit ledger</div>
      </section>
    </div>
  </div>
</main>
</div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Admin dashboard</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Attention strip first</b>The amber strip lists only items that need you today.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Pipeline stages are live</b>Counts come straight from the notice register; the tallest bar is where work sits.</div></div><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Audit stream is append-only</b>Every action lands here hash-chained; use Export for the full ledger.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="admin"><summary>How do I publish a tender from a DPR?</summary><p>Open <b>Tender builder</b>, choose <b>AI generate from DPR</b> and upload the document. Check any fields the AI could not extract, save, then send for approval.</p></details><details className="pmc-faq" data-cat="admin"><summary>How do I issue a corrigendum?</summary><p>Open the notice, choose <b>Issue corrigendum</b>, set the effective date and describe the change. Every bidder and follower is alerted.</p></details><details className="pmc-faq" data-cat="admin"><summary>How do I form an evaluation committee?</summary><p>From <b>Bidding ops</b>, choose <b>Form committee</b>, add internal members, invite external evaluators and set the quorum.</p></details><details className="pmc-faq" data-cat="admin"><summary>How do I verify the audit ledger?</summary><p>Open <b>Audit ledger</b> and choose <b>Verify chain</b>. The check re-computes every SHA-256 link and reports the first break, if any.</p></details></div>
    <p data-help-empty="" hidden style={{ color: "var(--ink-muted)", fontSize: "14px" }}>No answer matches yet. Raise a ticket below and the PMC desk will reply.</p>
    <a href="/help" className="pmc-btn pmc-btn--secondary" style={{ width: "100%", marginTop: "16px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Open the full Help Centre</a>
  </div>
  <div className="pmc-drawer__foot">
    <a href="/help" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg> Raise a ticket</a>
    <a href="mailto:tenders@pmcmanagers.com" className="pmc-btn pmc-btn--secondary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-mail" /></svg> Email the desk</a>
  </div>
</aside>
<button className="pmc-helpfab" data-help-open="" aria-label="Open help"><span className="pmc-helpfab__q">?</span>Help</button>
    </div>
  );
}
