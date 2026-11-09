import { useEffect, useState } from "react";
import { useLocation, useNavigate, NavLink, Link } from "react-router-dom";
import { pmcInstallSteps, detectPmcBrowser } from "@/lib/pmcInstallInstructions";
import { adminApi, vendorApi, api } from "@/lib/api";

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
  { to: "/market", label: "Marketplace" },
  { to: "/suppliers", label: "For suppliers" },
  { to: "/buyers", label: "For buyers" },
  { to: "/trust", label: "Trust & security" },
  { to: "/help", label: "Help & FAQs" },
  { to: "/contact", label: "Contact" },
];

export default function PmcMobileNav() {
  const { pathname } = useLocation();
  const navigate = useNavigate();
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

  // v51g — fetch the vendor profile for the top-bar avatar initials.
  const [vendorMe, setVendorMe] = useState(null);
  useEffect(() => {
    const onVendor = pathname === "/vendor" || pathname.startsWith("/vendor/");
    if (!onVendor || pathname === "/vendor/login") return;
    let live = true;
    // v52bv — skip the global 401→/login redirect: this probe fires on
    // public pages like /vendor/services and must fail silently.
    api.get("/api/v1/vendor/auth/me", { _skipAuthRedirect: true })
      .then((r) => { if (live) setVendorMe(r.data); }).catch(() => {});
    return () => { live = false; };
  }, [pathname]);

  // Route classification
  const isAdminLogin = pathname === "/admin/login";
  const isVendorLogin = pathname === "/vendor/login" || pathname === "/login" || pathname === "/forgot-password" || pathname === "/reset-password" || pathname === "/register";
  const isVendor = pathname === "/vendor" || pathname.startsWith("/vendor/");
  const isAdmin = pathname.startsWith("/admin");
  const isStaff = pathname.startsWith("/staff");
  const isEscrow = pathname.startsWith("/escrow");
  const isM = pathname.startsWith("/m");

  // Suppress mobile chrome on:
  //  - vendor/admin login pages (they already have their own centered form)
  //  - /m/* mobile showcase routes
  //  - /staff and /escrow/* — these now use PortalShellE, which owns the full
  //    responsive top bar + off-canvas drawer (one hamburger, one sign-out).
  //    Rendering the generic mobile chrome here produced a duplicate header,
  //    a duplicate sign-out and (for escrow) the wrong public menu.
  if (isVendorLogin || isAdminLogin || isM || isStaff || isEscrow) return null;

  // v51e — unified Sign-out for mobile vendor + admin top bar.
  const doSignOut = async () => {
    try {
      await Promise.allSettled([
        isAdmin || isStaff ? adminApi.logout?.() : vendorApi.logout?.(),
      ].filter(Boolean));
    } catch (_) { /* ignore */ }
    try { sessionStorage.clear(); } catch (_) { /* noop */ }
    navigate("/login", { replace: true });
  };

  // v51e — back navigation shared by every mobile top bar.
  const goBackUniversal = () => {
    if (window.history.length > 1) window.history.back();
    else window.location.href = (isAdmin || isStaff) ? "/admin" : (isVendor ? "/vendor" : "/");
  };

  // For vendor pages (post-login): mobile top bar (back + hamburger w/ Sign out)
  // + bottom tab bar. Earlier releases rendered ONLY the bottom bar — users
  // reported there was no way to sign out and no back button on mobile.
  if (isVendor) {
    const showBack = pathname !== "/vendor";
    return (
      <>
        {/* v51g — user-requested layout: hamburger top-LEFT, avatar + Sign out
            always visible top-RIGHT (no drawer needed to sign out). */}
        <header className="pmc-mobile-topbar" data-testid="pmc-mobile-topbar-vendor" role="banner">
          <button type="button" className="pmc-mob-hamburger"
                  onClick={() => setMenuOpen((o) => !o)} aria-label="Open menu"
                  data-testid="pmc-mobile-menu-open">
            <svg viewBox="0 0 24 24" aria-hidden="true">
              <line x1="4" y1="7" x2="20" y2="7" />
              <line x1="4" y1="12" x2="20" y2="12" />
              <line x1="4" y1="17" x2="20" y2="17" />
            </svg>
          </button>
          {showBack ? (
            <button type="button" className="pmc-mob-back" onClick={goBackUniversal}
                    aria-label="Go back" data-testid="pmc-mobile-back">
              <svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="15 6 9 12 15 18" /></svg>
            </button>
          ) : null}
          <Link to="/vendor" className="pmc-mob-brand pmc-mob-brand--wm" data-testid="pmc-mobile-brand">
            <img src="/pmc-wordmark-gold.png" alt="PMC Managers · Global Tender Grid" /><span>Supplier portal</span>
          </Link>
          <div style={{ marginLeft: "auto", display: "flex", alignItems: "center", gap: 6 }}>
            <Link to="/vendor/alerts" className="pmc-mob-bell"
                  aria-label="Notifications & alerts"
                  data-testid="pmc-mobile-bell"
                  style={{ display: "inline-grid", placeItems: "center",
                           width: 36, height: 36, color: "#f3efe4", textDecoration: "none",
                           borderRadius: 6, border: "1px solid rgba(243,239,228,0.25)" }}>
              <svg width="19" height="19" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
                <path d="M10 21a2 2 0 0 0 4 0" />
              </svg>
            </Link>
            <Link to="/vendor/account" className="pmc-mob-avatar"
                  aria-label="My account"
                  data-testid="pmc-mobile-avatar"
                  style={{ width: 32, height: 32, borderRadius: "50%",
                           display: "inline-grid", placeItems: "center",
                           background: "rgba(217,189,114,0.2)", color: "#d9bd72",
                           border: "1px solid rgba(217,189,114,0.5)",
                           fontSize: 12, fontWeight: 700, textDecoration: "none" }}>
              {(vendorMe?.company_name || vendorMe?.email || "V").trim().slice(0, 2).toUpperCase()}
            </Link>
            <button type="button" onClick={doSignOut}
                    data-testid="pmc-mobile-signout"
                    aria-label="Sign out"
                    style={{ background: "transparent", whiteSpace: "nowrap",
                             border: "1px solid rgba(217,189,114,0.6)", color: "#f3efe4",
                             padding: "7px 10px", borderRadius: 6, fontSize: 12,
                             fontWeight: 700, cursor: "pointer" }}>
              Sign out
            </button>
          </div>
        </header>

        <div className="pmc-mobile-menu-scrim" onClick={() => setMenuOpen(false)}
             aria-hidden={!menuOpen} />
        <aside className="pmc-mobile-menu-drawer" role="dialog" aria-modal="true"
               aria-label="Vendor menu" aria-hidden={!menuOpen}
               data-testid="pmc-mobile-menu-drawer-vendor">
          <div className="pmc-mob-menu-head">
            <div className="pmc-mob-brand"><b>Supplier menu</b><span>&nbsp;</span></div>
            <button type="button" className="pmc-mob-menu-close"
                    onClick={() => setMenuOpen(false)} aria-label="Close menu">×</button>
          </div>
          <nav aria-label="Supplier">
            <NavLink to="/vendor" end data-testid="pmc-mobile-menu-link-home">Home</NavLink>
            <NavLink to="/vendor/tenders" data-testid="pmc-mobile-menu-link-tenders">Find tenders</NavLink>
            <NavLink to="/vendor/ai-tools" data-testid="pmc-mobile-menu-link-ai-tools">AI tender tools</NavLink>
            <NavLink to="/vendor/tender-builder" data-testid="pmc-mobile-menu-link-tender-builder">Prepare tender</NavLink>
            <NavLink to="/vendor/mybids" data-testid="pmc-mobile-menu-link-mybids">My bids</NavLink>
            <NavLink to="/vendor/auctions" data-testid="pmc-mobile-menu-link-auctions">Reverse auctions</NavLink>
            <NavLink to="/vendor/consortia" data-testid="pmc-mobile-menu-link-consortia">Consortia</NavLink>
            <NavLink to="/vendor/market" data-testid="pmc-mobile-menu-link-market">Sell products</NavLink>
            <NavLink to="/vendor/emd" data-testid="pmc-mobile-menu-link-emd">EMD &amp; payments</NavLink>
            <NavLink to="/vendor/signatures" data-testid="pmc-mobile-menu-link-signatures">Signatures</NavLink>
            <hr />
            <NavLink to="/vendor/company" data-testid="pmc-mobile-menu-link-company">Company &amp; KYC</NavLink>
            <NavLink to="/vendor/categories" data-testid="pmc-mobile-menu-link-categories">Categories</NavLink>
            <NavLink to="/vendor/saved-alerts" data-testid="pmc-mobile-menu-link-saved-alerts">Saved alerts</NavLink>
            <NavLink to="/vendor/listing" data-testid="pmc-mobile-menu-link-listing">Directory listing</NavLink>
            <NavLink to="/vendor/data-intel" data-testid="pmc-mobile-menu-link-data-intel">Data intel</NavLink>
            <NavLink to="/vendor/messages" data-testid="pmc-mobile-menu-link-messages">Messages</NavLink>
            <NavLink to="/vendor/refer" data-testid="pmc-mobile-menu-link-refer">Refer &amp; earn</NavLink>
            <NavLink to="/vendor/services" data-testid="pmc-mobile-menu-link-services">Services</NavLink>
            <NavLink to="/vendor/reviews" data-testid="pmc-mobile-menu-link-reviews">Reviews</NavLink>
            <NavLink to="/vendor/account" data-testid="pmc-mobile-menu-link-account">Account &amp; security</NavLink>
            <NavLink to="/vendor/alerts" data-testid="pmc-mobile-menu-link-alerts">Alerts</NavLink>
            <NavLink to="/help" data-testid="pmc-mobile-menu-link-help">Help &amp; FAQs</NavLink>
          </nav>
          <div className="pmc-mob-menu-cta">
            <button type="button" onClick={doSignOut}
                    data-testid="pmc-mobile-menu-signout"
                    style={{ background: "#d9bd72", color: "#1b1606", border: 0,
                             minHeight: 48, borderRadius: 6, fontWeight: 700,
                             fontSize: 15, cursor: "pointer", padding: "0 16px",
                             display: "inline-flex", justifyContent: "center",
                             alignItems: "center", gap: 10, width: "100%" }}>
              <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
                <path d="M14 4h5v16h-5" />
                <path d="M10 8l-4 4 4 4" />
                <path d="M6 12h10" />
              </svg>
              Sign out
            </button>
          </div>
        </aside>
      </>
    );
  }

  // v51e — Admin / staff mobile: compact top bar with Back + Sign out so the
  // admin console is usable from a phone (desktop sidebar is too wide to
  // render here).
  if (isAdmin || isStaff) {
    return (
      <header className="pmc-mobile-topbar" data-testid="pmc-mobile-topbar-admin" role="banner">
        <button type="button" className="pmc-mob-back" onClick={goBackUniversal}
                aria-label="Go back" data-testid="pmc-mobile-back">
          <svg viewBox="0 0 24 24" aria-hidden="true"><polyline points="15 6 9 12 15 18" /></svg>
        </button>
        <Link to={isAdmin ? "/admin" : "/staff"} className="pmc-mob-brand pmc-mob-brand--wm"
              data-testid="pmc-mobile-brand">
          <img src="/pmc-wordmark-gold.png" alt="PMC Managers · Global Tender Grid" /><span>{isAdmin ? "Admin console" : "Staff"}</span>
        </Link>
        <button type="button" onClick={doSignOut}
                data-testid="pmc-mobile-signout"
                aria-label="Sign out"
                style={{ background: "transparent", border: "1px solid rgba(243,239,228,0.4)",
                         color: "#f3efe4", padding: "6px 10px", borderRadius: 4,
                         fontSize: 12, fontWeight: 600, cursor: "pointer" }}>
          Sign out
        </button>
      </header>
    );
  }

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
          className="pmc-mob-brand pmc-mob-brand--wm"
          data-testid="pmc-mobile-brand"
        >
          <img src="/pmc-wordmark-gold.png" alt="PMC Managers · Global Tender Grid" />
        </Link>
        <button
          type="button"
          className="pmc-mob-hamburger"
          onClick={() => setMenuOpen((o) => !o)}
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
