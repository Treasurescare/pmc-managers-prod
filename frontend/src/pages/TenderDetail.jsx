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
      actions={
        <div className="flex items-center gap-2">
          <span data-testid="tender-doctype" className="pmc-label px-2 py-1 border border-primary text-primary">{(tender.document_type || "tender").toUpperCase()}</span>
          <StatusBadge status={tender.status} testid="tender-detail-status" />
        </div>
      }
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

            {tender.document_type === "rfq" && (tender.line_items || []).length > 0 && (
              <div className="mt-6 border" data-testid="tender-line-items">
                <div className="p-4 border-b bg-muted/30">
                  <div className="pmc-label text-primary">RFQ · Line items to quote</div>
                  <div className="font-serif text-xl mt-1">Itemised quotation table</div>
                </div>
                <table className="w-full text-sm">
                  <thead><tr className="border-b bg-muted/20"><th className="pmc-label text-left px-3 py-2">#</th><th className="pmc-label text-left px-3 py-2">Item</th><th className="pmc-label text-left px-3 py-2">Qty</th><th className="pmc-label text-left px-3 py-2">Unit</th><th className="pmc-label text-left px-3 py-2">Target price</th></tr></thead>
                  <tbody>
                    {tender.line_items.map((li, i) => (
                      <tr key={i} className="border-b">
                        <td className="px-3 py-2 font-mono text-xs">{String(i + 1).padStart(2, "0")}</td>
                        <td className="px-3 py-2">{li.item}</td>
                        <td className="px-3 py-2 font-mono">{li.qty}</td>
                        <td className="px-3 py-2 font-mono">{li.unit}</td>
                        <td className="px-3 py-2 font-mono">{li.target_unit_price ? `${tender.budget_currency} ${Number(li.target_unit_price).toLocaleString()}` : "—"}</td>
                      </tr>
                    ))}
                  </tbody>
                </table>
                <div className="grid md:grid-cols-2 gap-4 p-4 border-t text-sm">
                  {tender.payment_terms && (<div><div className="pmc-label mb-1">Payment terms</div><div>{tender.payment_terms}</div></div>)}
                  {tender.delivery_date && (<div><div className="pmc-label mb-1">Required delivery</div><div className="font-mono">{tender.delivery_date}</div></div>)}
                </div>
              </div>
            )}

            {tender.document_type === "rfp" && (
              <div className="mt-6 border" data-testid="tender-rfp-block">
                <div className="p-4 border-b bg-muted/30 flex items-center justify-between gap-3">
                  <div>
                    <div className="pmc-label text-primary">RFP · Evaluation framework</div>
                    <div className="font-serif text-xl mt-1">How your proposal will be judged</div>
                  </div>
                  {tender.two_envelope && (
                    <span data-testid="rfp-two-envelope-badge" className="text-[10px] font-semibold tracking-widest px-2 py-1 border border-primary text-primary">
                      TWO-ENVELOPE
                    </span>
                  )}
                </div>
                <div className="p-4 space-y-4 text-sm">
                  {tender.scope_of_work && (<div><div className="pmc-label mb-1">Full scope of work</div><p className="whitespace-pre-line">{tender.scope_of_work}</p></div>)}
                  {tender.expected_deliverables && (<div><div className="pmc-label mb-1">Expected deliverables</div><p className="whitespace-pre-line">{tender.expected_deliverables}</p></div>)}
                  {(tender.evaluation_criteria || []).length > 0 && (
                    <div>
                      <div className="pmc-label mb-1">Evaluation criteria</div>
                      <table className="w-full border">
                        <thead><tr className="border-b bg-muted/20"><th className="pmc-label text-left px-3 py-2">Criterion</th><th className="pmc-label text-left px-3 py-2">Weight</th><th className="pmc-label text-left px-3 py-2">Description</th></tr></thead>
                        <tbody>{tender.evaluation_criteria.map((c, i) => (
                          <tr key={i} className="border-b"><td className="px-3 py-2">{c.name}</td><td className="px-3 py-2 font-mono">{c.weight}%</td><td className="px-3 py-2 text-muted-foreground">{c.description}</td></tr>
                        ))}</tbody>
                      </table>
                    </div>
                  )}
                  {(tender.evaluation_committee || []).length > 0 && (
                    <div>
                      <div className="pmc-label mb-1">Evaluation committee</div>
                      <ul className="text-sm">{tender.evaluation_committee.map((m, i) => (<li key={i}>· {m.name} — <span className="text-muted-foreground">{m.role}</span></li>))}</ul>
                    </div>
                  )}
                  {tender.pre_bid_meeting_date && (<div><div className="pmc-label mb-1">Pre-bid meeting</div><div className="font-mono">{new Date(tender.pre_bid_meeting_date).toLocaleString()}</div></div>)}
                  {tender.bid_bond_amount && (<div><div className="pmc-label mb-1">Bid bond</div><div className="font-mono">USD {Number(tender.bid_bond_amount).toLocaleString()}</div></div>)}
                </div>
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
            <BidsComparison bids={bids} tender={tender} canManage={canManage} onAward={award} onScored={load} />
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
  const isRFQ = tender.document_type === "rfq";
  const isRFP = tender.document_type === "rfp";
  const initialLineItemPrices = isRFQ ? (tender.line_items || []).map((li) => ({ item: li.item, qty: li.qty, unit: li.unit, unit_price: "", subtotal: 0 })) : [];
  const [form, setForm] = useState({
    price_currency: tender.budget_currency || "USD",
    price_amount: "",
    delivery_days: 30,
    proposal: "",
    attachments: [],
    line_item_prices: initialLineItemPrices,
    technical_proposal: "",
    commercial_proposal: "",
    team_composition: "",
  });
  const [busy, setBusy] = useState(false);
  const set = (k) => (e) => setForm((s) => ({ ...s, [k]: e.target.value }));

  const updateLineItemPrice = (i, unit_price) => {
    setForm((s) => {
      const list = s.line_item_prices.map((li, idx) => {
        if (idx !== i) return li;
        const p = Number(unit_price);
        const q = Number(li.qty) || 0;
        return { ...li, unit_price, subtotal: !isNaN(p) ? p * q : 0 };
      });
      const total = list.reduce((sum, x) => sum + (Number(x.subtotal) || 0), 0);
      return { ...s, line_item_prices: list, price_amount: total };
    });
  };

  const submit = async (e) => {
    e.preventDefault();
    if (isRFP && !form.technical_proposal) { toast.error("Technical proposal is required for RFP responses."); return; }
    if (isRFQ && form.line_item_prices.some((li) => li.unit_price === "" || li.unit_price === null)) { toast.error("Enter a unit price for every line item."); return; }
    setBusy(true);
    try {
      const payload = {
        ...form, tender_id: tender.id,
        price_amount: Number(form.price_amount),
        delivery_days: Number(form.delivery_days),
        proposal: form.proposal || (isRFP ? form.technical_proposal : isRFQ ? `RFQ response: ${form.line_item_prices.length} line items` : ""),
      };
      await api.post("/bids", payload);
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
        {(myBid.line_item_prices || []).length > 0 && (
          <>
            <div className="pmc-label mt-6 mb-2">Line items</div>
            <table className="w-full text-sm border"><thead><tr className="bg-muted/30 border-b"><th className="pmc-label text-left px-3 py-2">Item</th><th className="pmc-label text-left px-3 py-2">Qty</th><th className="pmc-label text-left px-3 py-2">Unit price</th><th className="pmc-label text-left px-3 py-2">Subtotal</th></tr></thead><tbody>
              {myBid.line_item_prices.map((li, i) => (<tr key={i} className="border-b"><td className="px-3 py-2">{li.item}</td><td className="px-3 py-2 font-mono">{li.qty} {li.unit}</td><td className="px-3 py-2 font-mono">{myBid.price_currency} {Number(li.unit_price).toLocaleString()}</td><td className="px-3 py-2 font-mono">{myBid.price_currency} {Number(li.subtotal).toLocaleString()}</td></tr>))}
            </tbody></table>
          </>
        )}
        {myBid.technical_proposal && (<><div className="pmc-label mt-6 mb-2">Technical proposal</div><p className="whitespace-pre-line text-sm">{myBid.technical_proposal}</p></>)}
        {myBid.commercial_proposal && (<><div className="pmc-label mt-6 mb-2">Commercial proposal</div><p className="whitespace-pre-line text-sm">{myBid.commercial_proposal}</p></>)}
        {myBid.proposal && !myBid.technical_proposal && (<><div className="pmc-label mt-6 mb-2">Proposal</div><p className="whitespace-pre-line text-sm">{myBid.proposal}</p></>)}
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
      <div className="pmc-label mb-2">Submit your {isRFP ? "proposal" : isRFQ ? "quotation" : "bid"}</div>
      <h3 className="font-serif text-2xl mb-4">{isRFP ? "Your RFP response" : isRFQ ? "Your quotation" : "Your bid"}</h3>

      {/* RFQ line-item pricing */}
      {isRFQ && (
        <div className="mb-6">
          <div className="pmc-label mb-2">Line items · enter unit prices</div>
          <table className="w-full text-sm border" data-testid="bid-line-items-table">
            <thead><tr className="border-b bg-muted/30"><th className="pmc-label text-left px-3 py-2">#</th><th className="pmc-label text-left px-3 py-2">Item</th><th className="pmc-label text-left px-3 py-2">Qty</th><th className="pmc-label text-left px-3 py-2">Unit</th><th className="pmc-label text-left px-3 py-2">Your unit price ({form.price_currency})</th><th className="pmc-label text-left px-3 py-2">Subtotal</th></tr></thead>
            <tbody>
              {form.line_item_prices.map((li, i) => (
                <tr key={i} className="border-b" data-testid={`bid-li-${i}`}>
                  <td className="px-3 py-2 font-mono text-xs">{String(i + 1).padStart(2, "0")}</td>
                  <td className="px-3 py-2">{li.item}</td>
                  <td className="px-3 py-2 font-mono">{li.qty}</td>
                  <td className="px-3 py-2 font-mono">{li.unit}</td>
                  <td className="px-2 py-1 w-40">
                    <input data-testid={`bid-li-${i}-price`} type="number" min="0" step="any" value={li.unit_price} onChange={(e) => updateLineItemPrice(i, e.target.value)} className="w-full h-9 px-2 border border-input bg-white" />
                  </td>
                  <td className="px-3 py-2 font-mono">{Number(li.subtotal || 0).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
            <tfoot>
              <tr className="bg-muted/30"><td colSpan={5} className="px-3 py-2 text-right pmc-label">Total</td><td className="px-3 py-2 font-mono font-bold" data-testid="bid-total">{form.price_currency} {Number(form.price_amount || 0).toLocaleString()}</td></tr>
            </tfoot>
          </table>
        </div>
      )}

      {/* RFP technical + commercial */}
      {isRFP && (
        <div className="space-y-5 mb-6">
          <div>
            <label className="pmc-label block mb-2">Technical proposal <span className="text-destructive">*</span></label>
            <textarea data-testid="bid-technical" required rows={6} value={form.technical_proposal} onChange={set("technical_proposal")} className="w-full px-4 py-3 border border-input bg-white focus:border-primary focus:outline-none" />
          </div>
          <div>
            <label className="pmc-label block mb-2">Commercial proposal / pricing narrative</label>
            <textarea data-testid="bid-commercial" rows={4} value={form.commercial_proposal} onChange={set("commercial_proposal")} className="w-full px-4 py-3 border border-input bg-white focus:border-primary focus:outline-none" />
          </div>
          <div>
            <label className="pmc-label block mb-2">Team composition / key personnel</label>
            <textarea data-testid="bid-team" rows={3} value={form.team_composition} onChange={set("team_composition")} className="w-full px-4 py-3 border border-input bg-white focus:border-primary focus:outline-none" />
          </div>
        </div>
      )}

      {/* Common price / delivery */}
      <div className="grid md:grid-cols-3 gap-5">
        <div>
          <label className="pmc-label block mb-2">Currency</label>
          <select data-testid="bid-currency" value={form.price_currency} onChange={set("price_currency")} className="w-full h-12 px-4 border border-input bg-white">
            {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
          </select>
        </div>
        <div>
          <label className="pmc-label block mb-2">{isRFQ ? "Total (auto)" : "Price"}</label>
          <input data-testid="bid-amount" required={!isRFQ} readOnly={isRFQ} type="number" min="0" step="any" value={form.price_amount} onChange={set("price_amount")}
            className={`w-full h-12 px-4 border border-input focus:border-primary focus:outline-none ${isRFQ ? "bg-muted" : "bg-white"}`} />
        </div>
        <div>
          <label className="pmc-label block mb-2">Delivery days</label>
          <input data-testid="bid-days" required type="number" min="1" value={form.delivery_days} onChange={set("delivery_days")}
            className="w-full h-12 px-4 border border-input bg-white focus:border-primary focus:outline-none" />
        </div>
      </div>

      {!isRFP && (
        <div className="mt-5">
          <label className="pmc-label block mb-2">{isRFQ ? "Notes to buyer" : "Proposal"}</label>
          <textarea data-testid="bid-proposal" required={!isRFQ} rows={isRFQ ? 3 : 5} value={form.proposal} onChange={set("proposal")}
            className="w-full px-4 py-3 border border-input bg-white focus:border-primary focus:outline-none" />
        </div>
      )}

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
          {busy ? "Submitting..." : `Submit ${isRFP ? "proposal" : isRFQ ? "quotation" : "bid"}`}
        </button>
      </div>
    </form>
  );
}

function BidsComparison({ bids, tender, canManage, onAward, onScored }) {
  if (!bids.length) return <div className="border p-8 text-center text-sm text-muted-foreground">No bids received yet.</div>;
  const csvUrl = `${BACKEND_URL}/api/tenders/${tender.id}/bids/export`;
  const isRFQ = tender.document_type === "rfq";
  const isRFP = tender.document_type === "rfp";

  return (
    <div className="border">
      <div className="p-4 border-b bg-muted/30 flex items-center justify-between gap-4">
        <div>
          <div className="pmc-label">Bids received · {tender.document_type?.toUpperCase() || "TENDER"}{tender.two_envelope ? " · TWO-ENVELOPE" : ""}</div>
          <div className="font-serif text-2xl mt-1">{bids.length} vendor{bids.length > 1 ? "s" : ""} responded</div>
        </div>
        {canManage && (
          <a data-testid="export-csv" href={csvUrl} className="inline-flex items-center gap-2 text-sm border border-foreground px-3 py-2 hover:bg-foreground hover:text-white transition-colors">
            <Download className="h-4 w-4" /> Export CSV
          </a>
        )}
      </div>

      {tender.two_envelope && (
        <TwoEnvelopePanel tender={tender} bids={bids} canManage={canManage} onChanged={onScored} />
      )}

      {isRFP ? (
        <RfpScoringMatrix bids={bids} tender={tender} canManage={canManage} onAward={onAward} onScored={onScored} />
      ) : isRFQ && (tender.line_items || []).length > 0 ? (
        <RfqLineItemMatrix bids={bids} tender={tender} canManage={canManage} onAward={onAward} />
      ) : (
        <FlatBidTable bids={bids} tender={tender} canManage={canManage} onAward={onAward} />
      )}
    </div>
  );
}

function TwoEnvelopePanel({ tender, bids, canManage, onChanged }) {
  const [busy, setBusy] = useState(null);
  const techOpen = !!tender.technical_opened_at;
  const commOpen = !!tender.commercial_opened_at;
  const qualified = bids.filter((b) => b.technical_qualified === true).length;
  const disqualified = bids.filter((b) => b.technical_qualified === false).length;
  const pending = bids.length - qualified - disqualified;

  const openTech = async () => {
    setBusy("tech");
    try { await api.post(`/tenders/${tender.id}/open-technical`); toast.success("Technical envelopes opened"); onChanged && onChanged(); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(null); }
  };
  const openComm = async () => {
    setBusy("comm");
    try { await api.post(`/tenders/${tender.id}/open-commercial`); toast.success("Commercial envelopes opened"); onChanged && onChanged(); }
    catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(null); }
  };

  const stage = commOpen ? 3 : techOpen ? 2 : 1;
  const stageLabels = ["Sealed", "Technical open · Qualifying", "Commercial open · Awarding"];

  return (
    <div className="border-b bg-primary/[0.04] p-4" data-testid="two-envelope-panel">
      <div className="flex flex-wrap items-center justify-between gap-4">
        <div>
          <div className="pmc-label text-primary">Two-envelope evaluation</div>
          <div className="font-serif text-lg mt-1" data-testid="te-stage-label">Stage {stage} · {stageLabels[stage - 1]}</div>
          <div className="text-xs text-muted-foreground mt-1 font-mono">
            {qualified} qualified · {disqualified} disqualified · {pending} pending
          </div>
        </div>
        {canManage && (
          <div className="flex gap-2">
            {!techOpen && (
              <button data-testid="te-open-technical" onClick={openTech} disabled={busy === "tech"}
                className="text-sm bg-primary text-white px-4 py-2 hover:-translate-y-0.5 transition-transform disabled:opacity-60">
                {busy === "tech" ? "Opening..." : "Open Technical Envelopes"}
              </button>
            )}
            {techOpen && !commOpen && (
              <button data-testid="te-open-commercial" onClick={openComm} disabled={busy === "comm" || qualified === 0}
                title={qualified === 0 ? "Qualify at least one bid first" : ""}
                className="text-sm bg-primary text-white px-4 py-2 hover:-translate-y-0.5 transition-transform disabled:opacity-60">
                {busy === "comm" ? "Opening..." : `Open Commercial Envelopes (${qualified})`}
              </button>
            )}
            {commOpen && (
              <div className="text-sm px-4 py-2 border border-primary text-primary">
                Ready to award qualified bids
              </div>
            )}
          </div>
        )}
      </div>
      <div className="mt-3 grid grid-cols-3 gap-2">
        {[1,2,3].map((n) => (
          <div key={n} className={`h-1.5 ${n <= stage ? "bg-primary" : "bg-muted"}`} />
        ))}
      </div>
    </div>
  );
}

function FlatBidTable({ bids, tender, canManage, onAward }) {
  const min = Math.min(...bids.map((b) => b.price_amount));
  return (
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
  );
}

function RfqLineItemMatrix({ bids, tender, canManage, onAward }) {
  const items = tender.line_items || [];
  const totalMin = Math.min(...bids.map((b) => b.price_amount));

  const getUnit = (bid, idx) => {
    const lip = (bid.line_item_prices || [])[idx];
    return lip && lip.unit_price !== undefined && lip.unit_price !== "" ? Number(lip.unit_price) : null;
  };

  // per-row min across bids
  const rowMins = items.map((_, rowIdx) => {
    const vals = bids.map((b) => getUnit(b, rowIdx)).filter((v) => v !== null && !isNaN(v));
    return vals.length ? Math.min(...vals) : null;
  });

  return (
    <div className="overflow-x-auto" data-testid="rfq-matrix">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/30">
            <th className="pmc-label text-left px-3 py-2 sticky left-0 bg-muted/30 min-w-[240px]">Line item</th>
            <th className="pmc-label text-left px-3 py-2">Qty × Unit</th>
            {bids.map((b) => (
              <th key={b.id} className="pmc-label text-left px-3 py-2 min-w-[160px]">
                <div>{b.vendor_company || b.vendor_email}</div>
                <div className="text-[10px] text-muted-foreground normal-case tracking-normal">{b.vendor_email}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {items.map((it, rowIdx) => (
            <tr key={rowIdx} className="border-b">
              <td className="px-3 py-2 sticky left-0 bg-white">
                <div className="font-mono text-xs text-muted-foreground">{String(rowIdx + 1).padStart(2, "0")}</div>
                <div>{it.item}</div>
              </td>
              <td className="px-3 py-2 font-mono text-xs">{it.qty} × {it.unit}</td>
              {bids.map((b) => {
                const v = getUnit(b, rowIdx);
                const isMin = v !== null && rowMins[rowIdx] !== null && v === rowMins[rowIdx];
                return (
                  <td key={b.id} className={`px-3 py-2 font-mono ${isMin ? "bg-primary/10 text-primary font-bold" : ""}`} data-testid={`matrix-${rowIdx}-${b.id}`}>
                    {v === null ? "—" : v.toLocaleString()}
                    {isMin && <span className="ml-2 text-[10px] tracking-widest">LOW</span>}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-foreground bg-muted/40">
            <td className="px-3 py-3 pmc-label sticky left-0 bg-muted/40">Total</td>
            <td className="px-3 py-3"></td>
            {bids.map((b) => {
              const isLowTotal = b.price_amount === totalMin;
              return (
                <td key={b.id} className={`px-3 py-3 font-mono font-bold ${isLowTotal ? "bg-primary text-white" : ""}`}>
                  {b.price_currency} {Number(b.price_amount).toLocaleString()}
                  {isLowTotal && <div className="text-[10px] tracking-widest mt-0.5">LOWEST</div>}
                </td>
              );
            })}
          </tr>
          <tr className="border-t bg-white">
            <td className="px-3 py-2 pmc-label sticky left-0 bg-white">Delivery</td>
            <td></td>
            {bids.map((b) => (<td key={b.id} className="px-3 py-2 font-mono text-xs">{b.delivery_days}d</td>))}
          </tr>
          <tr className="border-t bg-white">
            <td className="px-3 py-2 pmc-label sticky left-0 bg-white">Status</td>
            <td></td>
            {bids.map((b) => (<td key={b.id} className="px-3 py-2"><StatusBadge status={b.status} /></td>))}
          </tr>
          {canManage && tender.status === "open" && (
            <tr className="border-t bg-white">
              <td className="px-3 py-2 pmc-label sticky left-0 bg-white">Award</td>
              <td></td>
              {bids.map((b) => (
                <td key={b.id} className="px-3 py-2">
                  <button data-testid={`award-bid-${b.id}`} onClick={() => onAward(b.id)} className="text-xs bg-primary text-white px-3 py-1.5">Award</button>
                </td>
              ))}
            </tr>
          )}
        </tfoot>
      </table>
    </div>
  );
}

function RfpScoringMatrix({ bids, tender, canManage, onAward, onScored }) {
  const criteria = tender.evaluation_criteria || [];
  const [drafts, setDrafts] = useState({});
  const [saving, setSaving] = useState({});
  const [qualBusy, setQualBusy] = useState({});

  const isTwoEnv = !!tender.two_envelope;
  const techOpen = !!tender.technical_opened_at;
  const commOpen = !!tender.commercial_opened_at;
  const scoringLocked = isTwoEnv && !techOpen;

  const draftFor = (bid) => drafts[bid.id] || bid.rfp_scores || {};
  const setScore = (bidId, name, val) => setDrafts((s) => ({ ...s, [bidId]: { ...(s[bidId] || {}), [name]: val } }));

  const weightedTotal = (scores) => criteria.reduce((sum, c) => {
    const s = Number(scores[c.name] || 0);
    return sum + (Number(c.weight) || 0) * (isNaN(s) ? 0 : s) / 100;
  }, 0);

  const saveScore = async (bidId) => {
    setSaving((s) => ({ ...s, [bidId]: true }));
    try {
      const scores = draftFor({ id: bidId });
      const { data } = await api.post(`/bids/${bidId}/score`, { scores });
      toast.success(`Bid scored · Weighted total: ${data.weighted_total}`);
      onScored && onScored();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setSaving((s) => ({ ...s, [bidId]: false })); }
  };

  const qualifyBid = async (bidId, qualified) => {
    setQualBusy((s) => ({ ...s, [bidId]: true }));
    try {
      await api.post(`/bids/${bidId}/qualify`, { qualified });
      toast.success(qualified ? "Bid marked qualified" : "Bid marked disqualified");
      onScored && onScored();
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setQualBusy((s) => ({ ...s, [bidId]: false })); }
  };

  const bestBidId = bids.reduce((best, b) => {
    const wt = b.rfp_weighted_total || 0;
    if (!best || wt > (best.wt || 0)) return { id: b.id, wt };
    return best;
  }, null)?.id;

  if (!criteria.length) {
    return <div className="p-6 text-sm text-muted-foreground">This RFP has no evaluation criteria defined — please add them before scoring bids.</div>;
  }

  const priceCell = (b) => {
    if (isTwoEnv && (!commOpen || b.technical_qualified !== true)) {
      return <span className="pmc-label text-muted-foreground">SEALED</span>;
    }
    return <>{b.price_currency} {Number(b.price_amount).toLocaleString()} · {b.delivery_days}d</>;
  };

  return (
    <div className="overflow-x-auto" data-testid="rfp-scoring-matrix">
      {scoringLocked && (
        <div className="px-4 py-3 bg-muted/40 border-b text-sm text-muted-foreground" data-testid="rfp-scoring-locked">
          Scoring is locked until Technical envelopes are opened above.
        </div>
      )}
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b bg-muted/30">
            <th className="pmc-label text-left px-3 py-2 sticky left-0 bg-muted/30 min-w-[220px]">Criterion (weight)</th>
            {bids.map((b) => (
              <th key={b.id} className="pmc-label text-left px-3 py-2 min-w-[180px]">
                <div className="flex items-center gap-2">
                  <span>{b.vendor_company || b.vendor_email}</span>
                  {isTwoEnv && b.technical_qualified === true && (
                    <span data-testid={`qual-badge-${b.id}`} className="text-[9px] tracking-widest px-1.5 py-0.5 bg-success text-white">QUALIFIED</span>
                  )}
                  {isTwoEnv && b.technical_qualified === false && (
                    <span data-testid={`disq-badge-${b.id}`} className="text-[9px] tracking-widest px-1.5 py-0.5 bg-destructive text-white">DISQUALIFIED</span>
                  )}
                </div>
                <div className="text-[10px] text-muted-foreground normal-case tracking-normal">{b.vendor_email}</div>
              </th>
            ))}
          </tr>
        </thead>
        <tbody>
          {criteria.map((c, idx) => (
            <tr key={idx} className="border-b" data-testid={`crit-row-${idx}`}>
              <td className="px-3 py-2 sticky left-0 bg-white">
                <div>{c.name}</div>
                <div className="text-xs text-muted-foreground">{c.description}</div>
                <div className="pmc-label mt-1 text-primary">{c.weight}%</div>
              </td>
              {bids.map((b) => {
                const val = draftFor(b)[c.name] ?? "";
                return (
                  <td key={b.id} className="px-3 py-2">
                    {canManage ? (
                      <input
                        data-testid={`score-${idx}-${b.id}`}
                        type="number" min="0" max="100" value={val}
                        onChange={(e) => setScore(b.id, c.name, e.target.value)}
                        placeholder="0–100"
                        disabled={scoringLocked}
                        className="w-20 h-9 px-2 border border-input bg-white font-mono focus:border-primary focus:outline-none disabled:bg-muted disabled:cursor-not-allowed"
                      />
                    ) : (
                      <span className="font-mono">{val || "—"}</span>
                    )}
                  </td>
                );
              })}
            </tr>
          ))}
        </tbody>
        <tfoot>
          <tr className="border-t-2 border-foreground bg-muted/40">
            <td className="px-3 py-3 pmc-label sticky left-0 bg-muted/40">Weighted total</td>
            {bids.map((b) => {
              const wt = weightedTotal(draftFor(b));
              const isBest = b.id === bestBidId;
              return (
                <td key={b.id} className={`px-3 py-3 font-mono font-bold ${isBest && b.rfp_weighted_total ? "bg-primary text-white" : ""}`} data-testid={`total-${b.id}`}>
                  {wt.toFixed(2)} / 100
                  {isBest && b.rfp_weighted_total > 0 && <div className="text-[10px] tracking-widest mt-0.5">TOP</div>}
                </td>
              );
            })}
          </tr>
          <tr className="border-t bg-white">
            <td className="px-3 py-2 pmc-label sticky left-0 bg-white">Commercial (price)</td>
            {bids.map((b) => (
              <td key={b.id} className="px-3 py-2 font-mono text-xs" data-testid={`price-cell-${b.id}`}>{priceCell(b)}</td>
            ))}
          </tr>
          {canManage && isTwoEnv && techOpen && !commOpen && (
            <tr className="border-t bg-white">
              <td className="px-3 py-2 pmc-label sticky left-0 bg-white">Qualification</td>
              {bids.map((b) => (
                <td key={b.id} className="px-3 py-2">
                  <div className="flex gap-1">
                    <button
                      data-testid={`qualify-${b.id}`}
                      onClick={() => qualifyBid(b.id, true)}
                      disabled={qualBusy[b.id]}
                      className={`text-xs px-2 py-1 border transition-colors ${b.technical_qualified === true ? "bg-success text-white border-success" : "border-input hover:bg-success/10"}`}
                    >
                      Qualify
                    </button>
                    <button
                      data-testid={`disqualify-${b.id}`}
                      onClick={() => qualifyBid(b.id, false)}
                      disabled={qualBusy[b.id]}
                      className={`text-xs px-2 py-1 border transition-colors ${b.technical_qualified === false ? "bg-destructive text-white border-destructive" : "border-input hover:bg-destructive/10"}`}
                    >
                      Reject
                    </button>
                  </div>
                </td>
              ))}
            </tr>
          )}
          {canManage && (
            <tr className="border-t bg-white">
              <td className="px-3 py-2 pmc-label sticky left-0 bg-white">Actions</td>
              {bids.map((b) => {
                const awardBlocked = isTwoEnv && (!commOpen || b.technical_qualified !== true);
                return (
                  <td key={b.id} className="px-3 py-2 flex gap-2">
                    <button data-testid={`save-score-${b.id}`} onClick={() => saveScore(b.id)} disabled={saving[b.id] || scoringLocked}
                      className="text-xs border border-foreground px-3 py-1.5 hover:bg-foreground hover:text-white disabled:opacity-60 disabled:cursor-not-allowed">
                      {saving[b.id] ? "Saving..." : "Save score"}
                    </button>
                    {tender.status === "open" && (
                      <button
                        data-testid={`award-bid-${b.id}`}
                        onClick={() => onAward(b.id)}
                        disabled={awardBlocked}
                        title={awardBlocked ? (commOpen ? "Not technically qualified" : "Open commercial envelopes first") : ""}
                        className="text-xs bg-primary text-white px-3 py-1.5 disabled:opacity-40 disabled:cursor-not-allowed"
                      >
                        Award
                      </button>
                    )}
                  </td>
                );
              })}
            </tr>
          )}
        </tfoot>
      </table>
    </div>
  );
}

function Th({ children }) { return <th className="text-left px-4 py-3 pmc-label border-b">{children}</th>; }
function Td({ children, className = "" }) { return <td className={`px-4 py-3 ${className}`}>{children}</td>; }
