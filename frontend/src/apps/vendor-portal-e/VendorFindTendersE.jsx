import { useEffect, useState, useMemo } from "react";
import { Link } from "react-router-dom";
import { useUiTheme } from "@/context/UiThemeContext";
import { publicApi, showApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";

const PAGE_SIZE = 9;

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
  const [page, setPage] = useState(0);
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

  const paged = filtered.slice(page * PAGE_SIZE, (page + 1) * PAGE_SIZE);
  const totalPages = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));

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
              onChange={(e) => { setSearch(e.target.value); setPage(0); }}
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
                <Link to={`/notices/${n.notice_ref}`}
                      className="pmc-btn pmc-btn--primary pmc-btn--sm"
                      data-testid={`vft-bid-${n.notice_ref}`}>Start bid</Link>
              </div>
            </article>
          ))}
        </div>

        {totalPages > 1 && (
          <div style={{ marginTop: 20, display: "flex", gap: 8, alignItems: "center",
                        justifyContent: "space-between" }} data-testid="vft-pager">
            <button className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                    onClick={() => setPage((p) => Math.max(0, p - 1))}
                    disabled={page === 0}
                    data-testid="vft-page-prev">
              ← Previous
            </button>
            <div className="pmc-muted" style={{ fontSize: 13 }}>
              Page {page + 1} of {totalPages} · {total} total on board
            </div>
            <button className="pmc-btn pmc-btn--secondary pmc-btn--sm"
                    onClick={() => setPage((p) => Math.min(totalPages - 1, p + 1))}
                    disabled={page >= totalPages - 1}
                    data-testid="vft-page-next">
              Next →
            </button>
          </div>
        )}
      </VendorPortalChrome>
    </div>
  );
}
