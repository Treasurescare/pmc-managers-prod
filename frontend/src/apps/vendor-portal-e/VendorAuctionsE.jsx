/**
 * VendorAuctionsE — v52bx. Lists reverse auctions the vendor can join:
 * (a) every auction tied to a notice they already bid on, (b) explicit
 * admin invitations. Mounted at /vendor/auctions.
 */
import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { reverseAuctionApi, showApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";

export default function VendorAuctionsE() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    reverseAuctionApi.mine()
      .then((d) => setItems(d.items || []))
      .catch(showApiError)
      .finally(() => setLoading(false));
  }, []);

  return (
    <div className="pmc-vp" data-pmc-e-page="vendor-auctions-e">
      <VendorPortalChrome active="Reverse auctions">
        <div className="pmc-page">
          <div className="pmc-page__head">
            <h1 className="pmc-page__title">Reverse auctions</h1>
            <p className="pmc-page__lead">Live and upcoming auctions you can join. Click Enter to go to the auction room — your identity stays masked to competitors.</p>
          </div>
          <div className="pmc-panel" data-testid="va-list">
            <div className="pmc-panel__head"><h2>Open to you</h2></div>
            <div className="pmc-panel__body">
              {loading && <div style={{ padding: 16 }}>Loading…</div>}
              {!loading && items.length === 0 && (
                <div style={{ padding: 24, color: "var(--on-chrome-muted)" }}>
                  No reverse auctions right now. If PMC invites you, it will appear here.
                </div>
              )}
              {items.map((a) => (
                <div key={a.id} className="pmc-txn" data-testid={`va-row-${a.id}`}
                     style={{ display: "grid", gridTemplateColumns: "1fr auto", gap: 12, padding: 12, borderBottom: "1px solid rgba(15,59,46,.08)" }}>
                  <div>
                    <div style={{ fontWeight: 600 }}>{a.title}</div>
                    <div style={{ fontSize: 12, color: "var(--on-chrome-muted)" }}>
                      {a.notice_ref} · {a.currency} · start {Number(a.starting_price || 0).toLocaleString()} → floor {Number(a.floor_price || 0).toLocaleString()}
                    </div>
                    <div style={{ fontSize: 11, marginTop: 4 }}>
                      <span className={`pmc-pill ${a.status === "live" ? "pmc-pill--success" : a.status === "draft" ? "pmc-pill--info" : "pmc-pill--warning"}`}>{a.status}</span>
                      {a.why && <span style={{ marginLeft: 8, color: "var(--on-chrome-muted)" }}>· {a.why}</span>}
                    </div>
                  </div>
                  <div style={{ alignSelf: "center" }}>
                    <Link to={`/vendor/auction/${a.id}`} className="pmc-btn pmc-btn--primary pmc-btn--sm" data-testid={`va-enter-${a.id}`}>
                      {a.status === "live" ? "Enter" : "View details"}
                    </Link>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </VendorPortalChrome>
    </div>
  );
}
