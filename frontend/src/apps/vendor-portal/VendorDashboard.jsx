import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { vendorApi, publicApi, bidApi, formatApiError, showApiError} from "@/lib/api";
import { useUiTheme } from "@/context/UiThemeContext";
import VendorGdprButton from "./VendorGdprButton";
import VendorSignatures from "./VendorSignatures";
import RateAVendor from "./RateAVendor";
import VendorNotificationBell from "./VendorNotificationBell";
import BidDetailModal from "./BidDetailModal";
import ProfileModal from "@/apps/shared/ProfileModal";
import useTenantSkin from "@/apps/shared/useTenantSkin";
import { useListPager } from "@/components/ListPager";

const STATUS_LABELS = {
  draft: "Draft", submitted: "Submitted", emd_pending: "EMD Pending", emd_paid: "EMD Paid",
  escrow_accepted: "Escrow Accepted", admin_flagged: "Admin Flagged",
  certifier_review: "Certifier Reviewing", certifier_cleared: "Certifier Cleared",
  legal_review: "Legal Reviewing", legal_cleared: "Legal Cleared",
  accounting_review: "Accounting Reviewing", accounting_cleared: "Accounting Cleared",
  committee_review: "Committee Reviewing", on_hold: "On Hold", awarded: "Awarded", rejected: "Rejected",
  withdrawn: "Withdrawn", closed: "Closed",
};

export default function VendorDashboard() {
  const nav = useNavigate();
  const { isE } = useUiTheme();
  const [vendor, setVendor] = useState(null);
  const [notices, setNotices] = useState([]);
  const [bids, setBids] = useState([]);
  const [tab, setTab] = useState("tenders");
  const [bidFilter, setBidFilter] = useState(null);
  const [profileOpen, setProfileOpen] = useState(false);
  const [viewBidId, setViewBidId] = useState(null);
  const tenant = useTenantSkin();
  const tenderPager = useListPager(notices, { testid: "vendor-tender-pager" });
  const bidPager = useListPager(bids, { testid: "vendor-bid-pager" });

  useEffect(() => {
    (async () => {
      try {
        const v = await vendorApi.me();
        if (v.must_change_password) return nav("/vendor/change-password");
        setVendor(v);
        const [n, b] = await Promise.all([publicApi.listNotices({ limit: 50 }), bidApi.mine()]);
        setNotices(n.items || []);
        setBids(b || []);
      } catch {
        nav("/vendor/login");
      }
    })();
  }, []);

  const logout = async () => {
    try { await vendorApi.logout(); }
    catch (err) {
      if (process.env.NODE_ENV !== "production") console.debug("vendor logout skipped:", err?.response?.status);
    }
    nav("/vendor/login");
  };

  if (!vendor) return <div className="p-10 text-slate-500">Loading…</div>;

  const now = new Date();
  const greeting = now.getHours() < 12 ? "Good morning" : now.getHours() < 18 ? "Good afternoon" : "Good evening";
  const activeBids = bids.filter((b) => !["awarded","rejected","withdrawn","closed"].includes(b.status));
  const drafts = bids.filter((b) => b.status === "draft").length;
  const awarded = bids.filter((b) => b.status === "awarded").length;
  const emdDue = bids.filter((b) => b.status === "emd_pending" && (b.emd_due_amount || 0) > 0).length;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="vendor-dashboard" data-ui={isE ? "e" : undefined}>
      <header className="text-white" style={{ backgroundColor: isE ? "#0F3B2E" : (tenant?.branding_color || "#0b1e3f") }}>
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <div className="text-xs tracking-widest uppercase text-amber-300">
              {tenant ? `${tenant.name} · Vendor Portal` : "Vendor Portal"}
            </div>
            <h1 className="text-lg font-serif">{vendor.company_name || vendor.email}</h1>
          </div>
          <div className="text-sm flex items-center gap-4">
            <span className="text-white/70">{vendor.vendor_ref}</span>
            <VendorNotificationBell />
            <button onClick={() => setProfileOpen(true)}
                    data-testid="vendor-profile-open"
                    className="w-9 h-9 rounded-full overflow-hidden border border-white/30 flex items-center justify-center bg-white/10 hover:ring-2 hover:ring-white/40">
              {vendor.avatar_data_url
                ? <img src={vendor.avatar_data_url} alt="avatar" className="w-full h-full object-cover" />
                : <span className="text-white text-sm font-serif">{(vendor.email || "?").slice(0, 1).toUpperCase()}</span>}
            </button>
            <VendorGdprButton onSuccess={() => nav("/vendor/login")} />
            <button onClick={logout} className="text-white/80 hover:text-white underline"
              data-testid="vendor-logout">Sign out</button>
          </div>
        </div>
      </header>
      <ProfileModal open={profileOpen} onClose={() => setProfileOpen(false)}
                    role="vendor" me={vendor} onChange={setVendor} />

      {/* Option E — greeting band + KPI cards (opt-in) matching E-Vendor-Portal.html */}
      {isE && (
        <>
          <section className="e-portal-greeting" data-testid="vendor-greeting-e">
            <div>
              <span className="e-portal-datechip">
                {now.toLocaleDateString("en-US", { weekday: "long", day: "2-digit", month: "long", year: "numeric" })}
              </span>
              <h1>
                {greeting}, <em>{(vendor.contact_name || vendor.company_name || vendor.email || "Vendor").split(" ")[0]}</em>
              </h1>
            </div>
            <Link
              to="#"
              onClick={(e) => { e.preventDefault(); setTab("tenders"); }}
              data-testid="vendor-find-tenders-e"
              className="e-cta-gold"
            >
              <svg aria-hidden="true" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="2" viewBox="0 0 24 24">
                <circle cx="11" cy="11" r="7" strokeLinecap="round" />
                <path d="M20 20l-3.5-3.5" strokeLinecap="round" />
              </svg>
              Find tenders
            </Link>
          </section>
          <section className="e-portal-kpis" data-testid="vendor-kpis-e">
            <button type="button" className="e-portal-kpi text-left cursor-pointer transition-colors hover:brightness-110" data-testid="vendor-kpi-active"
                    onClick={() => { setTab("bids"); setBidFilter("active"); }}>
              <span className="e-portal-kpi-label">Bids in progress</span>
              <span className="e-portal-kpi-value">{String(activeBids.length).padStart(2, "0")}</span>
              <span className="e-portal-kpi-foot">{activeBids.length - drafts} active · {drafts} draft{drafts === 1 ? "" : "s"}</span>
            </button>
            <button type="button" className={"text-left cursor-pointer transition-colors hover:brightness-110 e-portal-kpi" + (emdDue > 0 ? " e-attn" : "")} data-testid="vendor-kpi-emd"
                    onClick={() => { setTab("bids"); setBidFilter("emd"); }}>
              <span className="e-portal-kpi-label">
                {emdDue > 0 && <span className="e-live-dot inline-block mr-2" style={{background:"#E3B55C",boxShadow:"0 0 0 3px rgba(227,181,92,0.25)"}} />}
                EMD due
              </span>
              <span className="e-portal-kpi-value">{String(emdDue).padStart(2, "0")}</span>
              <span className="e-portal-kpi-foot">{emdDue === 0 ? "All clear" : "Pay before deadline"}</span>
            </button>
            <button type="button" className="e-portal-kpi text-left cursor-pointer transition-colors hover:brightness-110" data-testid="vendor-kpi-awarded"
                    onClick={() => { setTab("bids"); setBidFilter("awarded"); }}>
              <span className="e-portal-kpi-label">Awarded</span>
              <span className="e-portal-kpi-value">{String(awarded).padStart(2, "0")}</span>
              <span className="e-portal-kpi-foot">{awarded === 0 ? "Awaiting" : "Contracts ready"}</span>
            </button>
            <button type="button" className="e-portal-kpi text-left cursor-pointer transition-colors hover:brightness-110" data-testid="vendor-kpi-open"
                    onClick={() => { setTab("tenders"); setBidFilter(null); }}>
              <span className="e-portal-kpi-label">Open opportunities</span>
              <span className="e-portal-kpi-value">{String(notices.length).padStart(2, "0")}</span>
              <span className="e-portal-kpi-foot">Matched to your KYC</span>
            </button>
          </section>
        </>
      )}

      {/* Option E — Sealed bid in progress card (matches E-Vendor-Portal.html) */}
      {isE && activeBids.length > 0 && (() => {
        const bip = activeBids[0];
        const notice = notices.find((n) => n.notice_ref === bip.notice_ref);
        const rem = notice?.submission_deadline ? new Date(notice.submission_deadline) - new Date() : 0;
        const days = Math.max(0, Math.floor(rem / (1000*60*60*24)));
        const hours = Math.max(0, Math.floor((rem / (1000*60*60)) % 24));
        const mins = Math.max(0, Math.floor((rem / (1000*60)) % 60));
        const statusRank = { draft: 0, submitted: 1, emd_pending: 2, emd_paid: 3, escrow_accepted: 3, certifier_review: 4, awarded: 4 };
        const currentStep = Math.min(4, statusRank[bip.status] ?? 2);
        const stepNames = ["Eligibility", "Technical envelope", "Commercial envelope", "EMD / bank guarantee", "Review, sign & seal"];
        return (
          <section className="e-bid-progress" data-testid="vendor-bid-progress-e">
            <div className="e-bid-progress-inner">
              <div className="e-bid-progress-head">
                <span className="e-tag">
                  <svg aria-hidden="true" width="16" height="16" fill="none" stroke="currentColor" strokeWidth="1.8" viewBox="0 0 24 24"><rect x="4" y="10" width="16" height="11" rx="1.5" /><path d="M8 10V7a4 4 0 0 1 8 0v3" strokeLinejoin="round" /></svg>
                  Sealed bid in progress · {bip.bid_ref}
                </span>
                {rem > 0 && (
                  <span className="e-timer" role="timer">
                    <span className="e-live-dot" style={{background:"#E3B55C",boxShadow:"0 0 0 3px rgba(227,181,92,0.25)"}} />
                    CLOSES IN <span className="e-num">{String(days).padStart(2,"0")}d {String(hours).padStart(2,"0")}:{String(mins).padStart(2,"0")}</span>
                  </span>
                )}
              </div>
              <div className="e-bid-progress-body">
                <Link to={`/notices/${bip.notice_ref}`} className="e-bid-progress-title">
                  {notice?.title || bip.notice_ref}
                </Link>
                <ol className="e-bid-steps">
                  {stepNames.map((name, i) => {
                    const isDone = i < currentStep;
                    const isActive = i === currentStep;
                    const roman = ["I","II","III","IV","V"][i];
                    return (
                      <li key={i} className="e-bid-step">
                        <span className="e-bid-step-marker">
                          <span className={"e-bid-step-dot" + (isDone ? " done" : isActive ? " active" : "")}>
                            {isDone ? (
                              <svg width="14" height="14" fill="none" stroke="#8FD9C4" strokeWidth="2.4" viewBox="0 0 24 24"><path d="M5 12l5 5L19 7" strokeLinejoin="round" strokeLinecap="round"/></svg>
                            ) : roman}
                          </span>
                          {i < 4 && <span className={"e-bid-step-line" + (isDone ? " done" : " dashed")} />}
                        </span>
                        <span className="e-bid-step-label">
                          <span className={"e-bid-step-tag" + (isDone ? " done" : isActive ? " active" : "")}>
                            {roman} · {isDone ? "DONE" : isActive ? "IN PROGRESS" : "TO DO"}
                          </span>
                          <span className="e-bid-step-name">{name}</span>
                        </span>
                      </li>
                    );
                  })}
                </ol>
              </div>
            </div>
          </section>
        );
      })()}

      <div className="max-w-6xl mx-auto px-6 py-6">
        <div className="flex gap-4 border-b mb-6 overflow-x-auto">
          <button onClick={() => setTab("tenders")}
            className={`pb-2 text-sm whitespace-nowrap ${tab === "tenders" ? "border-b-2 border-slate-900 font-semibold" : "text-slate-500"}`}
            data-testid="vendor-tab-tenders">Open tenders ({notices.length})</button>
          <button onClick={() => setTab("bids")}
            className={`pb-2 text-sm whitespace-nowrap ${tab === "bids" ? "border-b-2 border-slate-900 font-semibold" : "text-slate-500"}`}
            data-testid="vendor-tab-bids">My bids ({bids.length})</button>
          <button onClick={() => setTab("signatures")}
            className={`pb-2 text-sm whitespace-nowrap ${tab === "signatures" ? "border-b-2 border-slate-900 font-semibold" : "text-slate-500"}`}
            data-testid="vendor-tab-signatures">
            Signatures ({bids.filter((b) => b.status === "awarded").length})
          </button>
          <button onClick={() => setTab("rate")}
            className={`pb-2 text-sm whitespace-nowrap ${tab === "rate" ? "border-b-2 border-slate-900 font-semibold" : "text-slate-500"}`}
            data-testid="vendor-tab-rate">Rate a vendor</button>
        </div>

        {tab === "signatures" && <VendorSignatures />}
        {tab === "rate" && <RateAVendor me={vendor} />}

        {tab === "tenders" && (
          <>
          <div className="grid md:grid-cols-2 gap-4" data-testid="vendor-tender-list">
            {tenderPager.paged.map((n) => (
              <Link key={n.id} to={`/vendor/bid/new/${n.notice_ref}`}
                className="bg-white border rounded-lg p-5 hover:shadow-md transition"
                data-testid={`tender-card-${n.notice_ref}`}>
                <div className="text-xs text-slate-500">{n.notice_ref} · {n.document_type.toUpperCase()}</div>
                <div className="font-serif text-lg mt-1">{n.title}</div>
                <div className="text-sm text-slate-600 mt-2 line-clamp-2">{n.description}</div>
                <div className="mt-3 flex items-center justify-between text-xs text-slate-500">
                  <span>{n.category}</span>
                  <span>Deadline: {(n.submission_deadline || "").slice(0, 10)}</span>
                </div>
                <div className="mt-2 text-sm">
                  Budget: <strong>{n.budget_currency} {(n.budget_amount || 0).toLocaleString()}</strong>
                </div>
                <div className="mt-3 text-xs font-semibold text-blue-700">Submit bid →</div>
              </Link>
            ))}
            {notices.length === 0 && (
              <div className="text-slate-500 col-span-2 text-sm">No open tenders right now.</div>
            )}
          </div>
          {tenderPager.controls}
          </>
        )}

        {tab === "bids" && (
          <>
          {bidFilter && (
            <div className="mb-3 flex items-center gap-2 text-sm" data-testid="vendor-bid-filter-banner">
              <span className="text-slate-600">Filter:</span>
              <span className="px-3 py-1 rounded-full bg-slate-100 border font-medium">
                {bidFilter === "active" ? "In progress" : bidFilter === "emd" ? "EMD due" : bidFilter === "awarded" ? "Awarded" : bidFilter}
              </span>
              <button onClick={() => setBidFilter(null)} className="text-xs underline text-slate-500 hover:text-slate-800"
                      data-testid="vendor-bid-filter-clear">Clear</button>
            </div>
          )}
          <div className="space-y-3" data-testid="vendor-bid-list">
            {bidPager.paged
              .filter((b) => {
                if (!bidFilter) return true;
                if (bidFilter === "active") return !["awarded","rejected","withdrawn","closed"].includes(b.status);
                if (bidFilter === "emd") return b.status === "emd_pending" && (b.emd_due_amount || 0) > 0;
                if (bidFilter === "awarded") return b.status === "awarded";
                return true;
              })
              .map((b) => (
              <div key={b.id} className="bg-white border rounded-lg p-4 flex items-center justify-between"
                data-testid={`bid-row-${b.bid_ref}`}>
                <div>
                  <div className="text-xs text-slate-500">{b.bid_ref} · {b.notice_ref}</div>
                  <div className="text-sm mt-0.5">
                    Price: <strong>{b.price_currency} {(b.price_amount || 0).toLocaleString()}</strong>
                    &nbsp;·&nbsp; EMD due: {b.emd_currency} {(b.emd_due_amount || 0).toLocaleString()}
                  </div>
                </div>
                <div className="flex items-center gap-3">
                  <span className="text-xs px-2 py-1 rounded bg-slate-100">
                    {STATUS_LABELS[b.status] || b.status}
                  </span>
                  {b.status === "submitted" && (b.emd_due_amount || 0) === 0 && (
                    <span className="text-[10px] uppercase tracking-widest text-emerald-700"
                          data-testid={`no-emd-${b.bid_ref}`}>No EMD required</span>
                  )}
                  <button
                    onClick={() => setViewBidId(b.id)}
                    data-testid={`view-bid-${b.bid_ref}`}
                    className="text-xs border px-3 py-1.5 hover:bg-slate-50">
                    View
                  </button>
                  {(b.status === "emd_pending" || b.status === "submitted") && b.emd_due_amount > 0 && (
                    <button
                      onClick={async () => {
                        try {
                          const r = await bidApi.get(b.id); void r;
                          const chk = await (await import("@/lib/api")).paymentApi
                            .checkout(b.id, window.location.origin);
                          // Open Stripe checkout in a new tab — Stripe's CSP blocks
                          // iframe embedding, so navigating the current window
                          // hangs when the app is viewed inside a preview iframe.
                          const w = window.open(chk.checkout_url, "_blank", "noopener,noreferrer");
                          if (!w) {
                            // Popup blocker: fall back to top-window navigation
                            try { window.top.location.href = chk.checkout_url; }
                            catch { window.location.href = chk.checkout_url; }
                          }
                          toast.info("Stripe checkout opened in a new tab");
                        } catch (err) { showApiError(err); }
                      }}
                      className="text-xs bg-amber-500 text-white px-3 py-1.5 rounded hover:bg-amber-600"
                      data-testid={`pay-emd-${b.bid_ref}`}>Pay EMD</button>
                  )}
                </div>
              </div>
            ))}
            {bids.length === 0 && <div className="text-slate-500 text-sm">You haven't placed any bids yet.</div>}
          </div>
          {bidPager.controls}
          </>
        )}
        <BidDetailModal bidId={viewBidId} onClose={() => setViewBidId(null)} />
      </div>
    </div>
  );
}
