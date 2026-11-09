import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import VendorPortalChrome from "./VendorPortalChrome";
import { marketApi, MODE_LABEL, money } from "@/lib/marketApi";
import { payNeeded } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";
import { DocList, PhotoStrip } from "./MarketMediaPicker";
import { CategoryPicker, LocationPicker } from "./MarketFormPickers";
import { AiFillButton } from "./AiFillButton";
import { CurrencySelect } from "@/components/CurrencySelect";
import CatalogueImportE from "./CatalogueImportE";

const EMPTY = { title: "", description: "", category: "", quantity: 1, unit: "lot", currency: "USD", location: "", image_url: "", photos: [], documents: [],
  country_code: "", state_code: "", state_name: "", city: "", zip: "",
  sale_modes: ["auction"], start_price: "", reserve_price: "", min_increment: 1, buy_now_price: "", closes_at: "", eligibility: "verified_buyers" };

const toBody = (f) => ({ ...f, quantity: Number(f.quantity) || 1, min_increment: Number(f.min_increment) || 1,
  start_price: f.start_price === "" ? null : Number(f.start_price), reserve_price: f.reserve_price === "" ? null : Number(f.reserve_price),
  buy_now_price: f.buy_now_price === "" ? null : Number(f.buy_now_price),
  closes_at: f.closes_at ? new Date(f.closes_at).toISOString() : null, currency: (f.currency || "USD").toUpperCase() });

function Field({ label, children }) {
  return <label className="text-sm block">{label}<div className="mt-1">{children}</div></label>;
}

function ListingForm({ initial, onSaved, onCancel }) {
  const [f, setF] = useState(initial || EMPTY);
  const set = (k, v) => setF((x) => ({ ...x, [k]: v }));
  const toggle = (m) => set("sale_modes", f.sale_modes.includes(m) ? f.sale_modes.filter((x) => x !== m) : [...f.sale_modes, m]);
  const onCurrency = useCallback((v) => setF((x) => ({ ...x, currency: v })), []);
  const save = async () => {
    try {
      if (f.id) await marketApi.update(f.id, toBody(f)); else await marketApi.create(toBody(f));
      toast.success("Saved as draft — submit it for PMC approval when ready");
      onSaved();
    } catch (e) { showApiError(e); }
  };
  const inp = (k, type = "text", extra = {}) => <input type={type} className="pmc-input w-full" value={f[k] ?? ""} onChange={(e) => set(k, e.target.value)} data-testid={`mkt-f-${k}`} {...extra} />;
  const aiFill = useCallback((p, doc) => setF((x) => ({ ...x, title: p.title || x.title, unit: p.unit || x.unit, category: p.category || x.category,
    description: [p.description, (p.specs || []).length ? `Specifications:\n${p.specs.map((s) => `• ${s}`).join("\n")}` : ""].filter(Boolean).join("\n\n") || x.description,
    photos: [...new Set([...(x.photos || []), ...(p.photos || [])])].slice(0, 12),
    documents: doc && !(x.documents || []).some((d) => d.id === doc.id) ? [...(x.documents || []), doc].slice(0, 6) : x.documents })), []);
  return (
    <section className="pmc-panel p-4 mt-4 grid gap-3 md:grid-cols-2" data-testid="mkt-listing-form">
      <AiFillButton onFill={aiFill} />
      <Field label="Product title *">{inp("title")}</Field>
      <Field label="Category"><CategoryPicker value={f.category} onChange={(v) => set("category", v)} /></Field>
      <div className="md:col-span-2"><Field label="Description"><textarea className="pmc-input w-full" rows={4} value={f.description} onChange={(e) => set("description", e.target.value)} data-testid="mkt-f-description" /></Field></div>
      <Field label="Quantity">{inp("quantity", "number", { min: 0 })}</Field>
      <Field label="Unit (e.g. lot, unit, tonne)">{inp("unit")}</Field>
      <Field label="Currency"><CurrencySelect country={f.country_code} value={f.currency} onChange={onCurrency} preserveInitial={!!f.id} testId="mkt-f-currency" className="pmc-input w-full" /></Field>
      <div className="md:col-span-2"><Field label="Where is the product? (country → state → city → ZIP)"><LocationPicker f={f} setF={setF} /></Field></div>
      <div className="md:col-span-2"><Field label="Product photos (up to 12 · framed to 4:3, 1200 × 900)"><PhotoStrip photos={f.photos || []} onChange={(fn) => setF((x) => ({ ...x, photos: fn(x.photos || []) }))} /></Field></div>
      <div className="md:col-span-2"><Field label="Spec sheets / brochures (PDF, up to 6)"><DocList docs={f.documents || []} onChange={(fn) => setF((x) => ({ ...x, documents: fn(x.documents || []) }))} /></Field></div>
      <div className="md:col-span-2"><Field label="Or a photo link (optional)">{inp("image_url", "url")}</Field></div>
      <div className="md:col-span-2">
        <div className="text-sm font-medium">How do you want to sell? (pick one or more)</div>
        <div className="flex flex-wrap gap-4 mt-1">
          {Object.entries(MODE_LABEL).map(([m, l]) => (
            <label key={m} className="text-sm flex items-center gap-2"><input type="checkbox" checked={f.sale_modes.includes(m)} onChange={() => toggle(m)} data-testid={`mkt-mode-${m}`} />{l}</label>))}
        </div>
      </div>
      {f.sale_modes.includes("auction") && <>
        <Field label="Auction starting price *">{inp("start_price", "number", { min: 0 })}</Field>
        <Field label="Reserve price (hidden; no sale below it)">{inp("reserve_price", "number", { min: 0 })}</Field>
        <Field label="Minimum bid increase">{inp("min_increment", "number", { min: 0 })}</Field>
      </>}
      {f.sale_modes.includes("fixed") && <Field label="Fixed (buy-now) price *">{inp("buy_now_price", "number", { min: 0 })}</Field>}
      {(f.sale_modes.includes("auction") || f.sale_modes.includes("best_offer")) &&
        <Field label="Closing date & time *">{inp("closes_at", "datetime-local")}</Field>}
      <Field label="Who may bid or buy?">
        <select className="pmc-input w-full" value={f.eligibility} onChange={(e) => set("eligibility", e.target.value)} data-testid="mkt-f-eligibility">
          <option value="verified_buyers">Verified buyer organisations only</option>
          <option value="any_verified">Any verified account (buyers and suppliers)</option>
        </select>
      </Field>
      <div className="md:col-span-2 flex gap-2">
        <button type="button" className="pmc-btn pmc-btn--primary" onClick={save} data-testid="mkt-save">Save draft</button>
        <button type="button" className="pmc-btn pmc-btn--secondary" onClick={onCancel} data-testid="mkt-cancel">Cancel</button>
      </div>
    </section>);
}

function ListingRow({ l, reload, onEdit }) {
  const act = async (fn, ok) => {
    try { await fn(); toast.success(ok); reload(); } catch (e) {
      const pay = payNeeded(e);
      if (pay?.checkout_url) { toast(pay.message, { action: { label: "Pay listing fee", onClick: () => { window.location.href = pay.checkout_url; } } }); }
      else showApiError(e);
    }
  };
  return (
    <div className="pmc-panel p-3" data-testid={`mkt-row-${l.id}`}>
      <div className="flex flex-wrap justify-between gap-2">
        <div><b>{l.title}</b> <span className="text-xs opacity-70">· {l.sale_modes.map((m) => MODE_LABEL[m]).join(", ")}</span>{l.needs_details && <span className="text-xs ml-2 text-amber-400" data-testid={`mkt-needs-${l.id}`}>· set price & how to sell (Edit)</span>}</div>
        <span className="text-xs uppercase tracking-wide" data-testid={`mkt-status-${l.id}`}>{l.status}</span>
      </div>
      <div className="text-xs opacity-80 mt-1">Top bid {money(l.currency, l.top_bid)} · {l.bid_count} {l.bid_count === 1 ? "bid" : "bids"}{l.closes_at ? ` · closes ${new Date(l.closes_at).toLocaleString()}` : ""}{l.review_notes ? ` · PMC note: ${l.review_notes}` : ""}</div>
      <div className="flex flex-wrap gap-2 mt-2">
        {["draft", "rejected"].includes(l.status) && <>
          <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => onEdit(l)} data-testid={`mkt-edit-${l.id}`}>Edit</button>
          <button className="pmc-btn pmc-btn--primary pmc-btn--sm" onClick={() => act(() => marketApi.submit(l.id), "Sent to PMC for approval")} data-testid={`mkt-submit-${l.id}`}>Submit for approval</button>
        </>}
        {["draft", "pending", "rejected", "live"].includes(l.status) && !l.bid_count &&
          <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => act(() => marketApi.withdraw(l.id), "Withdrawn")} data-testid={`mkt-withdraw-${l.id}`}>Withdraw</button>}
      </div>
      {l.offers?.length > 0 && <div className="mt-2 text-sm pb-14 md:pb-0" data-testid={`mkt-offers-${l.id}`}>
        <div className="font-medium">Offers</div>
        {l.offers.map((o) => (
          <div key={o.id} className="flex justify-between gap-2 py-1 border-t border-white/10">
            <span>{money(l.currency, o.amount)} — {o.bidder?.name}{o.note ? ` · “${o.note}”` : ""}</span>
            <button className="pmc-btn pmc-btn--primary pmc-btn--sm" onClick={() => act(() => marketApi.acceptOffer(o.id), "Offer accepted — the buyer gets a payment link")} data-testid={`mkt-accept-${o.id}`}>Accept</button>
          </div>))}
      </div>}
    </div>);
}

export default function VendorMarketE() {
  const [data, setData] = useState({ items: [], orders: [], fee: null });
  const [form, setForm] = useState(null);
  const [importing, setImporting] = useState(false);
  const load = () => marketApi.mine().then(setData).catch(showApiError);
  useEffect(() => { load(); }, []);
  const localDt = (iso) => { const d = new Date(iso); return new Date(d.getTime() - d.getTimezoneOffset() * 60000).toISOString().slice(0, 16); };
  const edit = (l) => setForm({ ...EMPTY, ...l, photos: l.photos || [], documents: l.documents || [], closes_at: l.closes_at ? localDt(l.closes_at) : "", start_price: l.start_price ?? "", reserve_price: l.reserve_price ?? "", buy_now_price: l.buy_now_price ?? "" });
  const fee = data.fee;
  return (
    <VendorPortalChrome active="Sell products">
      <div data-testid="vendor-market-page">
        <h1 className="text-2xl font-semibold">Sell your products</h1>
        <p className="text-sm opacity-80 mt-1 max-w-3xl">List products from your catalogue and sell them by timed auction, best offer or fixed price — no tender needed. Every listing is checked by PMC before buyers can see it. Buyers pay through a secure PMC payment link; PMC deducts its sale fee{fee ? ` (${fee.charge ? (fee.fee_type === "percent" ? `${fee.fee_value}% of the sale` : `${fee.fee_value} per sale`) : "currently none"})` : ""} and pays the rest to your registered bank account.</p>
        {!form && !importing && <div className="flex flex-wrap gap-2 mt-3">
          <button className="pmc-btn pmc-btn--primary" onClick={() => setForm(EMPTY)} data-testid="mkt-new">Add a product</button>
          <button className="pmc-btn pmc-btn--secondary" onClick={() => setImporting(true)} data-testid="mkt-import">Import from a catalogue with AI</button>
        </div>}
        {importing && <CatalogueImportE onDone={() => { setImporting(false); load(); }} onCancel={() => setImporting(false)} />}
        {form && <ListingForm initial={form} onSaved={() => { setForm(null); load(); }} onCancel={() => setForm(null)} />}
        <h2 className="text-lg font-semibold mt-6">My listings</h2>
        <div className="grid gap-2 mt-2" data-testid="mkt-my-listings">
          {data.items.length === 0 && <p className="text-sm opacity-70">No products listed yet.</p>}
          {data.items.map((l) => <ListingRow key={l.id} l={l} reload={load} onEdit={edit} />)}
        </div>
        <h2 className="text-lg font-semibold mt-6">Sales</h2>
        <div className="grid gap-2 mt-2" data-testid="mkt-sales">
          {data.orders.length === 0 && <p className="text-sm opacity-70">No sales yet.</p>}
          {data.orders.map((o) => (
            <div key={o.id} className="pmc-panel p-3 text-sm" data-testid={`mkt-sale-${o.id}`}>
              <b>{o.title}</b> — sold to {o.buyer?.name} for {money(o.currency, o.amount)} ({MODE_LABEL[o.via]}) · PMC fee {money(o.currency, o.pmc_fee)} · you receive <b>{money(o.currency, o.seller_net)}</b> · payment: {o.status.replace("_", " ")} · payout: {o.payout_status.replace("_", " ")}{o.payout_reference ? ` (ref ${o.payout_reference})` : ""}
            </div>))}
        </div>
      </div>
    </VendorPortalChrome>);
}
