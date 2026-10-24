import { useUiTheme } from "@/context/UiThemeContext";
import TenderBuilderPanel from "@/apps/admin-console/TenderBuilderPanel";
import AdminShellE from "./AdminShellE";
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
<AdminShellE active="Tender builder" mainStyle={{ padding: 0 }} header={<>
  <div className="crumb">Procurement / <b>Tender builder</b></div>
  <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" data-testid="tb-search-input" /><span className="pmc-kbd">Ctrl K</span></label>
  <div className="pmc-atop__r"><button className="pmc-btn pmc-btn--secondary" data-help-open="" data-testid="tb-help-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button><button className="pmc-ib pmc-bell" aria-label="Alerts" data-testid="tb-bell-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg></button><AdminAvatarMenu /></div>
</>}>
  <TenderBuilderPanel />
</AdminShellE>
    </div>
  );
}
