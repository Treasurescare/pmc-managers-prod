import { useEffect, useState } from "react";
import { useLocation, NavLink, Link } from "react-router-dom";

/**
 * PmcMobileNav — mobile-only navigation chrome.
 *
 * • On public routes (/, /notices, /tenders, /about, /vision, /help, etc.)
 *   renders a compact sticky top bar with a hamburger menu drawer.
 * • On vendor routes (/vendor, /vendor/*) renders a fixed bottom tab bar
 *   matching the supplied 01-Mobile-Supplier.html reference:
 *     Home | Tenders | Bids | Alerts | Account
 *
 * All visibility is controlled by CSS media queries in mobile-fix.css —
 * this component always renders but display collapses to `none` at
 * ≥768px viewports.
 */

const PUBLIC_MENU = [
  { to: "/", label: "Home" },
  { to: "/tenders/live", label: "Live tenders" },
  { to: "/tenders/completed", label: "Awarded" },
  { to: "/about", label: "About PMC" },
  { to: "/vision", label: "Vision & mission" },
  { to: "/suppliers", label: "For suppliers" },
  { to: "/buyers", label: "For buyers" },
  { to: "/trust", label: "Trust & security" },
  { to: "/help", label: "Help & FAQs" },
  { to: "/contact", label: "Contact" },
];

const VENDOR_TABS = [
  { to: "/vendor", label: "Home", testid: "mnav-home", iconId: "i-home" },
  { to: "/vendor/tenders", label: "Tenders", testid: "mnav-tenders", iconId: "i-search" },
  { to: "/vendor/mybids", label: "Bids", testid: "mnav-bids", iconId: "i-gavel" },
  { to: "/vendor/alerts", label: "Alerts", testid: "mnav-alerts", iconId: "i-bell" },
  { to: "/vendor/account", label: "Account", testid: "mnav-account", iconId: "i-users" },
];

export default function PmcMobileNav() {
  const { pathname } = useLocation();
  const [menuOpen, setMenuOpen] = useState(false);

  // Close drawer on route change
  useEffect(() => {
    setMenuOpen(false);
  }, [pathname]);

  // Body class toggle for CSS-driven drawer open state
  useEffect(() => {
    if (menuOpen) document.body.classList.add("pmc-mob-menu-open");
    else document.body.classList.remove("pmc-mob-menu-open");
    return () => document.body.classList.remove("pmc-mob-menu-open");
  }, [menuOpen]);

  // ESC closes drawer
  useEffect(() => {
    if (!menuOpen) return;
    const onKey = (e) => { if (e.key === "Escape") setMenuOpen(false); };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [menuOpen]);

  // Route classification
  const isAdminLogin = pathname === "/admin/login";
  const isVendorLogin = pathname === "/vendor/login" || pathname === "/login" || pathname === "/forgot-password" || pathname === "/reset-password";
  const isVendor = pathname === "/vendor" || pathname.startsWith("/vendor/");
  const isAdmin = pathname.startsWith("/admin");
  const isStaff = pathname.startsWith("/staff");
  const isM = pathname.startsWith("/m");

  // Suppress mobile chrome on:
  //  - vendor/admin login pages (they already have their own centered form)
  //  - /m/* mobile showcase routes
  if (isVendorLogin || isAdminLogin || isM) return null;

  // For vendor pages (post-login): show ONLY the bottom tab bar.
  if (isVendor) {
    return (
      <nav
        className="pmc-mobile-tabbar"
        data-testid="pmc-mobile-tabbar"
        aria-label="Vendor navigation"
      >
        {VENDOR_TABS.map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            end={t.to === "/vendor"}
            className={({ isActive }) => (isActive ? "is-active" : "")}
            data-testid={t.testid}
          >
            <svg aria-hidden="true"><use href={`#${t.iconId}`} /></svg>
            <span>{t.label}</span>
          </NavLink>
        ))}
      </nav>
    );
  }

  // For staff/admin routes: skip the mobile top bar (they have their own shells).
  if (isAdmin || isStaff) return null;

  // Public routes: compact top bar + slide-in menu.
  return (
    <>
      <header
        className="pmc-mobile-topbar"
        data-testid="pmc-mobile-topbar"
        role="banner"
      >
        <Link
          to="/"
          className="pmc-mob-brand"
          data-testid="pmc-mobile-brand"
        >
          <b>PMC Managers</b>
          <span>Global Tender Board</span>
        </Link>
        <button
          type="button"
          className="pmc-mob-hamburger"
          onClick={() => setMenuOpen(true)}
          aria-label="Open menu"
          data-testid="pmc-mobile-menu-open"
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <line x1="4" y1="7" x2="20" y2="7" />
            <line x1="4" y1="12" x2="20" y2="12" />
            <line x1="4" y1="17" x2="20" y2="17" />
          </svg>
        </button>
      </header>

      <div
        className="pmc-mobile-menu-scrim"
        onClick={() => setMenuOpen(false)}
        aria-hidden={!menuOpen}
        data-testid="pmc-mobile-menu-scrim"
      />
      <aside
        className="pmc-mobile-menu-drawer"
        role="dialog"
        aria-modal="true"
        aria-label="Navigation"
        aria-hidden={!menuOpen}
        data-testid="pmc-mobile-menu-drawer"
      >
        <div className="pmc-mob-menu-head">
          <div className="pmc-mob-brand">
            <b>PMC Managers</b>
            <span>Menu</span>
          </div>
          <button
            type="button"
            className="pmc-mob-menu-close"
            onClick={() => setMenuOpen(false)}
            aria-label="Close menu"
            data-testid="pmc-mobile-menu-close"
          >
            ×
          </button>
        </div>

        <nav aria-label="Main">
          {PUBLIC_MENU.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) => (isActive ? "is-active" : "")}
              data-testid={`pmc-mobile-menu-link-${item.to.replace(/\W+/g, "-").replace(/^-|-$/g, "") || "home"}`}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="pmc-mob-menu-cta">
          <Link
            to="/login"
            className="ghost"
            data-testid="pmc-mobile-menu-signin"
          >
            Sign in
          </Link>
          <Link
            to="/register"
            className="primary"
            data-testid="pmc-mobile-menu-register"
          >
            Register as supplier
          </Link>
        </div>
      </aside>
    </>
  );
}
