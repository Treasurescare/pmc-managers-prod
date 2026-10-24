import { useState } from "react";
import AdminAvatarMenu from "./AdminAvatarMenu";
import AdminSideNavE from "./AdminSideNavE";

// Shared Option E admin shell (sidebar + top bar). Below 1024px the sidebar
// becomes an off-canvas drawer toggled by the hamburger, with a tap-to-close
// scrim — so tablets/phones get the full content width instead of a squeezed
// column. Navigating via a sidebar link reloads the page, which resets state.
export default function AdminEShell({ active, crumb, children }) {
  const [navOpen, setNavOpen] = useState(false);
  return (
    <div className={"pmc-adm" + (navOpen ? " pmc-adm--navopen" : "")}>
      <AdminSideNavE active={active} />
      <button
        className="pmc-side__scrim"
        aria-label="Close menu"
        onClick={() => setNavOpen(false)}
        data-testid="admin-nav-scrim"
      />
      <div className="pmc-adm__main">
        <header className="pmc-atop">
          <button
            className="pmc-navtoggle"
            aria-label="Open menu"
            aria-expanded={navOpen}
            onClick={() => setNavOpen((v) => !v)}
            data-testid="admin-nav-toggle"
          >
            <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
              <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
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
