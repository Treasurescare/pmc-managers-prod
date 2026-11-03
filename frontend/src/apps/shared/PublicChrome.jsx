import { Link } from "react-router-dom";

/**
 * Shared public-site chrome (header + footer) matching the PMC Managers
 * landing/awards pages. Used to wrap public-facing pages so their navigation
 * is consistent with the rest of the public board.
 */
export default function PublicChrome({ active, children, testid }) {
  const is = (k) => (active === k ? "is-on" : undefined);
  return (
    <div data-testid={testid} data-pmc-e-page="public-chrome" className="min-h-screen flex flex-col">
      <header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
        <Link to="/" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Grid</span></Link>
        <nav className="pmc-nav">
          <Link to="/tenders/all" className={is("tenders")}>Tenders</Link>
          <Link to="/auctions" className={is("auctions")}>Auctions</Link>
          <Link to="/suppliers">For suppliers</Link>
          <Link to="/buyers">For buyers</Link>
          <Link to="/trust">Trust &amp; security</Link>
          <Link to="/help">Help &amp; FAQs</Link>
        </nav>
        <div className="pmc-top__act">
          <button className="pmc-btn pmc-btn--onchrome pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-globe" /></svg> EN</button>
          <Link to="/login" className="pmc-btn pmc-btn--onchrome" data-testid="public-chrome-signin">Sign in</Link>
          <Link to="/register" className="pmc-btn pmc-btn--brass" data-testid="public-chrome-register">Register as supplier</Link>
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
