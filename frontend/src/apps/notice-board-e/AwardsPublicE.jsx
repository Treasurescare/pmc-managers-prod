import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useUiTheme } from "@/context/UiThemeContext";
import { usePublicNav } from "@/lib/pmcEPublicNav";
import { publicApi } from "@/lib/api";
import PmcSocialLinks from "@/components/PmcSocialLinks";

function money(v, ccy) {
  if (v == null) return "—";
  try {
    return new Intl.NumberFormat("en-US", { style: "currency", currency: ccy || "USD", maximumFractionDigits: 0 }).format(v);
  } catch { return `${ccy || ""} ${Number(v).toLocaleString()}`; }
}
function fmtDate(iso) {
  if (!iso) return "—";
  try { return new Date(iso).toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" }); }
  catch { return "—"; }
}

export default function AwardsPublicE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  usePublicNav(isE);
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isE) return;
    setLoading(true);
    publicApi.listNotices({ status: "awarded", limit: 100 })
      .then((res) => {
        const rows = (res.items || []).filter(
          (n) => n.status === "awarded" || n.awarded_at || n.award_value != null
        );
        setItems(rows);
      })
      .catch(() => setItems([]))
      .finally(() => setLoading(false));
  }, [isE]);

  const kpi = useMemo(() => {
    const total = items.reduce((s, n) => s + (Number(n.award_value ?? n.budget_amount) || 0), 0);
    const bids = items.map((n) => Number(n.bids_count)).filter((x) => !Number.isNaN(x));
    const avg = bids.length ? (bids.reduce((a, b) => a + b, 0) / bids.length).toFixed(1) : "—";
    return { count: items.length, total, avg };
  }, [items]);

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="awards-public-e" data-pmc-e-page="awards-public-e">
      <header className="pmc-chrome pmc-top"><div className="pmc-wrap pmc-top__in">
        <Link to="/" className="pmc-brand"><span className="pmc-brand__n">PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></Link>
        <nav className="pmc-nav">
          <Link to="/tenders/all" className="is-on">Tenders</Link>
          <Link to="/suppliers">For suppliers</Link>
          <Link to="/buyers">For buyers</Link>
          <Link to="/trust">Trust &amp; security</Link>
          <Link to="/help">Help &amp; FAQs</Link>
        </nav>
        <div className="pmc-top__act">
          <button className="pmc-btn pmc-btn--onchrome pmc-btn--sm"><svg className="pmc-ico" aria-hidden="true"><use href="#i-globe" /></svg> EN</button>
          <Link to="/login" className="pmc-btn pmc-btn--onchrome" data-testid="awards-topbar-signin">Sign in</Link>
          <Link to="/register" className="pmc-btn pmc-btn--brass" data-testid="awards-topbar-register">Register as supplier</Link>
        </div>
      </div></header>
      <section className="pmc-chrome" style={{ padding: "36px 0 40px" }}><div className="pmc-wrap">
        <div className="pmc-crumb"><Link to="/tenders/all">Tender notices</Link>/<span>Completed &amp; awarded</span></div>
        <h1 className="pmc-display" style={{ fontSize: "52px", lineHeight: "56px", margin: "10px 0 12px" }}>Completed &amp; awarded</h1>
        <p className="pmc-muted" style={{ fontSize: "18px", lineHeight: "30px", margin: 0, maxWidth: "720px" }}>Every award is published with the winning value, the number of bids and a verifiable ledger reference. Losing bidders see their own ranking in their portal.</p>
      </div></section>

      <div className="pmc-wrap" style={{ padding: "32px 0 72px", display: "grid", gap: "28px" }}>
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4,1fr)", gap: "16px" }}>
          <div className="pmc-kpi pmc-panel" style={{ padding: "18px 20px" }}><div className="pmc-eyebrow" style={{ color: "var(--ink-muted)" }}>Awarded in 2026</div><div className="pmc-figure" style={{ marginTop: "8px" }} data-testid="awards-kpi-count">{loading ? "…" : kpi.count}</div></div>
          <div className="pmc-panel" style={{ padding: "18px 20px" }}><div className="pmc-eyebrow" style={{ color: "var(--ink-muted)" }}>Total awarded value</div><div className="pmc-figure" style={{ marginTop: "8px" }} data-testid="awards-kpi-value">{loading ? "…" : money(kpi.total)}</div></div>
          <div className="pmc-panel" style={{ padding: "18px 20px" }}><div className="pmc-eyebrow" style={{ color: "var(--ink-muted)" }}>Average bids per tender</div><div className="pmc-figure" style={{ marginTop: "8px" }}>{loading ? "…" : kpi.avg}</div></div>
          <div className="pmc-panel" style={{ padding: "18px 20px" }}><div className="pmc-eyebrow" style={{ color: "var(--ink-muted)" }}>Closed without award</div><div className="pmc-figure" style={{ marginTop: "8px" }}>0</div></div>
        </div>

        <section className="pmc-panel">
          <div className="pmc-panel__head"><h2 className="pmc-panel__title">Recent awards</h2></div>
          {loading ? (
            <div style={{ padding: "28px" }} className="pmc-muted" data-testid="awards-loading">Loading awards…</div>
          ) : items.length === 0 ? (
            <div style={{ padding: "40px 28px", textAlign: "center" }} className="pmc-muted" data-testid="awards-empty">
              <b>No awards published yet.</b>
              <div style={{ marginTop: 6 }}>Completed tender awards will appear here with their winning value and ledger reference.</div>
            </div>
          ) : (
            <table className="pmc-table" data-testid="awards-table">
              <thead><tr><th>Tender</th><th>Delivery</th><th className="num">Award value</th><th className="num">Bids</th><th>Awarded</th><th>Status</th></tr></thead>
              <tbody>
                {items.map((n) => (
                  <tr key={n.notice_ref || n.id} data-testid={`awards-row-${n.notice_ref || n.id}`}>
                    <td><div style={{ fontWeight: 600 }}>{n.title}</div><span className="pmc-ref">{n.notice_ref}</span></td>
                    <td>{n.delivery_country || "—"}</td>
                    <td className="num" style={{ fontWeight: 600 }}>{money(n.award_value ?? n.budget_amount, n.budget_currency)}</td>
                    <td className="num">{n.bids_count ?? "—"}</td>
                    <td>{fmtDate(n.awarded_at)}</td>
                    <td><span className="pmc-pill pmc-pill--success">Awarded</span></td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </section>
      </div>
      <footer className="pmc-chrome" style={{ padding: "40px 0 28px", marginTop: "0" }}><div className="pmc-wrap" style={{ display: "flex", justifyContent: "space-between", alignItems: "center", fontSize: "13px" }}>
        <div className="pmc-brand"><span className="pmc-brand__n" style={{ fontSize: "20px" }}>PMC Managers</span><span className="pmc-brand__s">Global Tender Board</span></div><PmcSocialLinks />
        <div style={{ display: "flex", flexDirection: "row", alignItems: "center", gap: "20px" }} className="pmc-fcol"><Link to="/tenders/all">Open notices</Link><Link to="/help">Help Centre</Link><Link to="/trust">Trust &amp; security</Link><Link to="/privacy">Privacy</Link><span className="pmc-muted">© 2026 PMC Managers Limited</span></div>
      </div></footer>
    </div>
  );
}
