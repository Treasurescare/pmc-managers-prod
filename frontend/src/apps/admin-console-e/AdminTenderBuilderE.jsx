import { useUiTheme } from "@/context/UiThemeContext";
import TenderBuilderPanel from "@/apps/admin-console/TenderBuilderPanel";
import AdminSideNavE from "./AdminSideNavE";
import AdminAvatarMenu from "./AdminAvatarMenu";
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
<div className="pmc-adm"><AdminSideNavE active="Tender builder" />
<div>
<header className="pmc-atop">
  <div className="crumb">Procurement / <b>Tender builder</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" data-testid="tb-search-input" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r"><button className="pmc-btn pmc-btn--secondary" data-help-open="" data-testid="tb-help-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button><button className="pmc-ib pmc-bell" aria-label="Alerts" data-testid="tb-bell-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg></button><AdminAvatarMenu /></div>
</header>
<main className="pmc-amain" style={{ padding: 0 }}>
  <TenderBuilderPanel />
</main>
</div>
</div>
    </div>
  );
}
