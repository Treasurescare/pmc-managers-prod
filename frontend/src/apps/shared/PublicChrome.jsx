import { Link, useNavigate } from "react-router-dom";
import { useEffect, useState } from "react";
import LangSwitcher from "./LangSwitcher";
import { marketApi } from "@/lib/marketApi";
import { api } from "@/lib/api";

function BuyerHeaderMenu({ me }) {
  const nav = useNavigate();
  const [open, setOpen] = useState(false);
  const out = async () => { try { await api.post("/api/v1/staff/auth/logout"); } catch { /* ignore */ } nav("/login?role=buyer"); };
  return (
    <div style={{ position: "relative" }}>
      <button type="button" className="pmc-btn pmc-btn--onchrome" onClick={() => setOpen(!open)} data-testid="public-buyer-menu">{me.user_name || me.name} ▾</button>
      {open && (
        <div className="pmc-avatar-menu" data-testid="public-buyer-menu-list" style={{ position: "absolute", right: 0, top: "calc(100% + 6px)", width: 220, zIndex: 1200, background: "var(--surface)", color: "var(--ink)", border: "1px solid var(--line)", borderRadius: 8, padding: 8, display: "grid", gap: 4 }}>
          <Link to="/buyer" data-testid="public-buyer-dashboard">My dashboard</Link>
          <Link to="/buyer/bids" data-testid="public-buyer-bids">My bids & purchases</Link>
          <button type="button" style={{ textAlign: "left", color: "var(--danger)" }} onClick={out} data-testid="public-buyer-signout">Sign out</button>
        </div>)}
    </div>);
}

/**
 * Shared public-site chrome (header + footer) matching the PMC Managers
 * landing/awards pages. Used to wrap public-facing pages so their navigation
 * is consistent with the rest of the public board.
 */
export default function PublicChrome({ active, children, testid }) {
  const is = (k) => (active === k ? "is-on" : undefined);
  const [me, setMe] = useState(null);
  useEffect(() => { marketApi.whoami().then(setMe).catch(() => {}); }, []);
  return (
    <div data-testid={testid} data-pmc-e-page="public-chrome" className="min-h-screen flex flex-col">
      <header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
        <Link to="/" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Grid</span></Link>
        <nav className="pmc-nav">
          <Link to="/tenders/all" className={is("tenders")}>Tenders</Link>
          <Link to="/tenders/global" className={is("global")}>Global tenders</Link>
          <Link to="/auctions" className={is("auctions")}>Auctions</Link>
          <Link to="/market" className={is("market")} data-testid="nav-market">Marketplace</Link>
          <Link to="/suppliers">For suppliers</Link>
          <Link to="/buyers">For buyers</Link>
          <Link to="/trust">Trust &amp; security</Link>
          <Link to="/help">Help &amp; FAQs</Link>
        </nav>
        <div className="pmc-top__act">
          <LangSwitcher dark />
          {me?.kind === "buyer" ? <BuyerHeaderMenu me={me} /> : (<>
            <Link to="/login" className="pmc-btn pmc-btn--onchrome" data-testid="public-chrome-signin">Sign in</Link>
            <Link to="/buyers/register" style={{ color: "inherit", fontSize: 13, textDecoration: "underline", whiteSpace: "nowrap" }} data-testid="public-chrome-register-buyer">Buyer? Join free</Link>
            <Link to="/register" className="pmc-btn pmc-btn--brass" data-testid="public-chrome-register">Register as supplier</Link></>)}
        </div>
      </div></header>

      <div className="flex-1 bg-brand-pale">{children}</div>

      <footer className="pmc-chrome" style={{ padding: "40px 0 28px", marginTop: "0" }}><div className="pmc-wrap" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
        <div className="pmc-brand"><span className="pmc-brand__n" style={{ fontSize: "20px" }}>PMC Managers</span><span className="pmc-brand__s">Global Tender Grid</span></div>
        <div style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: "20px" }} className="pmc-fcol"><Link to="/tenders/all">Open notices</Link><Link to="/auctions">Auctions</Link><Link to="/help">Help Centre</Link><Link to="/trust">Trust &amp; security</Link><Link to="/privacy">Privacy</Link><span className="pmc-muted">© 2026 PMC Managers Limited</span></div>
      </div></footer>
    </div>
  );
}
