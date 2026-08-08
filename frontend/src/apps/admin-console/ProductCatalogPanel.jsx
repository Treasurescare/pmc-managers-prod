/**
 * ProductCatalogPanel — admin master of every revenue-stream line item.
 *
 * Renders a filterable, sortable table of catalog entries (both client &
 * supplier sides). Admin can edit every field inline via a modal; the
 * backend is fully idempotent so seed defaults never overwrite edits.
 */
import { useEffect, useMemo, useState, useCallback } from "react";
import { toast } from "sonner";
import UnspscPicker from "@/components/UnspscPicker";

const API = process.env.REACT_APP_BACKEND_URL;

const PRICING_MODELS = [
  { v: "fixed", l: "Fixed one-off" },
  { v: "range", l: "Range (quote)" },
  { v: "percentage", l: "% of value" },
  { v: "monthly", l: "Monthly subscription" },
  { v: "annual", l: "Annual subscription" },
  { v: "per_delegate", l: "Per delegate" },
  { v: "per_user_monthly", l: "Per user / month" },
  { v: "cost_recovery", l: "Cost recovery" },
  { v: "package", l: "Package (bundle)" },
];
const SIDES = [
  { v: "client", l: "Client (buyer)" },
  { v: "supplier", l: "Supplier (vendor)" },
  { v: "both", l: "Both" },
];
const CURRENCIES = ["USD", "GBP", "EUR", "KZT", "INR", "AED", "SAR"];

const EMPTY = {
  code: "", name: "", side: "client", category: "", subcategory: "",
  description: "", pricing_model: "fixed", currency: "USD",
  amount: "", min_amount: "", max_amount: "",
  percentage: "", percentage_of: "",
  unit_label: "", package_tier: "", conditions: "",
  is_active: true, display_order: 100,
  unspsc_code: "", unspsc_title: "",
};

function ProductRow({ p, onEdit, onToggle }) {
  const priceCell = () => {
    if (p.pricing_model === "percentage") return `${p.percentage}% of ${p.percentage_of || "value"}`;
    if (p.pricing_model === "range") return `${p.currency} ${(p.min_amount || 0).toLocaleString()} – ${(p.max_amount || 0).toLocaleString()}`;
    if (p.pricing_model === "cost_recovery") return "at cost";
    const unit = p.pricing_model.startsWith("monthly") ? "/mo"
              : p.pricing_model === "annual" ? "/yr"
              : p.pricing_model === "per_delegate" ? "/delegate"
              : p.pricing_model === "per_user_monthly" ? "/user/mo" : "";
    return `${p.currency} ${(p.amount || 0).toLocaleString()}${unit}`;
  };
  return (
    <tr className={`border-b border-brand-navy/10 ${p.is_active ? "" : "opacity-50"}`}
        data-testid={`product-row-${p.code}`}>
      <td className="px-3 py-3 font-mono text-xs">{p.code}</td>
      <td className="px-3 py-3">
        <div className="font-semibold">{p.name}</div>
        <div className="text-xs text-brand-navy/60">{p.category}{p.package_tier ? ` · ${p.package_tier}` : ""}</div>
      </td>
      <td className="px-3 py-3 text-xs">
        <span className={`px-2 py-1 uppercase tracking-widest ${
          p.side === "client" ? "bg-sky-100 text-sky-900"
          : p.side === "supplier" ? "bg-emerald-100 text-emerald-900"
          : "bg-purple-100 text-purple-900"}`}>{p.side}</span>
      </td>
      <td className="px-3 py-3 text-xs">{PRICING_MODELS.find(m => m.v === p.pricing_model)?.l || p.pricing_model}</td>
      <td className="px-3 py-3 text-right font-mono tabular-nums text-sm">{priceCell()}</td>
      <td className="px-3 py-3 text-right space-x-2">
        <button onClick={() => onEdit(p)} data-testid={`product-edit-${p.code}`}
                className="text-xs uppercase tracking-widest text-brand-navy hover:underline">Edit</button>
        <button onClick={() => onToggle(p)} data-testid={`product-toggle-${p.code}`}
                className={`text-xs uppercase tracking-widest hover:underline ${p.is_active ? "text-red-700" : "text-emerald-700"}`}>
          {p.is_active ? "Disable" : "Enable"}
        </button>
      </td>
    </tr>
  );
}

function ProductEditor({ item, onClose, onSaved }) {
  const [form, setForm] = useState(() => ({ ...EMPTY, ...(item || {}) }));
  const [saving, setSaving] = useState(false);
  const isNew = !item?.id;

  const set = (k, v) => setForm((s) => ({ ...s, [k]: v }));

  const save = async () => {
    setSaving(true);
    const body = { ...form };
    for (const k of ["amount", "min_amount", "max_amount", "percentage", "display_order"]) {
      body[k] = body[k] === "" || body[k] == null ? null : Number(body[k]);
    }
    try {
      const url = isNew ? `${API}/api/v1/products` : `${API}/api/v1/products/${item.id}`;
      const r = await fetch(url, {
        method: isNew ? "POST" : "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include", body: JSON.stringify(body),
      });
      if (!r.ok) throw new Error((await r.json()).detail || `HTTP ${r.status}`);
      toast.success(`${isNew ? "Created" : "Saved"} ${body.name}`);
      onSaved();
    } catch (e) {
      toast.error(`Save failed: ${e.message}`);
    } finally {
      setSaving(false);
    }
  };

  const showAmount = ["fixed", "monthly", "annual", "per_delegate", "per_user_monthly", "package"].includes(form.pricing_model);
  const showRange = form.pricing_model === "range";
  const showPct = form.pricing_model === "percentage";

  return (
    <div className="fixed inset-0 bg-brand-navy/40 backdrop-blur-sm z-50 flex items-start justify-center p-6 overflow-y-auto"
         data-testid="product-editor-modal">
      <div className="bg-white border-2 border-brand-navy w-full max-w-3xl p-8 my-8">
        <div className="flex items-center justify-between">
          <h3 className="font-display text-2xl text-brand-navy">{isNew ? "New product" : "Edit product"}</h3>
          <button onClick={onClose} data-testid="product-editor-close"
                  className="text-brand-navy/60 hover:text-brand-navy">✕</button>
        </div>

        <div className="mt-6 grid grid-cols-2 gap-4">
          <label className="col-span-1">
            <div className="pmc-label">Code (stable slug)</div>
            <input value={form.code} onChange={(e) => set("code", e.target.value)}
                   disabled={!isNew}
                   data-testid="product-form-code"
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2 font-mono text-sm disabled:bg-brand-navy/5"/>
          </label>
          <label className="col-span-1">
            <div className="pmc-label">Display order</div>
            <input type="number" value={form.display_order}
                   onChange={(e) => set("display_order", e.target.value)}
                   data-testid="product-form-order"
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2 font-mono text-sm"/>
          </label>
          <label className="col-span-2">
            <div className="pmc-label">Name</div>
            <input value={form.name} onChange={(e) => set("name", e.target.value)}
                   data-testid="product-form-name"
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/>
          </label>
          <label className="col-span-1">
            <div className="pmc-label">Side</div>
            <select value={form.side} onChange={(e) => set("side", e.target.value)}
                    data-testid="product-form-side"
                    className="mt-1 w-full border border-brand-navy/20 px-3 py-2 bg-white">
              {SIDES.map((s) => <option key={s.v} value={s.v}>{s.l}</option>)}
            </select>
          </label>
          <label className="col-span-1">
            <div className="pmc-label">Category</div>
            <input value={form.category} onChange={(e) => set("category", e.target.value)}
                   data-testid="product-form-category"
                   placeholder="Pre-Award / Post-Award / EOP / Package / …"
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/>
          </label>
          <label className="col-span-1">
            <div className="pmc-label">Pricing model</div>
            <select value={form.pricing_model}
                    onChange={(e) => set("pricing_model", e.target.value)}
                    data-testid="product-form-pricing"
                    className="mt-1 w-full border border-brand-navy/20 px-3 py-2 bg-white">
              {PRICING_MODELS.map((m) => <option key={m.v} value={m.v}>{m.l}</option>)}
            </select>
          </label>
          <label className="col-span-1">
            <div className="pmc-label">Currency</div>
            <select value={form.currency} onChange={(e) => set("currency", e.target.value)}
                    data-testid="product-form-currency"
                    className="mt-1 w-full border border-brand-navy/20 px-3 py-2 bg-white font-mono">
              {CURRENCIES.map((c) => <option key={c} value={c}>{c}</option>)}
            </select>
          </label>

          {showAmount && (
            <label className="col-span-1">
              <div className="pmc-label">Amount</div>
              <input type="number" value={form.amount ?? ""}
                     onChange={(e) => set("amount", e.target.value)}
                     data-testid="product-form-amount"
                     className="mt-1 w-full border border-brand-navy/20 px-3 py-2 font-mono tabular-nums"/>
            </label>
          )}
          {showRange && (
            <>
              <label className="col-span-1">
                <div className="pmc-label">Min amount</div>
                <input type="number" value={form.min_amount ?? ""}
                       onChange={(e) => set("min_amount", e.target.value)}
                       data-testid="product-form-min"
                       className="mt-1 w-full border border-brand-navy/20 px-3 py-2 font-mono tabular-nums"/>
              </label>
              <label className="col-span-1">
                <div className="pmc-label">Max amount</div>
                <input type="number" value={form.max_amount ?? ""}
                       onChange={(e) => set("max_amount", e.target.value)}
                       data-testid="product-form-max"
                       className="mt-1 w-full border border-brand-navy/20 px-3 py-2 font-mono tabular-nums"/>
              </label>
            </>
          )}
          {showPct && (
            <>
              <label className="col-span-1">
                <div className="pmc-label">Percentage (%)</div>
                <input type="number" step="0.01" value={form.percentage ?? ""}
                       onChange={(e) => set("percentage", e.target.value)}
                       data-testid="product-form-percentage"
                       className="mt-1 w-full border border-brand-navy/20 px-3 py-2 font-mono tabular-nums"/>
              </label>
              <label className="col-span-1">
                <div className="pmc-label">Of…</div>
                <input value={form.percentage_of ?? ""}
                       onChange={(e) => set("percentage_of", e.target.value)}
                       data-testid="product-form-percentage-of"
                       placeholder="contract_value / programme_value"
                       className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/>
              </label>
            </>
          )}

          <label className="col-span-1">
            <div className="pmc-label">Unit label (optional)</div>
            <input value={form.unit_label || ""} onChange={(e) => set("unit_label", e.target.value)}
                   placeholder="per delegate / per month"
                   data-testid="product-form-unit"
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/>
          </label>
          <label className="col-span-1">
            <div className="pmc-label">Package tier (optional)</div>
            <input value={form.package_tier || ""} onChange={(e) => set("package_tier", e.target.value)}
                   placeholder="Bronze / Silver / Gold / SME / Tier1"
                   data-testid="product-form-tier"
                   className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/>
          </label>

          <label className="col-span-2">
            <div className="pmc-label">Description</div>
            <textarea value={form.description || ""} onChange={(e) => set("description", e.target.value)}
                      data-testid="product-form-description" rows={3}
                      className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/>
          </label>
          <label className="col-span-2">
            <div className="pmc-label">Conditions / eligibility</div>
            <textarea value={form.conditions || ""} onChange={(e) => set("conditions", e.target.value)}
                      data-testid="product-form-conditions" rows={2}
                      className="mt-1 w-full border border-brand-navy/20 px-3 py-2"/>
          </label>
          <div className="col-span-2">
            <div className="pmc-label">UNSPSC classification (optional)</div>
            <div className="text-[11px] text-brand-navy/50 mb-1">
              Tag with the closest UNSPSC segment / family so buyers can find it via commodity code.
            </div>
            <UnspscPicker
              value={form.unspsc_code}
              title={form.unspsc_title}
              onChange={({ code, title }) => {
                set("unspsc_code", code);
                set("unspsc_title", title);
              }}
              testidPrefix="product-unspsc"
            />
          </div>
          <label className="col-span-2 flex items-center gap-2">
            <input type="checkbox" checked={!!form.is_active}
                   onChange={(e) => set("is_active", e.target.checked)}
                   data-testid="product-form-active"/>
            <span className="text-sm">Active — visible in the public catalog and to buyers</span>
          </label>
        </div>

        <div className="mt-8 flex items-center justify-end gap-3">
          <button onClick={onClose} data-testid="product-editor-cancel"
                  className="px-5 py-2 border border-brand-navy/20 text-sm">Cancel</button>
          <button onClick={save} disabled={saving} data-testid="product-editor-save"
                  className="px-5 py-2 bg-brand-navy text-white text-sm uppercase tracking-widest disabled:opacity-50">
            {saving ? "Saving…" : (isNew ? "Create" : "Save changes")}
          </button>
        </div>
      </div>
    </div>
  );
}

export default function ProductCatalogPanel() {
  const [items, setItems] = useState([]);
  const [loading, setLoading] = useState(true);
  const [sideFilter, setSideFilter] = useState("all");
  const [categoryFilter, setCategoryFilter] = useState("all");
  const [editing, setEditing] = useState(null);
  const [showNew, setShowNew] = useState(false);

  const reload = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/api/v1/products?active_only=false`, { credentials: "include" });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      const d = await r.json();
      setItems(d.items);
    } catch (e) {
      toast.error(`Load failed: ${e.message}`);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { reload(); }, [reload]);

  const categories = useMemo(() => Array.from(new Set(items.map((i) => i.category).filter(Boolean))).sort(), [items]);

  const filtered = useMemo(() => items.filter((i) => {
    if (sideFilter !== "all" && i.side !== sideFilter && i.side !== "both") return false;
    if (categoryFilter !== "all" && i.category !== categoryFilter) return false;
    return true;
  }), [items, sideFilter, categoryFilter]);

  const toggleActive = async (p) => {
    try {
      const r = await fetch(`${API}/api/v1/products/${p.id}`, {
        method: "PATCH",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ ...p, is_active: !p.is_active }),
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      toast.success(`${p.name} ${p.is_active ? "disabled" : "enabled"}`);
      reload();
    } catch (e) { toast.error(`Toggle failed: ${e.message}`); }
  };

  const reseed = async () => {
    try {
      const r = await fetch(`${API}/api/v1/products/reseed`, { method: "POST", credentials: "include" });
      const d = await r.json();
      toast.success(`Reseed complete — ${d.inserted} new default(s) inserted`);
      reload();
    } catch (e) { toast.error(`Reseed failed: ${e.message}`); }
  };

  const totals = useMemo(() => {
    const t = { client: 0, supplier: 0, both: 0, active: 0 };
    for (const i of items) {
      t[i.side] = (t[i.side] || 0) + 1;
      if (i.is_active) t.active += 1;
    }
    return t;
  }, [items]);

  return (
    <div className="space-y-6" data-testid="product-catalog-panel">
      <section className="flex items-start justify-between gap-6 flex-wrap">
        <div>
          <div className="pmc-label">Revenue-stream master</div>
          <h2 className="font-display text-2xl text-brand-navy mt-1">Product Catalog</h2>
          <p className="text-sm text-brand-navy/60 mt-2 max-w-xl">
            Every revenue line — client and supplier — is a catalog row. Edit any amount, currency
            or pricing model. Portals render live from here. Products are shared with Stripe on checkout.
          </p>
        </div>
        <div className="flex flex-col gap-2 items-end">
          <div className="flex gap-6 text-xs uppercase tracking-widest text-brand-navy/70">
            <span>Client: <b className="text-brand-navy">{totals.client}</b></span>
            <span>Supplier: <b className="text-brand-navy">{totals.supplier}</b></span>
            <span>Both: <b className="text-brand-navy">{totals.both}</b></span>
            <span>Active: <b className="text-emerald-700">{totals.active}</b></span>
          </div>
          <div className="flex gap-3">
            <button onClick={() => setShowNew(true)} data-testid="product-new-btn"
                    className="px-4 py-2 bg-brand-navy text-white text-xs uppercase tracking-widest">+ New product</button>
            <button onClick={reseed} data-testid="product-reseed-btn"
                    className="px-4 py-2 border border-brand-navy text-brand-navy text-xs uppercase tracking-widest">
              Reseed defaults
            </button>
          </div>
        </div>
      </section>

      <div className="flex gap-3 flex-wrap items-center">
        <span className="text-xs uppercase tracking-widest text-brand-navy/60">Filter:</span>
        <select value={sideFilter} onChange={(e) => setSideFilter(e.target.value)}
                data-testid="filter-side"
                className="border border-brand-navy/20 px-3 py-1 text-sm bg-white">
          <option value="all">All sides</option>
          <option value="client">Client only</option>
          <option value="supplier">Supplier only</option>
        </select>
        <select value={categoryFilter} onChange={(e) => setCategoryFilter(e.target.value)}
                data-testid="filter-category"
                className="border border-brand-navy/20 px-3 py-1 text-sm bg-white">
          <option value="all">All categories</option>
          {categories.map((c) => <option key={c} value={c}>{c}</option>)}
        </select>
      </div>

      {loading ? (
        <div className="text-brand-navy/60 py-10 text-center">Loading catalog…</div>
      ) : (
        <div className="border border-brand-navy/10 bg-white overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-brand-navy text-white uppercase text-xs tracking-widest">
              <tr>
                <th className="px-3 py-3 text-left">Code</th>
                <th className="px-3 py-3 text-left">Name / Category</th>
                <th className="px-3 py-3 text-left">Side</th>
                <th className="px-3 py-3 text-left">Model</th>
                <th className="px-3 py-3 text-right">Price</th>
                <th className="px-3 py-3 text-right">Actions</th>
              </tr>
            </thead>
            <tbody>
              {filtered.map((p) => (
                <ProductRow key={p.id} p={p}
                            onEdit={setEditing}
                            onToggle={toggleActive}/>
              ))}
              {filtered.length === 0 && (
                <tr><td colSpan={6} className="text-center py-10 text-brand-navy/60">No products match this filter.</td></tr>
              )}
            </tbody>
          </table>
        </div>
      )}

      {editing && <ProductEditor item={editing} onClose={() => setEditing(null)}
                                   onSaved={() => { setEditing(null); reload(); }}/>}
      {showNew && <ProductEditor item={null} onClose={() => setShowNew(false)}
                                  onSaved={() => { setShowNew(false); reload(); }}/>}
    </div>
  );
}
