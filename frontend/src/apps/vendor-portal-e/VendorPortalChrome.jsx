import { Link, useLocation } from "react-router-dom";
import { useEffect, useState } from "react";
import { vendorApi } from "@/lib/api";

/**
 * Shared Supplier-portal chrome (top bar + left nav) for Option E pages.
 * Replaces per-page static mockups where every link was href="#" — now
 * each nav item is a real React Router `<Link>` with aria-current wired to
 * the active route.
 */
const NAV = [
  { to: "/vendor",            label: "Home",             icon: "i-home" },
  { to: "/vendor/tenders",    label: "Find tenders",     icon: "i-search" },
  { to: "/vendor/mybids",     label: "My bids",          icon: "i-gavel" },
  { to: "/vendor/emd",        label: "EMD & payments",   icon: "i-coin" },
  { to: "/vendor/signatures", label: "Signatures",       icon: "i-sign" },
];
const NAV_SECONDARY = [
  { to: "/vendor/company",    label: "Company & KYC",    icon: "i-shield" },
  { to: "/vendor/categories", label: "Categories",       icon: "i-tag" },
  { to: "/vendor/reviews",    label: "Reviews",          icon: "i-users" },
  { to: "/vendor/account",    label: "Account & security", icon: "i-settings" },
];

export default function VendorPortalChrome({ active, counts = {}, children }) {
  const location = useLocation();
  const [me, setMe] = useState(null);
  useEffect(() => {
    vendorApi.me().then(setMe).catch(() => {});
  }, []);
  const initials = (me?.company_name || me?.email || "V")
    .split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  const renderLink = (item) => {
    const isActive = active ? active === item.to : location.pathname === item.to;
    const count = counts[item.to];
    return (
      <Link key={item.to} to={item.to}
        aria-current={isActive ? "page" : undefined}
        data-testid={`vendor-nav-${item.to.replace(/\//g, "-").replace(/^-/, "")}`}>
        <svg className="pmc-ico" aria-hidden="true"><use href={`#${item.icon}`} /></svg>
        {item.label}
        {count != null && <span className={"c" + (count > 0 && item.label === "My bids" ? " hot" : "")}>{count}</span>}
      </Link>
    );
  };

  return (
    <>
      <header className="pmc-chrome pmc-vtop">
        <Link to="/vendor" className="pmc-brand" data-testid="vendor-brand-link">
          <span className="pmc-brand__n">PMC Managers</span>
          <span className="pmc-brand__s">Supplier portal</span>
        </Link>
        <label className="pmc-search pmc-cmd">
          <svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>
          <input placeholder="Search tenders, bids, documents…" />
          <span className="pmc-kbd">Ctrl K</span>
        </label>
        <div className="pmc-vtop__r">
          <button className="pmc-btn pmc-btn--onchrome" data-help-open="">
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help
          </button>
          <Link to="/vendor/alerts" className="pmc-iconbtn pmc-bell" aria-label="Alerts"
                data-testid="vendor-alerts-link">
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg>
          </Link>
          <Link to="/vendor/account" className="pmc-who" aria-haspopup="menu"
                data-testid="vendor-who-link">
            <span className="pmc-avatar">{initials}</span>
            <span className="pmc-who__t">
              <b>{me?.company_name || "Supplier"}</b>
              <span>{me?.vendor_ref || ""}</span>
            </span>
          </Link>
        </div>
      </header>
      <div className="pmc-app">
        <nav className="pmc-lnav" aria-label="Supplier">
          {NAV.map(renderLink)}
          <hr />
          {NAV_SECONDARY.map(renderLink)}
          <a href="#" data-help-open="">
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs
          </a>
          <div className="pmc-desk">
            <b>Your PMC desk</b>
            <div className="pmc-muted">Questions on a tender or bid?</div>
            <a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a>
          </div>
        </nav>
        <main className="pmc-main">{children}</main>
      </div>
    </>
  );
}
