import { useState } from "react";
import PortalSideNavE from "./PortalSideNavE";

/**
 * PortalShellE — generic Option-E app frame shared by the staff and escrow
 * portals. It is a direct clone of AdminShellE's structure (.pmc-adm /
 * .pmc-side / .pmc-atop / .pmc-navtoggle / .pmc-side__scrim / .pmc-amain), so
 * on desktop the dark sidebar is fixed and below 1100px it collapses to an
 * off-canvas drawer driven by the single hamburger with a tap-to-close scrim.
 * All of that behaviour lives in the already-shipped theme CSS; this is only
 * the one place the markup/state lives.
 *
 * `items` are {key,label,icon,badge,group,testid}; selecting one calls
 * onSelect(key) and closes the drawer. `crumb` + `header` render inside the
 * top bar after the hamburger.
 */
export default function PortalShellE({
  brand, items, activeKey, onSelect, crumb, header, children, mainStyle,
  rootTestId, sideTestId,
}) {
  const [navOpen, setNavOpen] = useState(false);
  const select = (k) => { onSelect?.(k); setNavOpen(false); };
  return (
    <div className={"pmc-adm" + (navOpen ? " pmc-adm--navopen" : "")} data-testid={rootTestId}>
      <PortalSideNavE brand={brand} items={items} activeKey={activeKey} onSelect={select} testId={sideTestId} />
      <button className="pmc-side__scrim" aria-label="Close menu" onClick={() => setNavOpen(false)} data-testid="portal-nav-scrim" />
      <div className="pmc-adm__main">
        <header className="pmc-atop">
          <button className="pmc-navtoggle" aria-label="Open menu" aria-expanded={navOpen}
                  onClick={() => setNavOpen((v) => !v)} data-testid="portal-nav-toggle">
            <svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true">
              <path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" />
            </svg>
          </button>
          {crumb ? <div className="crumb">{crumb}</div> : null}
          {header}
        </header>
        <main className="pmc-amain" style={mainStyle}>{children}</main>
      </div>
    </div>
  );
}
