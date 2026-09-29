import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { useAdminCorrigendaLive } from "@/lib/pmcELiveData";

export default function AdminCorrigendaE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useAdminCorrigendaLive({ enabled: isE });
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
    <div data-testid="admin-corrigenda-e" data-pmc-e-page="admin-corrigenda-e">
<div className="pmc-adm"><aside className="pmc-side" aria-label="Admin"><div className="pmc-side__brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Admin console</span></div><div className="pmc-side__group">Overview</div><a href="/admin/e/dashboard" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Dashboard</a><a href="/admin/e/audit" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>Audit ledger</a><div className="pmc-side__group">Procurement</div><a href="/admin/e/notices" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Notices<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>29</span></a><a href="/admin/e/tender-builder" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg>Tender builder</a><a href="/admin/e/corrigenda" className="pmc-side__item" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Corrigenda</a><a href="/admin/e/boq" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>BOQ & contracts</a><a href="/admin/e/work-packages" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-box" /></svg>Work packages<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>50</span></a><a href="/admin/e/catalog" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>Catalog</a><div className="pmc-side__group">Market</div><a href="/admin/e/vendors" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Vendors<span style={{ marginLeft: "auto", fontSize: "12px", color: "var(--on-chrome-muted)" }}>76</span></a><a href="/admin/e/registrations" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Registrations</a><a href="/admin/e/vendor-intel" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-eye" /></svg>Vendor intel</a><a href="/admin/e/engagements" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg>Engagements</a><div className="pmc-side__group">Money & compliance</div><a href="/admin/e/bidding" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>Bidding ops<span className="pmc-side__count">10</span></a><a href="/admin/e/escrow" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>Escrow / EMD</a><a href="/admin/e/billing" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Billing</a><a href="/admin/e/evaluation" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Evaluation</a><a href="/admin/e/l1-award" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chart" /></svg>L1 comparison</a><a href="/admin/e/awards" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Awards</a><a href="/admin/e/docusign" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>DocuSign</a><a href="/admin/e/permissions" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>Permissions</a><div className="pmc-side__group">Events</div><a href="/admin/e/events" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>Events & alerts</a></aside><div>
<header className="pmc-atop"><div className="crumb">Procurement / <b>Corrigenda</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r"><a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Create</a><button className="pmc-btn pmc-btn--secondary" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button><button className="pmc-ib pmc-bell" aria-label="6 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">6</span></button><button className="pmc-ib" aria-label="AI copilot"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg></button><span className="pmc-avatar" title="adminsupport@pmcmanagers.com · 2FA on">A</span></div>
</header><main className="pmc-amain"><div className="ah"><div><div className="pmc-eyebrow">Procurement</div><h1>Corrigenda</h1></div><div style={{ display: "flex", gap: "8px" }}></div></div><div style={{ display: "grid", gridTemplateColumns: "minmax(0,1fr) 380px", gap: "24px", alignItems: "start" }}><section className="pmc-panel"><table className="pmc-table"><thead><tr><th>Corrigendum</th><th>Change</th><th>Status</th><th>Effective</th><th>Reach</th><th></th></tr></thead><tbody><tr><td><div style={{ fontWeight: "600" }}>Corrigendum 1 · Turnkey IVF Laboratory Setup</div><div className="pmc-muted" style={{ fontSize: "12px" }}><span className="pmc-ref">PMC-NOT-2026-0055</span></div></td><td>Clause 4.2 · ISO classes</td><td><span className="pmc-pill pmc-pill--success">Published</span></td><td>26 Sep 2026</td><td>3 bidders · 12 followers alerted</td><td><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">View</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Corrigendum 2 · Dual Medical University</div><div className="pmc-muted" style={{ fontSize: "12px" }}><span className="pmc-ref">PMC-NOT-2026-0059</span></div></td><td>Deadline extended to 7 Nov</td><td><span className="pmc-pill ">Draft</span></td><td>—</td><td>Not sent</td><td><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Edit</a></td></tr></tbody></table></section><aside className="pmc-panel" style={{ position: "sticky", top: "88px" }}><div className="pmc-panel__head"><h2 className="pmc-panel__title">New corrigendum</h2></div><div className="pmc-panel__body" style={{ display: "grid", gap: "12px" }}><div className="pmc-field"><label>Notice</label><select className="pmc-input"><option>PMC-NOT-2026-0059 · Dual Medical University</option></select></div>
<div className="pmc-field"><label>What changes</label><div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}><span className="pmc-chip" aria-pressed="true">Deadline</span><span className="pmc-chip">Scope</span><span className="pmc-chip">Documents</span><span className="pmc-chip">BOQ</span><span className="pmc-chip">Eligibility</span><span className="pmc-chip">EMD</span></div></div>
<div className="pmc-field"><label>New submission deadline</label><input className="pmc-input" value="7 Nov 2026, 17:00 Almaty" /></div>
<div className="pmc-field"><label>Effective from</label><input className="pmc-input" value="Publish immediately" /></div>
<div className="pmc-callout pmc-callout--info" style={{ fontSize: "13px", lineHeight: "20px" }}><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><div>2 bidders with drafts and 9 followers will be alerted. Sealed bids stay sealed; bidders may unseal to update.</div></div>
<button className="pmc-btn pmc-btn--primary">Publish corrigendum</button></div></aside></div></main></div></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Corrigenda</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>Reach is shown before you publish</b>You see exactly who will be alerted.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="admin"><summary>Do sealed bids have to change?</summary><p>No. Bidders are alerted and may unseal to update before the (new) deadline.</p></details></div>
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
