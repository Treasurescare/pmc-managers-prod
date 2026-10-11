import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";
import { useAdminEvaluationsLive } from "@/lib/pmcELiveData";
import AdminSideNavE from "./AdminSideNavE";

export default function AdminEvaluationListE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useAdminEvaluationsLive({ enabled: isE });
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
    <div data-testid="admin-evaluation-list-e" data-pmc-e-page="admin-evaluation-list-e">
<div className="pmc-adm"><AdminSideNavE active="Evaluation" /><div>
<header className="pmc-atop"><div className="crumb">Money &amp; compliance / <b>Evaluation</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r"><a href="#" className="pmc-btn pmc-btn--primary"><svg className="pmc-ico" aria-hidden="true"><use href="#i-plus" /></svg> Create</a><button className="pmc-btn pmc-btn--secondary" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button><button className="pmc-ib pmc-bell" aria-label="6 alerts"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg><span className="pmc-bell__n">6</span></button><button className="pmc-ib" aria-label="AI copilot"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg></button><span className="pmc-avatar" title="adminsupport@pmcmanagers.com · 2FA on">A</span></div>
</header><main className="pmc-amain"><div className="ah"><div><div className="pmc-eyebrow">Money &amp; compliance</div><h1>Evaluation</h1></div><div style={{ display: "flex", gap: "8px" }}></div></div><section className="pmc-panel"><table className="pmc-table"><thead><tr><th>Tender</th><th className="num">Bids</th><th>Stage</th><th>Detail</th><th></th></tr></thead><tbody><tr><td><div style={{ fontWeight: "600" }}>Turnkey IVF Laboratory Setup</div><div className="pmc-muted" style={{ fontSize: "12px" }}><span className="pmc-ref">PMC-NOT-2026-0055</span></div></td><td className="num">3</td><td><span className="pmc-pill pmc-pill--warning">Technical scoring</span></td><td>3 of 3 scored</td><td><a href="#" className="pmc-btn pmc-btn--primary pmc-btn--sm">Open room</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>OPD Queue Management</div><div className="pmc-muted" style={{ fontSize: "12px" }}><span className="pmc-ref">PMC-NOT-2026-0038</span></div></td><td className="num">2</td><td><span className="pmc-pill ">Waiting for deadline</span></td><td>Opens 1 Oct</td><td><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">View</a></td></tr><tr><td><div style={{ fontWeight: "600" }}>Modular OTs — Wave 2</div><div className="pmc-muted" style={{ fontSize: "12px" }}><span className="pmc-ref">PMC-NOT-2026-0016</span></div></td><td className="num">6</td><td><span className="pmc-pill pmc-pill--success">Awarded</span></td><td>Locked 8 Sep</td><td><a href="#" className="pmc-btn pmc-btn--secondary pmc-btn--sm">Report</a></td></tr></tbody></table></section></main></div></div>
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
    <div className="pmc-eyebrow" style={{ margin: "4px 0 10px", color: "var(--ink-muted)" }}>On this page · Evaluation</div>
    <div style={{ display: "grid", gap: "8px", marginBottom: "20px" }}><div className="pmc-tip"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg><div><b>One room per tender</b>Open room goes to scoring, L1 and sign-off for that tender.</div></div></div>
    <div className="pmc-eyebrow" style={{ marginBottom: "2px", color: "var(--ink-muted)" }}>Frequently asked</div>
    <div data-help-list=""><details className="pmc-faq" data-cat="admin"><summary>Who can see scores?</summary><p>Committee members and admins; bidders see their own scores after award.</p></details></div>
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
