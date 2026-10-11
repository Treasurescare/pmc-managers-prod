import { useEffect, useState, useCallback } from "react";
import { Link } from "react-router-dom";
import { useUiTheme } from "@/context/UiThemeContext";
import { vendorApi, bidApi, publicApi, docusignApi, engagementsApi } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";
import VendorBlacklistAppeal from "./VendorBlacklistAppeal";

/**
 * v50o — Vendor home rewritten on the shared VendorPortalChrome.
 *
 * The previous version was a static Option-E mockup whose sidebar Home link
 * (and every other link) was href="#" — clicks were rescued by the global
 * link patcher by *text*, which sometimes routed "Home" to the PUBLIC
 * landing page instead of the vendor portal. Every link on this page is now
 * a real React Router <Link>, so Home always stays inside /vendor.
 *
 * Content is live: greeting uses the real company name + today's date,
 * KPI tiles come from bidApi.mine / docusignApi.listMine /
 * publicApi.listNotices, and the "Do this next" strip picks the most
 * urgent pending action from the vendor's own bids.
 */

const greeting = () => {
  const h = new Date().getHours();
  if (h < 12) return "Good morning";
  if (h < 17) return "Good afternoon";
  return "Good evening";
};

const todayLabel = () =>
  new Date().toLocaleDateString("en-GB",
    { weekday: "long", day: "numeric", month: "long", year: "numeric" });

export default function VendorHomeE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  const [me, setMe] = useState(null);
  const [bids, setBids] = useState([]);
  const [envelopes, setEnvelopes] = useState([]);
  const [tendersTotal, setTendersTotal] = useState(0);
  const [quoteRequests, setQuoteRequests] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      const [meRes, bidsRes, envRes, noticeRes, engRes] = await Promise.all([
        vendorApi.me(),
        bidApi.mine().catch(() => []),
        docusignApi.listMine().catch(() => ({ items: [] })),
        publicApi.listNotices({ limit: 1 }).catch(() => ({ total: 0 })),
        // v52bv — vendor's own service quote requests feed a dedicated KPI.
        engagementsApi.mine().catch(() => ({ items: [] })),
      ]);
      setMe(meRes);
      setBids(Array.isArray(bidsRes) ? bidsRes : (bidsRes?.items || []));
      setEnvelopes(envRes?.items || []);
      setTendersTotal(noticeRes?.total || 0);
      const engItems = Array.isArray(engRes?.items) ? engRes.items : [];
      setQuoteRequests(engItems.filter((e) =>
        ["quote_requested", "quoted", "invoiced"].includes(e.status)).length);
    } catch { /* non-fatal — page still renders with empty states */ }
    finally { setLoading(false); }
  }, []);
  useEffect(() => { if (isE) load(); }, [isE, load]);

  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;

  const activeBids = bids.filter((b) => !["withdrawn", "rejected", "awarded"].includes(b.status));
  const draftBids = bids.filter((b) => b.status === "draft");
  const emdPending = bids.filter((b) => b.status === "submitted" && !b.emd_paid);
  const toSign = envelopes.filter((e) => ["sent", "delivered", "created"].includes(e.status));

  // Most urgent next action, in priority order.
  const next = (() => {
    if (emdPending.length) {
      const b = emdPending[0];
      return { icon: "i-coin", eyebrow: "Do this next",
        title: `Pay EMD for ${b.notice_title || b.bid_ref}`,
        sub: "Your bid can't move to sign & seal until the EMD is received.",
        to: "/vendor/emd", cta: "Pay EMD" };
    }
    if (toSign.length) {
      return { icon: "i-sign", eyebrow: "Do this next",
        title: `${toSign[0].subject || "Document"} is waiting for your signature`,
        sub: "Sign with DocuSign inside the portal — takes about 2 minutes.",
        to: "/vendor/signatures", cta: "Review & sign" };
    }
    if (draftBids.length) {
      const b = draftBids[0];
      return { icon: "i-file", eyebrow: "Pick up where you left off",
        title: `Draft bid on ${b.notice_title || b.bid_ref}`,
        sub: "Finish and submit before the tender deadline.",
        to: `/vendor/workspace/${b.id}`, cta: "Continue draft" };
    }
    return null;
  })();

  return (
    <div data-testid="vendor-home-e" data-pmc-e-page="vendor-home-e">
      <VendorPortalChrome active="/vendor" counts={{
        "/vendor": undefined,
        "/vendor/mybids": activeBids.length || undefined,
        "/vendor/signatures": toSign.length || undefined,
      }}>
        <VendorBlacklistAppeal />
        <div className="pmc-hi">
          <div>
            <div className="pmc-eyebrow" data-testid="vhome-date">{todayLabel()}</div>
            <h1 data-testid="vhome-greeting">
              {greeting()}, {me?.company_name || "Supplier"}
            </h1>
          </div>
          <div style={{ display: "flex", gap: 8 }}>
            {draftBids.length > 0 && (
              <Link to={`/vendor/workspace/${draftBids[0].id}`}
                    className="pmc-btn pmc-btn--secondary"
                    data-testid="vhome-continue-draft">
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-file" /></svg> Continue draft
              </Link>
            )}
            <Link to="/vendor/tenders" className="pmc-btn pmc-btn--primary"
                  data-testid="vhome-find-tenders">
              <svg className="pmc-ico" aria-hidden="true"><use href="#i-search" /></svg> Find tenders
            </Link>
          </div>
        </div>

        {next && (
          <section className="pmc-next" aria-label="Do this next"
                   data-testid="vhome-next">
            <div className="pmc-next__i">
              <svg className="pmc-ico" aria-hidden="true"><use href={`#${next.icon}`} /></svg>
            </div>
            <div>
              <div className="pmc-eyebrow">{next.eyebrow}</div>
              <h2>{next.title}</h2>
              <div className="pmc-muted" style={{ fontSize: 14 }}>{next.sub}</div>
            </div>
            <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
              <Link to={next.to} className="pmc-btn pmc-btn--primary"
                    data-testid="vhome-next-cta">{next.cta}</Link>
            </div>
          </section>
        )}

        <div className="pmc-kpis" data-testid="vhome-kpis">
          <Link to="/vendor/mybids" className="pmc-kpi" data-testid="vhome-kpi-bids"
                style={{ textDecoration: "none", color: "inherit" }}>
            <div className="l">Active bids</div>
            <div className="pmc-figure">{loading ? "…" : activeBids.length}</div>
            <div className="s">{emdPending.length ? `${emdPending.length} need EMD` : "all on track"}</div>
          </Link>
          <Link to="/vendor/signatures" className="pmc-kpi" data-testid="vhome-kpi-sign"
                style={{ textDecoration: "none", color: "inherit" }}>
            <div className="l">Awaiting signature</div>
            <div className="pmc-figure">{loading ? "…" : toSign.length}</div>
            <div className="s">{toSign.length ? "action needed" : "nothing pending"}</div>
          </Link>
          <Link to="/vendor/tenders" className="pmc-kpi" data-testid="vhome-kpi-tenders"
                style={{ textDecoration: "none", color: "inherit" }}>
            <div className="l">Open tenders</div>
            <div className="pmc-figure">{loading ? "…" : tendersTotal}</div>
            <div className="s">on the public board</div>
          </Link>
          <Link to="/vendor/services" className="pmc-kpi" data-testid="vhome-kpi-services"
                style={{ textDecoration: "none", color: "inherit" }}>
            <div className="l" style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <svg className="pmc-ico" aria-hidden="true"><use href="#i-briefcase" /></svg>
              Service quotes
            </div>
            <div className="pmc-figure">{loading ? "…" : quoteRequests}</div>
            <div className="s">{quoteRequests ? "requested · awaiting PMC pricing" : "no requests yet"}</div>
          </Link>
          <Link to="/vendor/company" className="pmc-kpi" data-testid="vhome-kpi-kyc"
                style={{ textDecoration: "none", color: "inherit" }}>
            <div className="l">KYC status</div>
            <div className="pmc-figure" style={{ fontSize: 20 }}>{me?.kyc_status || "Verified"}</div>
            <div className="s">{me?.vendor_ref || ""}</div>
          </Link>
        </div>

        <section className="pmc-panel" style={{ marginTop: 16 }}
                 data-testid="vhome-quicklinks">
          <div className="pmc-panel__head">
            <h2 className="pmc-panel__title">Quick links</h2>
          </div>
          <div className="pmc-panel__body" style={{ display: "grid",
               gridTemplateColumns: "repeat(auto-fit, minmax(220px, 1fr))", gap: 10 }}>
            {[
              ["/vendor/tenders", "Find tenders", "Browse every open tender on the board"],
              ["/vendor/categories", "Categories", "Request new categories of interest"],
              ["/vendor/company", "Licences & KYC", "Keep licences current to avoid KYC gaps"],
              ["/vendor/account", "Account & security", "Update company details (admin-approved)"],
            ].map(([to, label, sub]) => (
              <Link key={to} to={to} className="pmc-tip"
                    data-testid={`vhome-quick-${label.toLowerCase().replace(/[^a-z]+/g, "-")}`}
                    style={{ textDecoration: "none", color: "inherit" }}>
                <svg className="pmc-ico" aria-hidden="true"><use href="#i-spark" /></svg>
                <div><b>{label}</b><div className="pmc-muted" style={{ fontSize: 12 }}>{sub}</div></div>
              </Link>
            ))}
          </div>
        </section>
      </VendorPortalChrome>
    </div>
  );
}
