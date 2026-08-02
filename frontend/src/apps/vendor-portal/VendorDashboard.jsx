import { useEffect, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { vendorApi, publicApi, bidApi, formatApiError } from "@/lib/api";

const STATUS_LABELS = {
  draft: "Draft", submitted: "Submitted", emd_pending: "EMD Pending", emd_paid: "EMD Paid",
  escrow_accepted: "Escrow Accepted", admin_flagged: "Admin Flagged",
  certifier_review: "Certifier Reviewing", certifier_cleared: "Certifier Cleared",
  legal_review: "Legal Reviewing", legal_cleared: "Legal Cleared",
  accounting_review: "Accounting Reviewing", accounting_cleared: "Accounting Cleared",
  committee_review: "Committee Reviewing", awarded: "Awarded", rejected: "Rejected",
  withdrawn: "Withdrawn", closed: "Closed",
};

export default function VendorDashboard() {
  const nav = useNavigate();
  const [vendor, setVendor] = useState(null);
  const [notices, setNotices] = useState([]);
  const [bids, setBids] = useState([]);
  const [tab, setTab] = useState("tenders");

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
  }, [nav]);

  const logout = async () => {
    try { await vendorApi.logout(); } catch { /* ignore */ }
    nav("/vendor/login");
  };

  if (!vendor) return <div className="p-10 text-slate-500">Loading…</div>;

  return (
    <div className="min-h-screen bg-slate-50" data-testid="vendor-dashboard">
      <header className="bg-[#0b1e3f] text-white">
        <div className="max-w-6xl mx-auto px-6 py-4 flex items-center justify-between">
          <div>
            <div className="text-xs tracking-widest uppercase text-amber-300">Vendor Portal</div>
            <h1 className="text-lg font-serif">{vendor.company_name || vendor.email}</h1>
          </div>
          <div className="text-sm flex items-center gap-4">
            <span className="text-white/70">{vendor.vendor_ref}</span>
            <button onClick={logout} className="text-white/80 hover:text-white underline"
              data-testid="vendor-logout">Sign out</button>
          </div>
        </div>
      </header>

      <div className="max-w-6xl mx-auto px-6 py-6">
        <div className="flex gap-4 border-b mb-6">
          <button onClick={() => setTab("tenders")}
            className={`pb-2 text-sm ${tab === "tenders" ? "border-b-2 border-slate-900 font-semibold" : "text-slate-500"}`}
            data-testid="vendor-tab-tenders">Open tenders ({notices.length})</button>
          <button onClick={() => setTab("bids")}
            className={`pb-2 text-sm ${tab === "bids" ? "border-b-2 border-slate-900 font-semibold" : "text-slate-500"}`}
            data-testid="vendor-tab-bids">My bids ({bids.length})</button>
        </div>

        {tab === "tenders" && (
          <div className="grid md:grid-cols-2 gap-4" data-testid="vendor-tender-list">
            {notices.map((n) => (
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
        )}

        {tab === "bids" && (
          <div className="space-y-3" data-testid="vendor-bid-list">
            {bids.map((b) => (
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
                  {(b.status === "emd_pending" || b.status === "submitted") && b.emd_due_amount > 0 && (
                    <button
                      onClick={async () => {
                        try {
                          const r = await bidApi.get(b.id); void r;
                          const chk = await (await import("@/lib/api")).paymentApi
                            .checkout(b.id, window.location.origin);
                          window.location.href = chk.checkout_url;
                        } catch (err) { toast.error(formatApiError(err)); }
                      }}
                      className="text-xs bg-amber-500 text-white px-3 py-1.5 rounded hover:bg-amber-600"
                      data-testid={`pay-emd-${b.bid_ref}`}>Pay EMD</button>
                  )}
                </div>
              </div>
            ))}
            {bids.length === 0 && <div className="text-slate-500 text-sm">You haven't placed any bids yet.</div>}
          </div>
        )}
      </div>
    </div>
  );
}
