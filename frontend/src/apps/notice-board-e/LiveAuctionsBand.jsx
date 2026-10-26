import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { reverseAuctionApi } from "@/lib/api";
import TopBar from "@/apps/shared/TopBar";

const money = (cur, v) => `${cur || "USD"} ${Number(v || 0).toLocaleString()}`;

function Countdown({ endAt }) {
  const [now, setNow] = useState(Date.now());
  useEffect(() => {
    const t = setInterval(() => setNow(Date.now()), 1000);
    return () => clearInterval(t);
  }, []);
  if (!endAt) return <span>—</span>;
  const secs = Math.max(0, Math.floor((new Date(endAt).getTime() - now) / 1000));
  const d = Math.floor(secs / 86400), h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60), s = secs % 60;
  const txt = d > 0 ? `${d}d ${h}h` : h > 0 ? `${h}h ${m}m` : `${m}m ${String(s).padStart(2, "0")}s`;
  return <span className="tabular-nums font-mono">{txt}</span>;
}

const STATUS_BADGE = {
  live: { label: "LIVE", bg: "#065f46", fg: "#fff" },
  draft: { label: "UPCOMING", bg: "#92400e", fg: "#fff" },
  closed: { label: "CLOSED", bg: "#475569", fg: "#fff" },
  awarded_published: { label: "AWARDED", bg: "#1d4ed8", fg: "#fff" },
};

function AuctionCard({ a }) {
  const badgeKey = a.award_status === "awarded_published" ? "awarded_published" : a.status;
  const badge = STATUS_BADGE[badgeKey] || STATUS_BADGE.closed;
  const isLive = a.status === "live";
  const priceLabel = isLive ? "Current lowest" : a.status === "closed" ? "Final price" : "Starting price";
  const priceVal = isLive ? a.current_price : a.status === "closed" ? a.current_price : a.starting_price;
  return (
    <Link
      to={`/auctions/${a.id}/live`}
      className="pmc-tender"
      data-testid={`public-auction-card-${a.id}`}
      style={{ display: "block", textDecoration: "none", color: "inherit" }}
    >
      <div className="pmc-tender__top" style={{ alignItems: "center" }}>
        <span className="pmc-tag" style={{ background: badge.bg, color: badge.fg }}
              data-testid={`public-auction-status-${a.id}`}>
          {badge.label}
        </span>
        <span className="pmc-tag" style={{ background: "transparent", border: "1px solid var(--line)" }}>
          {a.is_standalone ? "Reverse auction" : "Tender-backed"}
        </span>
        {isLive && (
          <span style={{ marginLeft: "auto" }} className="pmc-countdown" data-testid={`public-auction-countdown-${a.id}`}>
            <Countdown endAt={a.end_at} />
          </span>
        )}
      </div>
      <h3 className="pmc-tender__title" data-testid={`public-auction-title-${a.id}`}>{a.title}</h3>
      <div className="pmc-ref" style={{ margin: "0 0 10px" }}>{a.notice_ref}</div>
      <dl className="pmc-tender__meta" style={{ margin: "0" }}>
        <div className="is-budget">
          <dt>{priceLabel}</dt>
          <dd data-testid={`public-auction-price-${a.id}`}>{money(a.currency, priceVal)}</dd>
        </div>
        <div><dt>Invited</dt><dd>{a.invite_count ?? 0}</dd></div>
        <div><dt>Bidders</dt><dd>{a.participant_count ?? 0}</dd></div>
        <div>
          <dt>{a.status === "closed" ? "Saving" : "Floor"}</dt>
          <dd>{a.status === "closed" ? `−${a.saving_pct ?? 0}%` : money(a.currency, a.floor_price)}</dd>
        </div>
      </dl>
      {a.award_status === "awarded_published" && a.winner && (
        <div style={{ marginTop: "10px", fontSize: "13px", color: "#1d4ed8" }}
             data-testid={`public-auction-winner-${a.id}`}>
          Awarded to <b>{a.winner.company_name}</b>
        </div>
      )}
      {a.status === "closed" && a.award_status === "in_approvals" && (
        <div style={{ marginTop: "10px", fontSize: "13px", color: "var(--ink-muted)" }}
             data-testid={`public-auction-inapprovals-${a.id}`}>
          Result gone for approvals — winner published after sign-off.
        </div>
      )}
      <div className="pmc-tender__foot">
        <span className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ paddingLeft: "0" }}>
          {isLive ? "Watch live" : "View auction"} →
        </span>
      </div>
    </Link>
  );
}

/**
 * v57e — Public reverse-auction discovery.
 * variant="band"  → embedded on the landing page (live, else upcoming).
 * variant="page"  → full page at /auctions with every bucket.
 */
export default function LiveAuctionsBand({ variant = "band" }) {
  const [buckets, setBuckets] = useState({ live: null, upcoming: null, closed: null });

  useEffect(() => {
    let cancelled = false;
    const load = () => {
      Promise.all([
        reverseAuctionApi.publicList("live").catch(() => ({ items: [] })),
        reverseAuctionApi.publicList("upcoming").catch(() => ({ items: [] })),
        reverseAuctionApi.publicList("closed").catch(() => ({ items: [] })),
        reverseAuctionApi.publicList("awarded").catch(() => ({ items: [] })),
      ]).then(([live, upcoming, closed, awarded]) => {
        if (cancelled) return;
        setBuckets({
          live: live.items || [],
          upcoming: upcoming.items || [],
          closed: [...(awarded.items || []), ...(closed.items || [])],
        });
      });
    };
    load();
    const t = setInterval(load, 15000);
    return () => { cancelled = true; clearInterval(t); };
  }, []);

  const loading = buckets.live === null;
  const liveItems = buckets.live || [];
  const upcomingItems = buckets.upcoming || [];
  const closedItems = buckets.closed || [];

  const Grid = ({ items }) => (
    <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fill,minmax(260px,1fr))", gap: "20px" }}>
      {items.map((a) => <AuctionCard key={a.id} a={a} />)}
    </div>
  );

  const body = (
    <section className="pmc-wrap" style={{ padding: variant === "page" ? "40px 0 88px" : "72px 0 0" }}
             data-testid="public-live-auctions">
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "end", marginBottom: "24px" }}>
        <div>
          <div className="pmc-eyebrow">Live reverse auctions</div>
          <h2 className="pmc-display" style={{ fontSize: "40px", lineHeight: "44px", margin: "8px 0 0" }}>
            Watch prices fall in real time
          </h2>
        </div>
        {variant === "band" && (
          <Link to="/auctions" className="pmc-btn pmc-btn--secondary" data-testid="see-all-auctions-link">
            See all auctions →
          </Link>
        )}
      </div>

      {loading && <div className="pmc-muted" data-testid="public-auctions-loading">Loading auctions…</div>}

      {!loading && (
        <>
          {liveItems.length > 0 && (
            <div data-testid="public-auctions-live-group">
              <Grid items={liveItems} />
            </div>
          )}

          {liveItems.length === 0 && (
            <div className="pmc-card" style={{ padding: "28px", textAlign: "center" }}
                 data-testid="public-auctions-empty-live">
              <div style={{ fontSize: "17px", fontWeight: 600 }}>No live auctions right now</div>
              <p className="pmc-muted" style={{ margin: "8px 0 0", fontSize: "14px" }}>
                {upcomingItems.length > 0
                  ? "Upcoming auctions are listed below — check back when they go live."
                  : "New reverse auctions are published here. Check back soon."}
              </p>
            </div>
          )}

          {(variant === "page" || liveItems.length === 0) && upcomingItems.length > 0 && (
            <div style={{ marginTop: "32px" }} data-testid="public-auctions-upcoming-group">
              <div className="pmc-eyebrow" style={{ marginBottom: "12px" }}>Upcoming</div>
              <Grid items={upcomingItems} />
            </div>
          )}

          {variant === "page" && closedItems.length > 0 && (
            <div style={{ marginTop: "32px" }} data-testid="public-auctions-closed-group">
              <div className="pmc-eyebrow" style={{ marginBottom: "12px" }}>Closed &amp; awarded</div>
              <Grid items={closedItems} />
            </div>
          )}
        </>
      )}
    </section>
  );

  if (variant === "page") {
    return (
      <div className="min-h-screen bg-brand-pale" data-testid="public-auctions-page">
        <TopBar />
        {body}
      </div>
    );
  }
  return body;
}

export function PublicAuctionsPage() {
  return <LiveAuctionsBand variant="page" />;
}
