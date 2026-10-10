import { useUiTheme } from "@/context/UiThemeContext";
import TenderBuilderPanel from "@/apps/admin-console/TenderBuilderPanel";
import "./tender-builder-e.css";

// The E-theme tender builder mock was display-only. Mount the fully-wired
// legacy panel (drafts list, DPR AI fill, section editor, save/history/
// publish) inside the Option E admin shell so navigation stays consistent.
export default function AdminTenderBuilderE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="admin-tender-builder-e" data-pmc-e-page="admin-tender-builder-e">
<div className="pmc-adm"><aside className="pmc-side" aria-label="Admin"><div className="pmc-side__brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Admin console</span></div><div className="pmc-side__group">Overview</div><a href="/admin/e/dashboard" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-home" /></svg>Dashboard</a><a href="/admin/e/audit" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-link" /></svg>Audit ledger</a><div className="pmc-side__group">Procurement</div><a href="/admin/e/notices" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Notices</a><a href="/admin/e/tender-builder" className="pmc-side__item" aria-current="page"><svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg>Tender builder</a><a href="/admin/e/corrigenda" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Corrigenda</a><a href="/admin/e/boq" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>BOQ & contracts</a><a href="/admin/e/work-packages" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-box" /></svg>Work packages</a><a href="/admin/e/catalog" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-layers" /></svg>Catalog</a><div className="pmc-side__group">Market</div><a href="/admin/e/vendors" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-users" /></svg>Vendors</a><a href="/admin/e/registrations" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Registrations</a><a href="/admin/e/vendor-intel" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-eye" /></svg>Vendor intel</a><a href="/admin/e/engagements" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chat" /></svg>Engagements</a><div className="pmc-side__group">Money & compliance</div><a href="/admin/e/bidding" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-gavel" /></svg>Bidding ops</a><a href="/admin/e/escrow" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-coin" /></svg>Escrow / EMD</a><a href="/admin/e/billing" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg>Billing</a><a href="/admin/e/evaluation" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-check" /></svg>Evaluation</a><a href="/admin/e/l1-award" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chart" /></svg>L1 comparison</a><a href="/admin/e/awards" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>Awards</a><a href="/admin/e/docusign" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-sign" /></svg>DocuSign</a><a href="/admin/e/permissions" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-lock" /></svg>Permissions</a><div className="pmc-side__group">Events</div><a href="/admin/e/events" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-clock" /></svg>Events & alerts</a><a href="/admin/e/stakeholder-reports" className="pmc-side__item"><svg className="pmc-ico" aria-hidden="true"><use href="#i-chart" /></svg>Stakeholder reports</a></aside>
<div>
<header className="pmc-atop">
  <div className="crumb">Procurement / <b>Tender builder</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" data-testid="tb-search-input" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r"><button className="pmc-btn pmc-btn--secondary" data-help-open="" data-testid="tb-help-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button><button className="pmc-ib pmc-bell" aria-label="Alerts" data-testid="tb-bell-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg></button><span className="pmc-avatar" title="Admin">A</span></div>
</header>
<main className="pmc-amain" style={{ padding: 0 }}>
  <TenderBuilderPanel />
</main>
</div>
</div>
    </div>
  );
}
