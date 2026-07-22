import { useEffect, useState } from "react";
import { useParams, useNavigate, Link } from "react-router-dom";
import DashboardLayout from "@/components/app/DashboardLayout";
import api, { formatApiError } from "@/lib/api";
import StatusBadge from "@/components/app/StatusBadge";
import { useAuth } from "@/context/AuthContext";
import { toast } from "sonner";
import { Upload, X, ArrowLeft, Timer, Building, MapPin, Download, ShieldAlert } from "lucide-react";
import { CURRENCIES } from "@/data/countries";
import { BACKEND_URL } from "@/lib/api";

function countdown(iso) {
  const diff = new Date(iso).getTime() - Date.now();
  if (diff <= 0) return "Closed";
  const d = Math.floor(diff / 86400000);
  const h = Math.floor((diff % 86400000) / 3600000);
  const m = Math.floor((diff % 3600000) / 60000);
  return `${d}d ${h}h ${m}m`;
}

export default function TenderDetail() {
  const { id } = useParams();
  const nav = useNavigate();
  const { user } = useAuth();
  const [tender, setTender] = useState(null);
  const [bids, setBids] = useState([]);
  const [myBid, setMyBid] = useState(null);
  const [profileStatus, setProfileStatus] = useState(null);
  const [tick, setTick] = useState(0);

  useEffect(() => { const t = setInterval(() => setTick((v) => v + 1), 30000); return () => clearInterval(t); }, []);

  const load = async () => {
    try {
      const { data } = await api.get(`/tenders/${id}`);
      setTender(data);
    } catch (e) { toast.error(formatApiError(e)); }
    try {
      if (user?.role === "vendor") {
        const { data } = await api.get(`/bids?tender_id=${id}`);
        setMyBid(data[0] || null);
      } else {
        const { data } = await api.get(`/bids?tender_id=${id}`);
        setBids(data);
      }
    } catch {}
    if (user?.role === "vendor") {
      try { const { data } = await api.get("/vendor/profile"); setProfileStatus(data.vendor_status); } catch {}
    }
  };
  useEffect(() => { load(); /* eslint-disable-next-line */ }, [id, user?.role]);

  const closeTender = async () => {
    try { await api.post(`/tenders/${id}/close`); toast.success("Tender closed"); load(); } catch (e) { toast.error(formatApiError(e)); }
  };

  const award = async (bidId) => {
    try { await api.post(`/bids/${bidId}/award`); toast.success("Bid awarded"); load(); } catch (e) { toast.error(formatApiError(e)); }
  };

  if (!tender) return <DashboardLayout title="Loading..." />;

  const canManage = user && (user.role === "admin" || (user.role === "buyer" && tender.created_by === user.id));
  const canBid = user?.role === "vendor" && profileStatus === "approved" && tender.status === "open" && !myBid;

  return (
    <DashboardLayout
      title={tender.title}
      subtitle={`Published by ${tender.created_by_name || tender.created_by_email}`}
      actions={<StatusBadge status={tender.status} testid="tender-detail-status" />}
    >
      <button onClick={() => nav(-1)} className="mb-6 text-sm text-muted-foreground inline-flex items-center gap-2 hover:text-foreground">
        <ArrowLeft className="h-4 w-4" /> Back
      </button>

      <div className="grid lg:grid-cols-[1fr_320px] gap-8">
        <div className="min-w-0 space-y-8">
          <div className="border p-6 md:p-8">
            <div className="pmc-label mb-3">Tender ID <span className="font-mono normal-case tracking-normal ml-2 text-primary">#{tender.id.slice(-6).toUpperCase()}</span></div>
            <h2 className="font-serif text-3xl mb-2 tracking-tight">{tender.title}</h2>
            <div className="flex flex-wrap gap-6 text-sm text-muted-foreground mb-6">
              <span className="inline-flex items-center gap-2"><Building className="h-4 w-4" />{tender.category}</span>
              {tender.delivery_location && <span className="inline-flex items-center gap-2"><MapPin className="h-4 w-4" />{tender.delivery_location}</span>}
              <span className="inline-flex items-center gap-2 font-mono"><Timer className="h-4 w-4" />{countdown(tender.submission_deadline)}{tick && ""}</span>
            </div>
            <div className="pmc-label mb-2">Scope of work</div>
            <p className="whitespace-pre-line text-sm leading-relaxed">{tender.description}</p>

            {tender.eligibility_criteria && (
              <>
                <div className="pmc-label mt-6 mb-2">Eligibility criteria</div>
                <p className="whitespace-pre-line text-sm leading-relaxed">{tender.eligibility_criteria}</p>
              </>
            )}

            {(tender.required_licenses || []).length > 0 && (
              <div className="mt-6 border border-l-4 border-primary bg-primary/5 p-4" data-testid="tender-required-licenses">
                <div className="pmc-label text-primary flex items-center gap-2"><ShieldAlert className="h-3.5 w-3.5" /> Required licenses (Kazakhstan)</div>
                <div className="text-sm mt-2">Bidders must hold: <span className="font-mono">{tender.required_licenses.join(", ")}</span></div>
              </div>
            )}

            {tender.attachments?.length > 0 && (
              <>
                <div className="pmc-label mt-6 mb-2">Attachments</div>
                <ul className="border">
                  {tender.attachments.map((a, i) => (
                    <li key={i} className="flex items-center justify-between px-4 py-2 border-b last:border-b-0 text-sm">
                      <span>{a.name}</span>
                      <a href={a.data} download={a.name} className="text-primary underline underline-offset-4">Download</a>
                    </li>
                  ))}
                </ul>
              </>
            )}
          </div>

          {/* Vendor bid area */}
          {user?.role === "vendor" && (
            <VendorBidSection tender={tender} myBid={myBid} canBid={canBid} profileStatus={profileStatus} onSubmitted={load} />
          )}

          {/* Buyer/Admin bid comparison */}
          {(user?.role === "admin" || user?.role === "buyer") && (
            <BidsComparison bids={bids} tender={tender} canManage={canManage} onAward={award} />
          )}
        </div>

        {/* Right rail */}
        <aside className="space-y-4">
          <div className="border p-6 border-l-4 border-primary bg-muted/20">
            <div className="pmc-label mb-1">Budget</div>
            <div className="font-mono text-2xl">{tender.budget_amount ? `${tender.budget_currency} ${tender.budget_amount.toLocaleString()}` : "Undisclosed"}</div>
          </div>
          <div className="border p-6">
            <div className="pmc-label mb-1">Deadline</div>
            <div className="font-mono text-sm">{new Date(tender.submission_deadline).toLocaleString()}</div>
            <div className="pmc-label mt-4 mb-1">Time remaining</div>
            <div data-testid="tender-countdown" className="font-mono text-2xl">{countdown(tender.submission_deadline)}</div>
          </div>
          {canManage && tender.status === "open" && (
            <button data-testid="tender-close-btn" onClick={closeTender} className="w-full border border-destructive text-destructive py-3 text-sm hover:bg-destructive hover:text-white transition-colors">
              Close tender
            </button>
          )}
        </aside>
      </div>
    </DashboardLayout>
  );
}

function VendorBidSection({ tender, myBid, canBid, profileStatus, onSubmitted }) {
  const [form, setForm] = useState({ price_currency: tender.budget_currency || "USD", price_amount: "", delivery_days: 30, proposal: "", attachments: [] });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((s) => ({ ...s, [k]: e.target.value }));

  const submit = async (e) => {
    e.preventDefault(); setBusy(true);
    try {
      await api.post("/bids", { ...form, tender_id: tender.id, price_amount: Number(form.price_amount), delivery_days: Number(form.delivery_days) });
      toast.success("Bid submitted");
      onSubmitted();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const onUpload = async (e) => {
    const files = Array.from(e.target.files || []);
    if (!files.length) return;
    const uploaded = [];
    for (const f of files) {
      const fd = new FormData(); fd.append("file", f);
      const { data } = await api.post("/uploads", fd, { headers: { "Content-Type": "multipart/form-data" } });
      uploaded.push(data);
    }
    setForm((s) => ({ ...s, attachments: [...s.attachments, ...uploaded] }));
    e.target.value = "";
  };

  if (myBid) {
    return (
      <div className="border p-6 md:p-8" data-testid="vendor-existing-bid">
        <div className="pmc-label mb-2">Your submitted bid</div>
        <h3 className="font-serif text-2xl">Bid #{myBid.id.slice(-6).toUpperCase()} <StatusBadge status={myBid.status} /></h3>
        <div className="grid md:grid-cols-3 gap-6 mt-6 text-sm">
          <div><div className="pmc-label mb-1">Price</div><div className="font-mono text-xl">{myBid.price_currency} {myBid.price_amount.toLocaleString()}</div></div>
          <div><div className="pmc-label mb-1">Delivery</div><div className="font-mono text-xl">{myBid.delivery_days} days</div></div>
          <div><div className="pmc-label mb-1">Submitted</div><div className="font-mono text-xs">{new Date(myBid.created_at).toLocaleString()}</div></div>
        </div>
        <div className="pmc-label mt-6 mb-2">Proposal</div>
        <p className="whitespace-pre-line text-sm">{myBid.proposal}</p>
      </div>
    );
  }

  if (!canBid) {
    return (
      <div className="border p-6 border-l-4 border-warning bg-warning/10">
        <div className="pmc-label text-warning">You cannot bid yet</div>
        <div className="mt-1 text-sm">
          {tender.status !== "open"
            ? "This tender is no longer open for bidding."
            : profileStatus !== "approved"
            ? "Your vendor profile is not approved yet. Complete your KYC and wait for compliance clearance."
            : "You have already submitted a bid."}
        </div>
      </div>
    );
  }

  return (
    <form onSubmit={submit} className="border p-6 md:p-8" data-testid="bid-form">
      <div className="pmc-label mb-2">Submit your bid</div>
      <h3 className="font-serif text-2xl mb-4">Your proposal</h3>
      <div className="grid md:grid-cols-3 gap-5">
        <div>
          <label className="pmc-label block mb-2">Currency</label>
          <select data-testid="bid-currency" value={form.price_currency} onChange={set("price_currency")} className="w-full h-12 px-4 border border-input bg-white">
            {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="pmc-label block mb-2">Price</label>
          <input data-testid="bid-amount" required type="number" min="0" step="any" value={form.price_amount} onChange={set("price_amount")}
            className="w-full h-12 px-4 border border-input bg-white focus:border-primary focus:outline-none" />
        </div>
        <div>
          <label className="pmc-label block mb-2">Delivery days</label>
          <input data-testid="bid-days" required type="number" min="1" value={form.delivery_days} onChange={set("delivery_days")}
            className="w-full h-12 px-4 border border-input bg-white focus:border-primary focus:outline-none" />
        </div>
      </div>
      <div className="mt-5">
        <label className="pmc-label block mb-2">Proposal</label>
        <textarea data-testid="bid-proposal" required rows={5} value={form.proposal} onChange={set("proposal")}
          className="w-full px-4 py-3 border border-input bg-white focus:border-primary focus:outline-none" />
      </div>
      <div className="mt-5">
        <label className="pmc-label block mb-2">Attachments</label>
        <label className="block border border-dashed border-input hover:border-primary p-4 text-center cursor-pointer text-sm">
          <input data-testid="bid-file" type="file" multiple onChange={onUpload} className="hidden" />
          <Upload className="mx-auto h-4 w-4 mb-2 text-muted-foreground" /> Upload files
        </label>
        {form.attachments.length > 0 && (
          <ul className="border mt-3">
            {form.attachments.map((d, i) => (
              <li key={i} className="flex justify-between items-center px-4 py-2 border-b last:border-b-0 text-sm">
                <span>{d.name}</span>
                <button type="button" onClick={() => setForm((s) => ({ ...s, attachments: s.attachments.filter((_, idx) => idx !== i) }))}>
                  <X className="h-4 w-4" />
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
      <div className="mt-6 flex justify-end border-t pt-4">
        <button data-testid="bid-submit" disabled={busy} className="bg-primary text-white px-6 py-3 text-sm hover:-translate-y-0.5 transition-transform disabled:opacity-60">
          {busy ? "Submitting..." : "Submit bid"}
        </button>
      </div>
    </form>
  );
}

function BidsComparison({ bids, tender, canManage, onAward }) {
  if (!bids.length) return <div className="border p-8 text-center text-sm text-muted-foreground">No bids received yet.</div>;
  const min = Math.min(...bids.map((b) => b.price_amount));
  const csvUrl = `${BACKEND_URL}/api/tenders/${tender.id}/bids/export`;
  return (
    <div className="border">
      <div className="p-4 border-b bg-muted/30 flex items-center justify-between gap-4">
        <div>
          <div className="pmc-label">Bids received</div>
          <div className="font-serif text-2xl mt-1">{bids.length} vendor{bids.length > 1 ? "s" : ""} responded</div>
        </div>
        {canManage && (
          <a data-testid="export-csv" href={csvUrl} className="inline-flex items-center gap-2 text-sm border border-foreground px-3 py-2 hover:bg-foreground hover:text-white transition-colors">
            <Download className="h-4 w-4" /> Export CSV
          </a>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm pmc-table" data-testid="bids-comparison-table">
          <thead>
            <tr className="border-b bg-muted/30">
              <Th>Vendor</Th><Th>Price</Th><Th>Delivery</Th><Th>Proposal</Th><Th>Status</Th><Th></Th>
            </tr>
          </thead>
          <tbody>
            {bids.map((b) => {
              const isLowest = b.price_amount === min;
              return (
                <tr key={b.id} className={`border-b ${isLowest ? "bg-primary/5" : "hover:bg-muted/40"}`}>
                  <Td>
                    <div className="font-medium">{b.vendor_company || b.vendor_email}</div>
                    <div className="text-xs text-muted-foreground">{b.vendor_email}</div>
                  </Td>
                  <Td className="font-mono">
                    {isLowest && <span className="mr-2 pmc-label text-primary">LOWEST</span>}
                    {b.price_currency} {b.price_amount.toLocaleString()}
                  </Td>
                  <Td className="font-mono">{b.delivery_days}d</Td>
                  <Td className="max-w-md truncate" title={b.proposal}>{b.proposal}</Td>
                  <Td><StatusBadge status={b.status} /></Td>
                  <Td>
                    {canManage && tender.status === "open" && (
                      <button data-testid={`award-bid-${b.id}`} onClick={() => onAward(b.id)} className="text-sm bg-primary text-white px-3 py-1.5 hover:-translate-y-0.5 transition-transform">Award</button>
                    )}
                  </Td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function Th({ children }) { return <th className="text-left px-4 py-3 pmc-label border-b">{children}</th>; }
function Td({ children, className = "" }) { return <td className={`px-4 py-3 ${className}`}>{children}</td>; }
