import AdminAvatarMenu from "./AdminAvatarMenu";
import AdminSideNavE from "./AdminSideNavE";

// Shared Option E admin shell (sidebar + top bar) so E pages can mount the
// fully-wired legacy panels without duplicating chrome markup.
export default function AdminEShell({ active, crumb, children }) {
  return (
    <div className="pmc-adm">
      <AdminSideNavE active={active} />
      <div>
        <header className="pmc-atop">
          <div className="crumb">{crumb}</div>
          <label className="pmc-search"><svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg><input placeholder="Search tenders, bids, vendors, ledger events…" data-testid="shell-search-input" /><span className="pmc-kbd">Ctrl K</span></label>
          <div className="pmc-atop__r">
            <button className="pmc-btn pmc-btn--secondary" data-help-open="" data-testid="shell-help-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
            <button className="pmc-ib pmc-bell" aria-label="Alerts" data-testid="shell-bell-btn"><svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg></button>
            <AdminAvatarMenu />
          </div>
        </header>
        <main className="pmc-amain">{children}</main>
      </div>
    </div>
  );
}
