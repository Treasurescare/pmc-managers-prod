import { useEffect, useState } from "react";
import { toast } from "sonner";
import AdminEShell from "./AdminEShell";
import { marketApi, mediaUrl, MODE_LABEL, money } from "@/lib/marketApi";
import { showApiError } from "@/lib/api";
import { CategoryReviewQueue, HomeAdverts } from "./AdminMarketExtras";

function FeeSettings() {
  const [s, setS] = useState(null);
  useEffect(() => { marketApi.settings().then(setS).catch(showApiError); }, []);
  if (!s) return null;
  const save = () => marketApi.saveSettings({ ...s, fee_value: Number(s.fee_value) || 0 }).then((r) => { setS(r); toast.success("Sale fee saved"); }).catch(showApiError);
  return (
    <section className="pmc-panel p-4 flex flex-wrap items-end gap-3" data-testid="mkt-fee-settings">
      <div className="text-sm font-semibold w-full">PMC sale fee (deducted before paying the seller)</div>
      <label className="text-sm"><input type="checkbox" checked={s.charge} onChange={(e) => setS({ ...s, charge: e.target.checked })} data-testid="mkt-fee-charge" /> Charge a sale fee</label>
      <select className="pmc-input" value={s.fee_type} onChange={(e) => setS({ ...s, fee_type: e.target.value })} data-testid="mkt-fee-type">
        <option value="percent">% of sale value</option><option value="fixed">Fixed amount per sale</option>
      </select>
      <input type="number" min="0" step="0.01" className="pmc-input w-32" value={s.fee_value} onChange={(e) => setS({ ...s, fee_value: e.target.value })} data-testid="mkt-fee-value" />
      <button className="pmc-btn pmc-btn--primary" onClick={save} data-testid="mkt-fee-save">Save</button>
      <div className="text-xs opacity-70 w-full">The listing fee is set in Pricing → fee rules as "Marketplace product listing".</div>
    </section>);
}

function Approvals() {
  const [items, setItems] = useState([]);
  const [status, setStatus] = useState("pending");
  const [waive, setWaive] = useState({});
  const [notes, setNotes] = useState({});
  const load = () => marketApi.adminListings(status).then((r) => setItems(r.items)).catch(showApiError);
  useEffect(() => { load(); }, [status]); // eslint-disable-line react-hooks/exhaustive-deps
  const decide = (id, action) => marketApi.decide(id, { action, waive_sale_fee: !!waive[id], notes: notes[id] || "" })
    .then(() => { toast.success(action === "approve" ? "Approved — now live" : "Rejected"); load(); }).catch(showApiError);
  return (
    <section className="mt-4" data-testid="mkt-approvals">
      <div className="flex gap-2 items-center"><b>Listings</b>
        <select className="pmc-input" value={status} onChange={(e) => setStatus(e.target.value)} data-testid="mkt-admin-status">
          {["pending", "live", "sold", "rejected", "closed_unsold", "all"].map((x) => <option key={x} value={x}>{x}</option>)}
        </select></div>
      {items.length === 0 && <p className="text-sm opacity-70 mt-2">Nothing here.</p>}
      {items.map((l) => (
        <div key={l.id} className="pmc-panel p-3 mt-2 text-sm" data-testid={`mkt-admin-row-${l.id}`}>
          <div><b>{l.title}</b> · {l.seller_name} · {l.sale_modes.map((m) => MODE_LABEL[m]).join(", ")} · {l.status}</div>
          <div className="opacity-80 mt-1">{l.description?.slice(0, 300)}</div>
          {(l.photos?.length > 0 || l.documents?.length > 0) && <div className="flex flex-wrap gap-2 mt-2 items-center" data-testid={`mkt-admin-media-${l.id}`}>
            {(l.photos || []).map((p) => <a key={p} href={mediaUrl(p)} target="_blank" rel="noreferrer"><img src={mediaUrl(p)} alt="" className="w-14 h-14 object-cover rounded" /></a>)}
            {(l.documents || []).map((d) => <a key={d.id} href={mediaUrl(d.id)} target="_blank" rel="noreferrer" className="underline text-xs">{d.name}</a>)}
          </div>}
          <div className="opacity-80 mt-1">Start {money(l.currency, l.start_price)} · reserve {money(l.currency, l.reserve_price)} · buy-now {money(l.currency, l.buy_now_price)}{l.closes_at ? ` · closes ${new Date(l.closes_at).toLocaleString()}` : ""} · {l.eligibility === "verified_buyers" ? "buyers only" : "any verified"}</div>
          {l.status === "pending" && <div className="flex flex-wrap gap-2 mt-2 items-center">
            <label><input type="checkbox" checked={!!waive[l.id]} onChange={(e) => setWaive({ ...waive, [l.id]: e.target.checked })} data-testid={`mkt-waive-${l.id}`} /> Waive sale fee</label>
            <input className="pmc-input" placeholder="Note to supplier" value={notes[l.id] || ""} onChange={(e) => setNotes({ ...notes, [l.id]: e.target.value })} data-testid={`mkt-note-${l.id}`} />
            <button className="pmc-btn pmc-btn--primary pmc-btn--sm" onClick={() => decide(l.id, "approve")} data-testid={`mkt-approve-${l.id}`}>Approve</button>
            <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => decide(l.id, "reject")} data-testid={`mkt-reject-${l.id}`}>Reject</button>
          </div>}
        </div>))}
    </section>);
}

function Orders() {
  const [items, setItems] = useState([]);
  const [ref, setRef] = useState({});
  const load = () => marketApi.adminOrders().then((r) => setItems(r.items)).catch(showApiError);
  useEffect(() => { load(); }, []);
  const payout = (id) => marketApi.payout(id, ref[id] || "").then(() => { toast.success("Payout recorded"); load(); }).catch(showApiError);
  return (
    <section className="mt-6" data-testid="mkt-orders">
      <b>Sales & seller payouts</b>
      {items.length === 0 && <p className="text-sm opacity-70 mt-2">No sales yet.</p>}
      {items.map((o) => (
        <div key={o.id} className="pmc-panel p-3 mt-2 text-sm" data-testid={`mkt-order-${o.id}`}>
          <div><b>{o.title}</b> · {o.seller_name} → {o.buyer?.name} · {money(o.currency, o.amount)} · PMC fee {money(o.currency, o.pmc_fee)} · seller net <b>{money(o.currency, o.seller_net)}</b></div>
          <div className="opacity-80">Payment {o.status.replace("_", " ")} · payout {o.payout_status.replace("_", " ")}{o.payout_reference ? ` (ref ${o.payout_reference})` : ""} · Bank: {o.seller_bank?.bank_name || "—"} {o.seller_bank?.bank_account_number || ""} {o.seller_bank?.bank_swift || ""}</div>
          {o.status === "paid" && o.payout_status === "due" && <div className="flex gap-2 mt-2">
            <input className="pmc-input" placeholder="Bank transfer reference" value={ref[o.id] || ""} onChange={(e) => setRef({ ...ref, [o.id]: e.target.value })} data-testid={`mkt-payout-ref-${o.id}`} />
            <button className="pmc-btn pmc-btn--primary pmc-btn--sm" onClick={() => payout(o.id)} data-testid={`mkt-payout-${o.id}`}>Mark seller paid</button>
          </div>}
        </div>))}
    </section>);
}

export default function AdminMarketE() {
  return (
    <div data-testid="admin-market-e">
      <AdminEShell active="Marketplace" crumb={<>Market / <b>Supplier marketplace</b></>}>
        <h1 className="text-2xl font-semibold mb-3">Supplier marketplace</h1>
        <FeeSettings />
        <Approvals />
        <CategoryReviewQueue />
        <HomeAdverts />
        <Orders />
      </AdminEShell>
    </div>);
}
