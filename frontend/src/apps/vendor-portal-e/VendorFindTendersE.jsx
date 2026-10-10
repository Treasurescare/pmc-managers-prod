import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useUiTheme } from "@/context/UiThemeContext";
import { publicApi, showApiError } from "@/lib/api";
import { useListPager } from "@/components/ListPager";
import VendorPortalChrome from "./VendorPortalChrome";

function fmtMoney(amount, currency) {
  if (amount == null) return "—";
  try {
    return new Intl.NumberFormat("en-US", {
      style: "currency", currency: currency || "USD", maximumFractionDigits: 0,
    }).format(amount);
  } catch {
    return `${currency || ""} ${Number(amount).toLocaleString()}`;
  }
}

function fmtCountdown(iso) {
  if (!iso) return "—";
  const secs = Math.max(0, Math.floor((new Date(iso) - new Date()) / 1000));
  const d = Math.floor(secs / 86400);
  const h = Math.floor((secs % 86400) / 3600);
  const m = Math.floor((secs % 3600) / 60);
  if (secs === 0) return "Closed";
  if (d > 0) return `${d}d ${h}h`;
  if (h > 0) return `${h}h ${m}m`;
  return `${m}m`;
}

export default function VendorFindTendersE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [items, setItems] = useState([]);
  const [total, setTotal] = useState(0);
  const [search, setSearch] = useState("");
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isE) return;
    setLoading(true);
    publicApi.listNotices({ limit: 100, offset: 0 })
      .then((res) => {
        setItems(res.items || []);
        setTotal(res.total || 0);
      })
      .catch(showApiError)
      .finally(() => setLoading(false));
  }, [isE]);

  const filtered = useMemo(() => {
    const q = search.trim().toLowerCase();
    if (!q) return items;
    return items.filter((n) => (
      (n.title || "").toLowerCase().includes(q) ||
      (n.notice_ref || "").toLowerCase().includes(q) ||
      (n.business_category || n.category || "").toLowerCase().includes(q)
    ));
  }, [items, search]);

  // v50o — same pagination widget as the admin console (Show 10/20/30/All,
  // "1–10 of N", Prev/Next) instead of a one-off pager.
  const { paged, controls } = useListPager(filtered, { defaultSize: 10, testid: "vft-pager" });

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  return (
    <div data-testid="vendor-find-tenders-e" data-pmc-e-page="vendor-find-tenders-e">
      <VendorPortalChrome active="/vendor/tenders">
        <div className="sp-head">
          <div>
            <div className="pmc-eyebrow">Find tenders</div>
            <h1 data-testid="vft-count-heading">
              {loading ? "Loading tenders…" : `${filtered.length} tender${filtered.length === 1 ? "" : "s"} available`}
            </h1>
          </div>
        </div>

        <div className="pmc-filter" style={{ margin: "0 0 12px" }}>
          <label className="pmc-search" style={{ flex: "1" }}>
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg>
            <input placeholder="Keyword, reference or category"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
              data-testid="vft-search" />
          </label>
        </div>

        {loading && (
          <div className="pmc-callout" style={{ marginBottom: "16px" }}
               data-testid="vft-loading">
            Loading live tenders from the public board…
          </div>
        )}

        {!loading && filtered.length === 0 && (
          <div className="pmc-callout" style={{ marginBottom: "16px" }}
               data-testid="vft-empty">
            <svg className="pmc-ico" aria-hidden="true"><use href="#i-flag" /></svg>
            <div>
              <b>No tenders match your search.</b>{" "}
              Try clearing filters or <Link to="/vendor/categories">add more categories</Link> to broaden your match.
            </div>
          </div>
        )}

        <div className="pmc-grid3" data-testid="vft-grid">
          {paged.map((n) => (
            <article className="pmc-tender" key={n.notice_ref || n.id}
                     data-testid={`vft-card-${n.notice_ref || n.id}`}>
              <div className="pmc-tender__top">
                <span className="pmc-tag">{(n.notice_type || "TENDER").toUpperCase()}</span>
                <span className="pmc-ref">{n.notice_ref}</span>
                <span style={{ marginLeft: "auto" }} className="pmc-countdown">
                  {fmtCountdown(n.submission_deadline)}
                </span>
              </div>
              <h3 className="pmc-tender__title">{n.title}</h3>
              <dl className="pmc-tender__meta" style={{ margin: 0 }}>
                <div className="is-budget">
                  <dt>Indicative budget</dt>
                  <dd>{fmtMoney(n.budget_amount, n.budget_currency)}</dd>
                </div>
                <div>
                  <dt>EMD</dt>
                  <dd style={{ fontWeight: 500 }}>{n.emd_rule_label || n.emd_rule || "See notice"}</dd>
                </div>
                <div>
                  <dt>Delivery</dt>
                  <dd style={{ fontWeight: 500 }}>
                    {n.country || "—"}{n.business_category ? ` · ${n.business_category}` : ""}
                  </dd>
                </div>
              </dl>
              <div className="pmc-tender__foot">
                <Link to={`/notices/${n.notice_ref}`}
                      className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                      data-testid={`vft-view-${n.notice_ref}`}>View</Link>
                {(() => {
                  const closed = n.submission_deadline && new Date(n.submission_deadline) < new Date();
                  return closed ? (
                    <span className="pmc-pill pmc-pill--warning"
                          data-testid={`vft-closed-${n.notice_ref}`}>Closed</span>
                  ) : (
                    <Link to={`/vendor/bid/new/${n.notice_ref}`}
                          className="pmc-btn pmc-btn--primary pmc-btn--sm"
                          data-testid={`vft-bid-${n.notice_ref}`}>Start bid</Link>
                  );
                })()}
              </div>
            </article>
          ))}
        </div>

        {filtered.length > 0 && (
          <div style={{ marginTop: 20, border: "1px solid var(--line, #0001)",
                        borderRadius: "var(--radius-sm, 4px)", overflow: "hidden" }}
               data-testid="vft-pager-wrap">
            {controls}
          </div>
        )}
      </VendorPortalChrome>
    </div>
  );
}
