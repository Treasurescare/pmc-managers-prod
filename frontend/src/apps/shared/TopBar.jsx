import { useEffect, useState } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import PmcLogo from "./PmcLogo";
import LangSwitcher from "./LangSwitcher";
import { useI18n } from "@/context/I18nContext";
import { adminApi, staffApi, vendorApi } from "@/lib/api";

/**
 * TopBar — responsive header with hamburger drawer for mobile.
 * Sign-out shows whenever the current route is inside /admin, /staff or /vendor.
 * The drawer lists every nav destination + the sign-out action so nothing is
 * hidden behind horizontal scroll on small screens.
 */
export default function TopBar({ dark = false }) {
  const { t } = useI18n();
  const nav = useNavigate();
  const location = useLocation();
  const [openDrawer, setOpenDrawer] = useState(false);

  useEffect(() => { setOpenDrawer(false); }, [location.pathname]);

  const base = dark
    ? "bg-brand-navy text-white border-white/10"
    : "bg-white text-brand-navy border-brand-navy/10";

  const path = location.pathname;
  const showSignOut =
    path.startsWith("/admin") ||
    path.startsWith("/staff") ||
    path.startsWith("/vendor");

  const signOut = async () => {
      // Best-effort logout across all three cookie realms — 401s just mean
      // "not signed in as this role", which is expected for role-scoped cookies.
      try { await adminApi.logout(); } catch (err) {
        if (process.env.NODE_ENV !== "production") console.debug("admin logout skipped:", err?.response?.status);
      }
      try { await staffApi.logout(); } catch (err) {
        if (process.env.NODE_ENV !== "production") console.debug("staff logout skipped:", err?.response?.status);
      }
      try { await vendorApi.logout(); } catch (err) {
        if (process.env.NODE_ENV !== "production") console.debug("vendor logout skipped:", err?.response?.status);
      }
    toast.success(t("nav.logout"));
    nav("/login");
  };

  const NAV = [
    ["/notices", t("nav.notices"), "nav-notices"],
    ["/register", t("nav.register"), "nav-register"],
    ["/register/status", t("nav.status"), "nav-status"],
    ["/login", t("nav.login"), "nav-signin"],
  ];

  return (
    <>
      <header className={`w-full border-b ${base}`}>
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-10 py-3 sm:py-4 flex items-center justify-between gap-3">
          <Link to="/" className="flex items-center gap-3 min-w-0" data-testid="topbar-brand">
            <PmcLogo size={36} inverse={dark} />
            <div className="min-w-0">
              <div className="pmc-label truncate" style={{ color: dark ? "rgba(255,255,255,0.6)" : undefined }}>
                {t("brand.name")}
              </div>
              <div className={`font-display text-base sm:text-lg leading-none tracking-tight truncate ${dark ? "text-white" : "text-brand-navy"}`}>
                {t("brand.tagline")}
              </div>
            </div>
          </Link>

          {/* Desktop nav */}
          <nav className="hidden md:flex items-center gap-6 text-[13px] tracking-wide">
            {NAV.map(([to, label, tid]) => (
              <Link key={to} to={to} data-testid={tid}
                className={dark ? "text-white/80 hover:text-white" : "text-brand-navy/70 hover:text-brand-navy"}>
                {label}
              </Link>
            ))}
          </nav>

          <div className="flex items-center gap-2 sm:gap-3">
            <div className="hidden sm:block"><LangSwitcher dark={dark} /></div>

            {/* Always-visible sign out for authed routes (desktop) */}
            {showSignOut && (
              <button onClick={signOut} data-testid="topbar-signout"
                className={"hidden md:inline-block px-3 py-1.5 text-[11px] font-semibold uppercase tracking-widest border " +
                  (dark ? "border-white/30 text-white hover:bg-white hover:text-brand-navy"
                        : "border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white")}>
                {t("nav.logout")}
              </button>
            )}

            {/* Hamburger — always visible on mobile */}
            <button
              type="button"
              onClick={() => setOpenDrawer(true)}
              data-testid="topbar-hamburger"
              aria-label="Open navigation"
              className={"md:hidden inline-flex items-center justify-center w-10 h-10 border " +
                (dark ? "border-white/30 text-white" : "border-brand-navy/30 text-brand-navy")}>
              <svg width="18" height="14" viewBox="0 0 18 14" fill="none" xmlns="http://www.w3.org/2000/svg" aria-hidden="true">
                <path d="M1 1h16M1 7h16M1 13h16" stroke="currentColor" strokeWidth="2" strokeLinecap="square"/>
              </svg>
            </button>
          </div>
        </div>
      </header>

      {/* Mobile drawer */}
      {openDrawer && (
        <div className="md:hidden fixed inset-0 z-50" data-testid="topbar-drawer">
          <div className="absolute inset-0 bg-black/40" onClick={() => setOpenDrawer(false)} />
          <aside className="absolute right-0 top-0 bottom-0 w-[85%] max-w-sm bg-white shadow-2xl flex flex-col">
            <div className="flex items-center justify-between p-4 border-b border-brand-navy/10">
              <div className="flex items-center gap-2">
                <PmcLogo size={28} />
                <div className="font-display text-brand-navy text-lg leading-none">{t("brand.tagline")}</div>
              </div>
              <button onClick={() => setOpenDrawer(false)}
                aria-label="Close menu"
                data-testid="topbar-drawer-close"
                className="w-9 h-9 inline-flex items-center justify-center border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
                <svg width="14" height="14" viewBox="0 0 14 14" fill="none" aria-hidden="true">
                  <path d="M1 1l12 12M13 1L1 13" stroke="currentColor" strokeWidth="2" strokeLinecap="square"/>
                </svg>
              </button>
            </div>

            <nav className="flex-1 overflow-y-auto p-4 space-y-1">
              {NAV.map(([to, label, tid]) => (
                <Link key={to} to={to} data-testid={`drawer-${tid}`}
                  className="block px-4 py-3 text-brand-navy hover:bg-brand-navy/5 border-l-2 border-transparent hover:border-brand-navy-soft text-[15px]">
                  {label}
                </Link>
              ))}
              {showSignOut && (
                <button
                  onClick={signOut}
                  data-testid="drawer-signout"
                  className="w-full text-left mt-4 px-4 py-3 border border-red-500 text-red-600 hover:bg-red-50 uppercase tracking-widest text-[12px] font-semibold">
                  {t("nav.logout")}
                </button>
              )}
              <Link to="/login" data-testid="drawer-signin"
                className="block mt-2 px-4 py-3 bg-brand-navy text-white text-center uppercase tracking-widest text-[12px] font-semibold hover:bg-brand-navy-deep">
                {t("nav.login")}
              </Link>
            </nav>

            <div className="p-4 border-t border-brand-navy/10">
              <div className="pmc-label mb-2">Language</div>
              <LangSwitcher />
            </div>
          </aside>
        </div>
      )}
    </>
  );
}
