import { Link, useLocation, useNavigate } from "react-router-dom";
import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { vendorApi, showApiError } from "@/lib/api";

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
  const navigate = useNavigate();
  const [me, setMe] = useState(null);
  const [menuOpen, setMenuOpen] = useState(false);
  const menuRef = useRef(null);
  const fileRef = useRef(null);
  useEffect(() => {
    vendorApi.me().then(setMe).catch(() => {});
  }, []);
  // v50o — close the avatar dropdown on outside-click / Esc.
  useEffect(() => {
    if (!menuOpen) return;
    const onDoc = (e) => { if (menuRef.current && !menuRef.current.contains(e.target)) setMenuOpen(false); };
    const onEsc = (e) => { if (e.key === "Escape") setMenuOpen(false); };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onEsc);
    };
  }, [menuOpen]);
  const initials = (me?.company_name || me?.email || "V")
    .split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();

  const onPhoto = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 400 * 1024) { toast.error("Photo must be under 400 KB"); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        await vendorApi.uploadAvatar(reader.result);
        setMe((m) => ({ ...m, avatar_data_url: reader.result }));
        toast.success("Profile photo updated");
      } catch (err) { showApiError(err); }
    };
    reader.readAsDataURL(f);
    e.target.value = "";
  };

  const onSignOut = async () => {
    try { await vendorApi.logout(); } catch {}
    navigate("/vendor/login", { replace: true });
  };

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
          <div ref={menuRef} style={{ position: "relative" }}>
            <button type="button" className="pmc-who" aria-haspopup="menu"
                    aria-expanded={menuOpen}
                    data-testid="vendor-who-link"
                    onClick={() => setMenuOpen((o) => !o)}
                    style={{ cursor: "pointer", background: "transparent", border: 0 }}>
              <span className="pmc-avatar" style={{ overflow: "hidden" }}>
                {me?.avatar_data_url
                  ? <img src={me.avatar_data_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} />
                  : initials}
              </span>
              <span className="pmc-who__t">
                <b data-testid="vendor-who-name">{me?.company_name || "Supplier"}</b>
                <span>{me?.vendor_ref || ""}</span>
              </span>
            </button>
            {menuOpen && (
              <div role="menu" data-testid="vendor-avatar-menu" style={{
                position: "absolute", right: 0, top: "calc(100% + 8px)", width: 260, zIndex: 60,
                background: "var(--surface)", border: "1px solid var(--line)",
                borderRadius: "var(--radius-md)", boxShadow: "var(--shadow-2)",
                padding: 8, display: "grid", gap: 2,
              }}>
                <div style={{ padding: "10px 10px 12px", borderBottom: "1px solid var(--line)", marginBottom: 6 }}>
                  <div style={{ fontWeight: 600, fontSize: 14, overflow: "hidden",
                                textOverflow: "ellipsis", whiteSpace: "nowrap" }}
                       data-testid="vendor-menu-company">{me?.company_name || "Supplier"}</div>
                  <div className="pmc-muted" style={{ fontSize: 12 }}>{me?.email}</div>
                </div>
                <input ref={fileRef} type="file" accept="image/*" hidden onChange={onPhoto}
                       data-testid="vendor-avatar-file" />
                <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                        style={{ justifyContent: "flex-start" }}
                        data-testid="vendor-menu-change-profile"
                        onClick={() => { setMenuOpen(false); navigate("/vendor/company"); }}>
                  Change profile
                </button>
                <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                        style={{ justifyContent: "flex-start" }}
                        data-testid="vendor-menu-change-photo"
                        onClick={() => fileRef.current?.click()}>
                  Change photo
                </button>
                <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                        style={{ justifyContent: "flex-start" }}
                        data-testid="vendor-menu-change-password"
                        onClick={() => { setMenuOpen(false); navigate("/vendor/change-password"); }}>
                  Change password
                </button>
                <div style={{ borderTop: "1px solid var(--line)", marginTop: 6, paddingTop: 6 }}>
                  <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm"
                          style={{ justifyContent: "flex-start", color: "var(--danger)" }}
                          data-testid="vendor-menu-sign-out" onClick={onSignOut}>
                    Sign out
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      </header>
      <div className="pmc-app">
        <nav className="pmc-lnav" aria-label="Supplier">
          {NAV.map(renderLink)}
          <hr />
          {NAV_SECONDARY.map(renderLink)}
          <button type="button" className="pmc-lnav__helpbtn" data-help-open=""
                  data-testid="vendor-nav-help"
                  style={{ background: "transparent", border: 0, textAlign: "left",
                           cursor: "pointer", padding: 0, font: "inherit", color: "inherit",
                           display: "flex", alignItems: "center", gap: 10,
                           width: "100%" }}>
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>Help &amp; FAQs
          </button>
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
