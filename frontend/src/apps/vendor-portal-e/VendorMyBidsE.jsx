import { useEffect, useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useUiTheme } from "@/context/UiThemeContext";
import { bidApi, showApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";

/**
 * v50s — Vendor "My bids" rewritten from the static Option-E mockup to a
 * fully live React page. Reads bidApi.mine() so every bid the vendor just
 * submitted appears here immediately (previous build patched 4 hard-coded
 * rows via DOM, so bid #5+ was invisible).
 */

const STATUS_PILL = {
  draft:         ["", "Draft"],
  submitted:     ["pmc-pill--info", "Submitted"],
  emd_pending:   ["pmc-pill--warning", "Awaiting your EMD"],
  emd_paid:      ["pmc-pill--info", "EMD paid"],
  escrow_accepted: ["pmc-pill--info", "In PMC review"],
  admin_flagged: ["pmc-pill--info", "In PMC review"],
  under_review:  ["pmc-pill--info", "Under review"],
  technical_cleared: ["pmc-pill--info", "Tech cleared"],
  escrow_pending: ["pmc-pill--info", "Escrow confirming"],
  awarded:       ["pmc-pill--success", "Awarded"],
  rejected:      ["", "Not awarded"],
  withdrawn:     ["", "Withdrawn"],
  closed:        ["", "Closed"],
};

function fmtMoney(amount, currency) {
  if (amount == null) return "—";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency", currency: currency || "USD", maximumFractionDigits: 0,
    }).format(amount);
  } catch { return `${currency || ""} ${Number(amount).toLocaleString()}`; }
}

function fmtCountdown(iso) {
  if (!iso) return "—";
  const secs = Math.max(0, Math.floor((new Date(iso) - new Date()) / 1000));
  if (secs === 0) return "Closed";
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

const ACTIVE_STATUSES = new Set(["submitted","emd_pending","emd_paid","under_review",
                                  "technical_cleared","escrow_pending",
                                  "escrow_accepted","admin_flagged","certifier_cleared",
                                  "legal_cleared","accounting_cleared","under_evaluation",
                                  "commercial_open"]);
const DRAFT_STATUSES  = new Set(["draft"]);
const CLOSED_STATUSES = new Set(["awarded","rejected","closed"]);
const WITHDRAWN_STATUSES = new Set(["withdrawn"]);

function BidRow({ b }) {
  const [cls, label] = STATUS_PILL[b.status] || ["", b.status || "—"];
  const action = (() => {
    if (b.status === "emd_pending") return { to: `/vendor/bids/${b.id}/pay`, text: "Pay EMD", primary: true };
    if (b.status === "draft")       return { to: `/vendor/workspace/${b.id}`, text: "Continue", primary: false };
    if (b.status === "awarded")     return { to: `/vendor/signatures`, text: "Sign LOA", primary: true };
    // v50u fix — /vendor/bids/:id is not a route (fell through to the notices
    // catch-all); the live bid detail page is the bid workspace.
    return { to: `/vendor/workspace/${b.id}`, text: "View", primary: false };
  })();
  return (
    <tr data-testid={`vmb-row-${b.bid_ref || b.id}`}>
      <td>
        <div style={{ fontWeight: 600 }} data-testid={`vmb-title-${b.bid_ref || b.id}`}>
          {b.notice_title || b.notice_ref}
        </div>
        <span className="pmc-ref">{b.bid_ref}</span>
      </td>
      <td className="num" style={{ fontWeight: 600 }}>
        {fmtMoney(b.price_amount, b.price_currency)}
      </td>
      <td>
        <span className={`pmc-pill ${cls}`}>{label}</span>
      </td>
      <td>
        {b.submission_deadline
          ? <span className="pmc-countdown">{fmtCountdown(b.submission_deadline)}</span>
          : <span className="pmc-muted">—</span>}
      </td>
      <td style={{ textAlign: "right" }}>
        <Link to={action.to}
              className={`pmc-btn pmc-btn--sm ${action.primary ? "pmc-btn--primary" : "pmc-btn--secondary"}`}
              data-testid={`vmb-act-${b.bid_ref || b.id}`}>
          {action.text}
        </Link>
      </td>
    </tr>
  );
}

export default function VendorMyBidsE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [bids, setBids] = useState([]);
  const [loading, setLoading] = useState(true);
  const [tab, setTab] = useState("active");

  useEffect(() => {
    if (!isE) return;
    setLoading(true);
    bidApi.mine()
      .then((rows) => setBids(Array.isArray(rows) ? rows : []))
      .catch(showApiError)
      .finally(() => setLoading(false));
  }, [isE]);

  const buckets = useMemo(() => {
    const b = { active: [], drafts: [], closed: [], withdrawn: [] };
    bids.forEach((x) => {
      if (DRAFT_STATUSES.has(x.status)) b.drafts.push(x);
      else if (WITHDRAWN_STATUSES.has(x.status)) b.withdrawn.push(x);
      else if (CLOSED_STATUSES.has(x.status)) b.closed.push(x);
      else b.active.push(x);
    });
    return b;
  }, [bids]);

  const kpis = useMemo(() => {
    const decided = bids.filter((b) => b.status === "awarded" || b.status === "rejected");
    const won = decided.filter((b) => b.status === "awarded");
    const win = decided.length ? Math.round((won.length / decided.length) * 100) : 0;
    const inPlay = buckets.active.reduce((s, b) => {
      if ((b.price_currency || "USD").toUpperCase() === "USD") return s + (b.price_amount || 0);
      return s;
    }, 0);
    const emdHeld = bids.reduce((s, b) => s + (b.emd_paid_amount || 0), 0);
    return {
      active: buckets.active.length,
      needsYou: buckets.active.filter((b) => b.status === "emd_pending").length,
      winRate: `${win}%`,
      decidedCount: decided.length,
      inPlay,
      emdHeld,
    };
  }, [bids, buckets]);

  const rows = buckets[tab] || [];

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="vendor-mybids-e" data-pmc-e-page="vendor-mybids-e">
      <VendorPortalChrome active="/vendor/mybids"
        counts={{ "/vendor/mybids": buckets.active.length }}>
        <div className="sp-head">
          <div>
            <div className="pmc-eyebrow">My bids</div>
            <h1 data-testid="vmb-heading">Every bid, and what it needs</h1>
          </div>
          <Link to="/vendor/tenders" className="pmc-btn pmc-btn--primary"
                data-testid="vmb-find-tenders">
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg> Find tenders
          </Link>
        </div>

        <div className="sp-kpis" data-testid="vmb-kpis">
          <div>
            <div className="l">Active</div>
            <div className="pmc-figure" data-testid="vmb-kpi-active">{kpis.active}</div>
            <div className="s">{kpis.needsYou ? `${kpis.needsYou} needs you` : "all up to date"}</div>
          </div>
          <div>
            <div className="l">Win rate</div>
            <div className="pmc-figure" data-testid="vmb-kpi-win">{kpis.winRate}</div>
            <div className="s">{kpis.decidedCount} decided bid{kpis.decidedCount === 1 ? "" : "s"}</div>
          </div>
          <div>
            <div className="l">Value in play (USD)</div>
            <div className="pmc-figure" data-testid="vmb-kpi-value">
              {fmtMoney(kpis.inPlay, "USD")}
            </div>
            <div className="s">across your active bids</div>
          </div>
          <div>
            <div className="l">EMD paid</div>
            <div className="pmc-figure" data-testid="vmb-kpi-emd">
              {fmtMoney(kpis.emdHeld, "USD")}
            </div>
            <div className="s">lifetime</div>
          </div>
        </div>

        <div className="pmc-tabs" style={{ marginBottom: 16 }} role="tablist"
             data-testid="vmb-tabs">
          {[
            ["active",    "Active",    buckets.active.length],
            ["drafts",    "Drafts",    buckets.drafts.length],
            ["closed",    "Closed",    buckets.closed.length],
            ["withdrawn", "Withdrawn", buckets.withdrawn.length],
          ].map(([k, label, n]) => (
            <button key={k} role="tab" aria-selected={tab === k}
                    className={"pmc-tab" + (tab === k ? " active" : "")}
                    onClick={() => setTab(k)}
                    data-testid={`vmb-tab-${k}`}>
              {label}<span className="n">{n}</span>
            </button>
          ))}
        </div>

        <section className="pmc-panel" data-testid="vmb-panel">
          {loading ? (
            <div className="p-6 text-sm pmc-muted" data-testid="vmb-loading">
              Loading your bids…
            </div>
          ) : rows.length === 0 ? (
            <div className="p-6 text-sm pmc-muted" data-testid="vmb-empty">
              {tab === "active"
                ? <>You have no active bids yet. <Link to="/vendor/tenders">Find a tender</Link> to start.</>
                : `No ${tab} bids.`}
            </div>
          ) : (
            <table className="pmc-table">
              <thead>
                <tr>
                  <th>Bid</th>
                  <th className="num">Your price</th>
                  <th>Status</th>
                  <th>Closes</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {rows.map((b) => <BidRow key={b.id || b.bid_ref} b={b} />)}
              </tbody>
            </table>
          )}
        </section>

        <div className="pmc-callout pmc-callout--info" style={{ marginTop: 16 }}>
          <svg className="pmc-ico" aria-hidden="true"><use href="#i-help" /></svg>
          <div>
            After every decision you get a <b>debrief</b>: your technical score and
            your price position against L1. Open any decided bid to see it.
          </div>
        </div>
      </VendorPortalChrome>
    </div>
  );
}
