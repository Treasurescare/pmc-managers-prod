import { Link, useLocation, useNavigate } from "react-router-dom";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import LangSwitcher from "@/apps/shared/LangSwitcher";
import { buyerApi } from "@/lib/buyerApi";
import { showApiError } from "@/lib/api";

const NAV = [
  ["/buyer", "Dashboard", "i-home"], ["/buyer/watchlist", "Watchlist", "i-eye"], ["/buyer/bids", "Bids & auctions", "i-gavel"], ["/buyer/orders", "Purchases & deliveries", "i-box"],
  ["/buyer/payments", "Payments & refunds", "i-coin"], ["/market", "Browse marketplace", "i-search"],
];
const NAV2 = [["/buyer/notifications", "Notifications", "i-bell"], ["/buyer/team", "My team", "i-users"], ["/buyer/profile", "Profile & security", "i-settings"]];

const Ctx = createContext(null);
export const useBuyer = () => useContext(Ctx);

function AvatarMenu({ me, setMe }) {
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const ref = useRef(null);
  const file = useRef(null);
  useEffect(() => {
    if (!open) return undefined;
    const h = (e) => { if (ref.current && !ref.current.contains(e.target)) setOpen(false); };
    document.addEventListener("mousedown", h);
    return () => { document.removeEventListener("mousedown", h); };
  }, [open]);
  const onPhoto = (e) => {
    const f = e.target.files?.[0];
    e.target.value = "";
    if (!f) return;
    if (f.size > 400 * 1024) { toast.error("Photo must be under 400 KB"); return; }
    const r = new FileReader();
    r.onload = () => buyerApi.avatar(r.result).then(() => { setMe({ ...me, avatar_data_url: r.result }); toast.success("Profile photo updated"); }).catch(showApiError);
    r.readAsDataURL(f);
  };
  const out = async () => { try { await buyerApi.logout(); } catch { /* ignore */ } nav("/login?role=buyer", { replace: true }); };
  const ini = (me?.name || me?.email || "B").split(/\s+/).map((w) => w[0]).join("").slice(0, 2).toUpperCase();
  const go = (to) => { setOpen(false); nav(to); };
  return (
    <div ref={ref} style={{ position: "relative" }}>
      <button type="button" className="pmc-who" onClick={() => setOpen(!open)} data-testid="buyer-who" style={{ background: "transparent", border: 0, cursor: "pointer" }}>
        <span className="pmc-avatar" style={{ overflow: "hidden" }}>{me?.avatar_data_url ? <img src={me.avatar_data_url} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : ini}</span>
        <span className="pmc-who__t"><b data-testid="buyer-who-name">{me?.name || "Buyer"}</b><span>{me?.org?.name || "Awaiting verification"}</span></span>
      </button>
      {open && (
        <div role="menu" className="pmc-avatar-menu" data-testid="buyer-avatar-menu" style={{ position: "absolute", right: 0, top: "calc(100% + 8px)", width: 250, zIndex: 1200, background: "#fff", color: "#1a2b27", border: "1px solid var(--line)", borderRadius: "var(--radius-md)", boxShadow: "var(--shadow-2)", padding: 8, display: "grid", gap: 2 }}>
          <div style={{ padding: "8px 10px", borderBottom: "1px solid var(--line)" }}><b style={{ fontSize: 14 }}>{me?.name}</b><div className="pmc-muted" style={{ fontSize: 12 }}>{me?.email}</div></div>
          <input ref={file} type="file" accept="image/png,image/jpeg,image/webp" hidden onChange={onPhoto} data-testid="buyer-avatar-file" />
          <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ justifyContent: "flex-start" }} onClick={() => go("/buyer/profile")} data-testid="buyer-menu-profile">Edit profile</button>
          <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ justifyContent: "flex-start" }} onClick={() => file.current?.click()} data-testid="buyer-menu-photo">Change photo</button>
          <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ justifyContent: "flex-start" }} onClick={() => go("/buyer/profile#password")} data-testid="buyer-menu-password">Change password</button>
          <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ justifyContent: "flex-start", color: "var(--danger)" }} onClick={out} data-testid="buyer-menu-signout">Sign out</button>
        </div>)}
    </div>);
}

export default function BuyerChrome({ children }) {
  const loc = useLocation();
  const nav = useNavigate();
  const [me, setMe] = useState(null);
  const [unread, setUnread] = useState(0);
  const refreshUnread = useCallback(() => buyerApi.notifications().then((r) => setUnread(r.unread)).catch(() => {}), []);
  useEffect(() => {
    buyerApi.me().then(setMe).catch(() => nav(`/login?role=buyer&next=${encodeURIComponent(loc.pathname)}`, { replace: true }));
  }, [nav, loc.pathname]);
  useEffect(() => { refreshUnread(); }, [loc.pathname, refreshUnread]);
  if (!me) return <div className="p-10 text-sm opacity-60" data-testid="buyer-loading">Loading your buyer portal…</div>;
  const link = ([to, label, icon]) => (
    <Link key={to} to={to} aria-current={loc.pathname === to ? "page" : undefined} data-testid={`buyer-nav-${label.toLowerCase().replace(/[^a-z]+/g, "-")}`}>
      <svg className="pmc-ico" aria-hidden="true"><use href={`#${icon}`} /></svg>{label}
      {to === "/buyer/notifications" && unread > 0 && <span className="c hot" data-testid="buyer-nav-unread">{unread}</span>}
    </Link>);
  return (
    <Ctx.Provider value={{ me, setMe, refreshUnread }}>
      <header className="pmc-chrome pmc-vtop">
        <Link to="/buyer" className="pmc-brand" data-testid="buyer-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Buyer portal</span></Link>
        <div className="pmc-vtop__r">
          <button className="pmc-btn pmc-btn--onchrome" data-help-open=""><svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg> Help</button>
          <LangSwitcher dark />
          <Link to="/buyer/notifications" className="pmc-iconbtn pmc-bell" aria-label="Notifications" data-testid="buyer-bell" style={{ position: "relative" }}>
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-bell" /></svg>
            {unread > 0 && <span data-testid="buyer-bell-count" style={{ position: "absolute", top: -4, right: -4, background: "#b3261e", color: "#fff", borderRadius: 999, fontSize: 10, minWidth: 16, height: 16, display: "grid", placeItems: "center", padding: "0 4px" }}>{unread}</span>}
          </Link>
          <AvatarMenu me={me} setMe={setMe} />
        </div>
      </header>
      <div className="pmc-app">
        <nav className="pmc-lnav" aria-label="Buyer">
          {NAV.map(link)}<hr />{NAV2.map(link)}
          <div className="pmc-desk"><b>Your PMC desk</b><div className="pmc-muted">Questions on a purchase?</div><a href="mailto:tenders@pmcmanagers.com">tenders@pmcmanagers.com</a></div>
        </nav>
        <main className="pmc-main">
          {!me.verified && <div className="border border-amber-600/40 bg-amber-50 text-amber-950 rounded p-3 text-sm mb-4" data-testid="buyer-pending-banner">PMC is verifying your buyer account. You can browse the marketplace now; bidding and buying unlock once you are verified (we'll notify you).</div>}
          {children}
        </main>
      </div>
      <footer className="pmc-chrome" style={{ padding: "20px 0" }} data-testid="buyer-footer"><div className="pmc-wrap" style={{ display: "flex", justifyContent: "space-between", flexWrap: "wrap", gap: 12, fontSize: 13 }}>
        <span>PMC Managers · Buyer portal</span>
        <span style={{ display: "flex", gap: 16, flexWrap: "wrap", whiteSpace: "nowrap" }}><Link to="/market">Marketplace</Link><Link to="/help">Help Centre</Link><Link to="/privacy">Privacy</Link><span className="pmc-muted">© 2026 PMC Managers Limited</span></span>
      </div></footer>
    </Ctx.Provider>);
}
