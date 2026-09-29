import { useEffect, useState } from "react";
import { useLocation, NavLink, Link } from "react-router-dom";
import { pmcInstallSteps, detectPmcBrowser } from "@/lib/pmcInstallInstructions";

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
 *
 * The drawer footer also exposes an "Install app" button that ALWAYS
 * shows an actionable path — replays the native install prompt when the
 * browser has fired one, otherwise shows browser-specific step-by-step
 * instructions (Samsung Internet, Firefox Android, Opera, Chrome, Edge,
 * iOS Safari, macOS Safari, desktop Chromium) via pmcInstallSteps().
 */

const PWA_DISMISS_KEY = "pmc_install_dismissed_at";

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
  const [installSteps, setInstallSteps] = useState(null);

  // Close drawer on route change
  useEffect(() => {
    setMenuOpen(false);
    setInstallSteps(null);
  }, [pathname]);

  // Trigger the PWA install flow. Always ends with SOMETHING actionable:
  //   1. If the browser fired `beforeinstallprompt`, call `.prompt()` — this
  //      is the ONLY way to invoke the OS-level install dialog. Chrome,
  //      Edge, Samsung Internet ≥ 4, Opera and Brave all fire this event
  //      and honour `.prompt()`.
  //   2. If `.prompt()` fails or the browser never fires the event
  //      (iOS Safari, Firefox Android, Chrome pre-engagement), fall back to
  //      browser-specific step-by-step instructions rendered in the drawer.
  const triggerInstall = async () => {
    try { localStorage.removeItem(PWA_DISMISS_KEY); } catch (_) { /* noop */ }
    const deferred = window.__pmcInstallPromptEvent;
    if (deferred) {
      try {
        await deferred.prompt();
        const choice = await deferred.userChoice;
        window.__pmcInstallPromptEvent = null;
        if (choice?.outcome === "accepted") {
          setMenuOpen(false);
          return;
        }
        // If the user dismissed the native OS dialog, don't nag them with
        // instructions — they explicitly said no.
        setMenuOpen(false);
        return;
      } catch (_) { /* prompt() rejected → fall back to manual steps */ }
    }
    setInstallSteps(pmcInstallSteps());
  };

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
  // Show a back button on any non-home public route so users always have a
  // way back — matches the `.mtop` reference pattern in
  // /app/design/mobile/02-Mobile-Public.html.
  const showBack = pathname !== "/" && pathname !== "";
  const goBack = () => {
    if (window.history.length > 1) window.history.back();
    else window.location.href = "/";
  };

  return (
    <>
      <header
        className="pmc-mobile-topbar"
        data-testid="pmc-mobile-topbar"
        role="banner"
      >
        {showBack ? (
          <button
            type="button"
            className="pmc-mob-back"
            onClick={goBack}
            aria-label="Go back"
            data-testid="pmc-mobile-back"
          >
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <polyline points="15 6 9 12 15 18" />
            </svg>
          </button>
        ) : null}
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
          <button
            type="button"
            onClick={triggerInstall}
            className="primary"
            data-testid="pmc-mobile-menu-install"
            style={{
              background: "#d9bd72",
              color: "#1b1606",
              border: 0,
              cursor: "pointer",
              font: "inherit",
              display: "inline-flex",
              justifyContent: "center",
              alignItems: "center",
              minHeight: 46,
              padding: "0 16px",
              borderRadius: 6,
              fontWeight: 600,
              gap: 8,
            }}
          >
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M12 3v12" />
              <path d="m7 10 5 5 5-5" />
              <path d="M5 21h14" />
            </svg>
            Install app
          </button>
          {installSteps && (
            <div
              data-testid="pmc-mobile-menu-install-steps"
              style={{
                fontSize: 12,
                lineHeight: "18px",
                color: "#f3efe4",
                background: "rgba(217,189,114,0.08)",
                border: "1px solid rgba(217,189,114,0.35)",
                padding: "10px 12px",
                borderRadius: 6,
              }}
            >
              <div style={{ fontWeight: 700, marginBottom: 6, color: "#d9bd72", fontSize: 13 }}>
                {installSteps.title}
              </div>
              <ol style={{ margin: 0, paddingLeft: 18, display: "grid", gap: 4 }}>
                {installSteps.steps.map((s, i) => (
                  <li key={i}>{s}</li>
                ))}
              </ol>
            </div>
          )}
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
