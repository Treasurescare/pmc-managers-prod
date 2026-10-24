import { useState } from "react";
import AdminSideNavE from "./AdminSideNavE";

// Shared Option E admin frame. On desktop the sidebar is fixed; below the
// responsive breakpoint it collapses to an off-canvas drawer toggled by the
// single hamburger, with a tap-to-close scrim — so tablets/phones get the full
// content width instead of a squeezed column. `header` is the top-bar content
// (crumb, search, actions) rendered after the hamburger; `children` is the
// main area. This is the one place the drawer markup/state lives.
export default function AdminShellE({ active, header, children, mainStyle }) {
  const [navOpen, setNavOpen] = useState(false);
  return (
    <div className={"pmc-adm" + (navOpen ? " pmc-adm--navopen" : "")}>
      <AdminSideNavE active={active} />
      <button className="pmc-side__scrim" aria-label="Close menu" onClick={() => setNavOpen(false)} data-testid="admin-nav-scrim" />
      <div className="pmc-adm__main">
        <header className="pmc-atop">
          <button className="pmc-navtoggle" aria-label="Open menu" aria-expanded={navOpen} onClick={() => setNavOpen((v) => !v)} data-testid="admin-nav-toggle"><svg width="20" height="20" viewBox="0 0 20 20" aria-hidden="true"><path d="M3 5h14M3 10h14M3 15h14" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" /></svg></button>
          {header}
        </header>
        <main className="pmc-amain" style={mainStyle}>{children}</main>
      </div>
    </div>
  );
}
