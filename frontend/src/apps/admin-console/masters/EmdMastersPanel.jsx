import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { tenderProApi, mastersApi, publicApi, feeTypesApi, pricingApi, showApiError } from "@/lib/api";
import { CategoryPicker, CheckPicker } from "./CategoryPicker";

/**
 * v50q — EMD / Fee Master Editor (bug-tracker "EMD Master Editor UI").
 * Lets finance/admin tune EMD & fee rules (per country, optional category,
 * slabbed percentage/fixed amounts) without touching code.
 * Backend: /api/v1/tender-pro/emd-masters (list/create/patch/delete/compute).
 */

const CURRENCIES = ["USD", "EUR", "GBP", "INR", "KZT", "AED"];
const TIMING = { upfront: "paid at the beginning", on_completion: "paid at the end" };

const EMPTY_SLAB = { tender_value_min: 0, tender_value_max: "", fee_type: "percentage",
                     fixed_amount: "", percentage: "", pct_min: "", pct_max: "" };
const EMPTY = { name: "", country_mode: "all", countries: [], bands: [], tier: "", nil_below: "", kind: "", categories: [], currency: "USD",
    is_active: true, notes: "", progressive: false, slabs: [ { ...EMPTY_SLAB } ] };

function slabLabel(s, currency) {
  const lo = Number(s.tender_value_min || 0).toLocaleString();
  const hi = s.tender_value_max == null || s.tender_value_max === "" ? "∞"
           : Number(s.tender_value_max).toLocaleString();
  const fee = s.fee_type === "fixed"
    ? `${currency} ${Number(s.fixed_amount || 0).toLocaleString()}`
    : `${s.percentage ?? 0}%${s.pct_min ? ` (min ${Number(s.pct_min).toLocaleString()})` : ""}${s.pct_max ? ` (max ${Number(s.pct_max).toLocaleString()})` : ""}`;
  return `${lo} – ${hi} → ${fee}`;
}

export default function EmdMastersPanel() {
  const [rows, setRows] = useState([]);
  const [countries, setCountries] = useState([]);
  const [categories, setCategories] = useState([]);
  const [editing, setEditing] = useState(null); // null | "new" | master id
  const [form, setForm] = useState(EMPTY);
  const [busy, setBusy] = useState(false);
  const [calc, setCalc] = useState({ master_id: "", tender_value: 100000 });
  const [calcOut, setCalcOut] = useState(null);
  const [feeTypes, setFeeTypes] = useState([]);
  const [pricing, setPricing] = useState({ bands: [], tiers: [] });
  const ft = feeTypes.find((t) => t.code === form.kind);
  const ftName = (code) => feeTypes.find((t) => t.code === code)?.name || (code || "").replace(/_/g, " ");
  const pickType = (code) => {
    const t = feeTypes.find((x) => x.code === code);
    const fee_type = t?.calc === "percentage" ? "percentage" : "fixed";
    const sel = t?.country_scope === "selected";
    setForm((f) => ({ ...f, kind: code,
      country_mode: sel ? "some" : "all", countries: sel ? [...(t.countries || [])] : [],
      categories: t?.category_scope === "selected" ? [...(t.categories || [])] : [],
      slabs: t?.amount_mode === "single" ? [{ ...EMPTY_SLAB, fee_type }] : f.slabs.map((s) => ({ ...s, fee_type: t?.calc === "either" ? s.fee_type : fee_type })) }));
  };

  const load = useCallback(async () => {
    try {
      const [m, c, cats, fts, pb] = await Promise.all([
        tenderProApi.listEmdMasters({}),
        publicApi.countries().catch(() => []),
        mastersApi.listCategories({ limit: 500 }).catch(() => []),
        feeTypesApi.list().catch(() => []),
        pricingApi.bands().catch(() => ({ bands: [], tiers: [] })),
      ]);
      setPricing(pb);
      setFeeTypes(fts.filter((t) => t.is_active !== false));
      setRows(Array.isArray(m) ? m : (m.items || []));
      const cl = Array.isArray(c) ? c : (c?.countries || []);
      setCountries(cl);
      setCategories(Array.isArray(cats) ? cats : (cats.items || []));
    } catch (e) { showApiError(e); }
  }, []);
  useEffect(() => { load(); }, [load]);

  const openNew = () => { setForm(EMPTY); setEditing("new"); };
  const openEdit = (m) => {
    setForm({
      name: m.name, kind: m.kind,
      countries: m.countries?.length ? m.countries : (m.country && !["ALL", "MULTI"].includes(m.country) ? [m.country] : []),
      country_mode: m.bands?.length ? "band" : (m.countries?.length || (m.country && !["ALL", "BAND"].includes(m.country)) || feeTypes.find((t) => t.code === m.kind)?.country_scope === "selected") ? "some" : "all",
      bands: m.bands || [], tier: m.tier || "", nil_below: m.nil_below ?? "",
      categories: m.categories?.length ? m.categories : (m.category ? [m.category] : []), currency: m.currency || "USD",
      is_active: m.is_active !== false, notes: m.notes || "", progressive: !!m.progressive,
      slabs: (m.slabs?.length ? m.slabs : [EMPTY_SLAB]).map((s) => ({
        tender_value_min: s.tender_value_min ?? 0,
        tender_value_max: s.tender_value_max ?? "",
        fee_type: s.fee_type || "percentage",
        fixed_amount: s.fixed_amount ?? "",
        percentage: s.percentage ?? "",
        pct_min: s.pct_min ?? "",
        pct_max: s.pct_max ?? "",
      })),
    });
    setEditing(m.id);
  };

  const setSlab = (i, k, v) => setForm((f) => {
    const slabs = f.slabs.slice();
    slabs[i] = { ...slabs[i], [k]: v };
    return { ...f, slabs };
  });

  const save = async () => {
    if (!form.name.trim()) return toast.error("Name is required.");
    if (!ft) return toast.error("Pick a fee type.");
    if (ft.category_scope === "selected" && !form.categories.length) return toast.error("Tick at least one category.");
    if (form.country_mode === "some" && !form.countries.length) return toast.error("Tick at least one country.");
    if (form.country_mode === "band" && !form.bands.length) return toast.error("Tick at least one pricing band.");
    if (!form.slabs.length) return toast.error("Add at least one slab.");
    for (const s of form.slabs) {
      if (s.fee_type === "fixed" && (s.fixed_amount === "" || s.fixed_amount == null))
        return toast.error("Fixed slabs need a fixed amount.");
      if (s.fee_type === "percentage" && (s.percentage === "" || s.percentage == null))
        return toast.error("Percentage slabs need a percentage.");
    }
    const payload = {
      name: form.name.trim(), kind: form.kind, extend_type: true,
      country: form.country_mode === "some" ? (form.countries[0] || "ALL") : "ALL",
      countries: form.country_mode === "some" ? form.countries : [],
      bands: form.country_mode === "band" ? form.bands : [],
      tier: form.tier || null, nil_below: form.nil_below === "" ? null : Number(form.nil_below),
      categories: ft.category_scope === "selected" ? form.categories : [], currency: form.currency,
      is_active: !!form.is_active, notes: form.notes || null, progressive: !!form.progressive,
      slabs: form.slabs.map((s) => ({
        tender_value_min: Number(s.tender_value_min) || 0,
        tender_value_max: s.tender_value_max === "" ? null : Number(s.tender_value_max),
        fee_type: s.fee_type,
        fixed_amount: s.fee_type === "fixed" ? Number(s.fixed_amount) : null,
        percentage: s.fee_type === "percentage" ? Number(s.percentage) : null,
        pct_min: s.pct_min === "" ? null : Number(s.pct_min),
        pct_max: s.pct_max === "" ? null : Number(s.pct_max),
      })),
    };
    setBusy(true);
    try {
      if (editing === "new") await tenderProApi.createEmdMaster(payload);
      else await tenderProApi.updateEmdMaster(editing, payload);
      const added = newCountries.length + newCats.length;
      toast.success((editing === "new" ? "Fee rule created" : "Fee rule saved") + (added ? ` · ${added} added to fee type "${ft.name}"` : ""));
      setEditing(null);
      load();
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  const remove = async (m) => {
    if (!window.confirm(`Delete EMD master "${m.name}"?`)) return;
    try {
      await tenderProApi.deleteEmdMaster(m.id);
      toast.success("Deleted");
      load();
    } catch (e) { showApiError(e); }
  };

  const runCalc = async () => {
    if (!calc.master_id) return toast.error("Pick a master first.");
    try {
      const r = await tenderProApi.computeEmd(calc.master_id, Number(calc.tender_value) || 0);
      setCalcOut(r);
    } catch (e) { showApiError(e); setCalcOut(null); }
  };

  const countryItems = countries.map((c) => {
    const code = Array.isArray(c) ? c[0] : (c.code || c.iso || c.value);
    return { value: String(code).toUpperCase(), name: Array.isArray(c) ? c[1] : (c.name || c.label || code) };
  });
  const newCountries = ft?.country_scope === "selected" && form.country_mode === "some"
    ? form.countries.filter((c) => !(ft.countries || []).map((x) => x.toUpperCase()).includes(c)) : [];
  const newCats = ft?.category_scope === "selected" && (ft.categories || []).length
    ? form.categories.filter((c) => !(ft.categories || []).includes(c)) : [];
  const countryName = (code) => {
    const c = countries.find((x) => {
      const cc = Array.isArray(x) ? x[0] : (x.code || x.iso || x.value);
      return String(cc).toUpperCase() === String(code).toUpperCase();
    });
    return c ? (Array.isArray(c) ? c[1] : (c.name || c.label || code)) : code;
  };

  return (
    <div data-testid="emd-masters-panel">
      <div className="flex items-center justify-between mb-3 flex-wrap gap-2">
        <div className="text-sm text-brand-navy/60">
          {rows.length} rule{rows.length === 1 ? "" : "s"} on file. Category-scoped rules win over
          country-wide rules in the notice builder.
        </div>
        <button onClick={openNew} data-testid="emd-new-btn"
          className="px-4 py-2 text-[10px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          New fee rule
        </button>
      </div>

      {editing && (
        <div className="bg-white border border-brand-navy/20 p-4 mb-4" data-testid="emd-form">
          <div className="grid gap-3 md:grid-cols-4">
            <label className="md:col-span-2"><span className="pmc-label">Rule name *</span>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. KZ EMD 2% capped"
                data-testid="emd-name" className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label className="md:col-span-2"><span className="pmc-label">Fee type *</span>
              <select value={form.kind} onChange={(e) => pickType(e.target.value)}
                data-testid="emd-kind" className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                <option value="">— pick a fee type —</option>
                {feeTypes.map((t) => <option key={t.code} value={t.code}>{t.name}</option>)}
              </select></label>
            {ft && (
              <div className="md:col-span-4 text-xs bg-brand-pale/50 border border-brand-navy/10 px-3 py-2" data-testid="emd-type-summary">
                <b>{ft.name}</b>: {TIMING[ft.timing]} · {ft.calc === "either" ? "fixed or %" : ft.calc} · {ft.amount_mode === "single" ? "one amount" : "range by tender value"} · {ft.category_scope === "all" ? "all categories" : "selected categories"} · {ft.billing === "yearly" ? "yearly" : "one-time"}{ft.used_in_tender_builder ? " · charged in vendor Tender Builder" : ""}
              </div>
            )}
            <div className="md:col-span-2" data-testid="emd-countries"><span className="pmc-label">Countries *</span>
              {ft?.country_scope !== "selected" && (
                <div className="flex gap-4 text-sm mt-1 mb-1">
                  <label className="flex items-center gap-2"><input type="radio" checked={form.country_mode === "all"} onChange={() => setForm({ ...form, country_mode: "all", countries: [] })} data-testid="emd-country-mode-all" /> All countries</label>
                  <label className="flex items-center gap-2"><input type="radio" checked={form.country_mode === "band"} onChange={() => setForm({ ...form, country_mode: "band", countries: [] })} data-testid="emd-country-mode-band" /> Pricing bands</label>
                  <label className="flex items-center gap-2"><input type="radio" checked={form.country_mode === "some"} onChange={() => setForm({ ...form, country_mode: "some", bands: [] })} data-testid="emd-country-mode-some" /> Specific countries</label>
                </div>
              )}
              {form.country_mode === "band" && (
                <div className="mt-1 flex flex-wrap gap-3 text-sm" data-testid="emd-band-picker">
                  {pricing.bands.filter((b) => b.is_active).map((b) => (
                    <label key={b.code} className="flex items-center gap-1"><input type="checkbox" checked={form.bands.includes(b.code)} data-testid={`emd-band-${b.code}`}
                      onChange={(e) => setForm({ ...form, bands: e.target.checked ? [...form.bands, b.code] : form.bands.filter((x) => x !== b.code) })} />{b.name}</label>))}
                </div>
              )}
              {form.country_mode === "some" && (
                <div className="mt-1"><CheckPicker items={countryItems} value={form.countries} extra={newCountries}
                  onChange={(v) => setForm({ ...form, countries: v })} prefix="emd-country" placeholder="Search countries…" /></div>
              )}
              {ft?.country_scope === "selected" && <div className="text-xs text-brand-navy/60 mt-1">Pre-filled from the fee type. Untick to narrow; tick others to add them.</div>}
            </div>
            <div className="md:col-span-2"><span className="pmc-label">Categories</span>
              {ft?.category_scope === "selected"
                ? <div className="mt-1"><CategoryPicker categories={categories} value={form.categories} extra={newCats} onChange={(v) => setForm({ ...form, categories: v })} />
                    <div className="text-xs text-brand-navy/60 mt-1">Pre-filled from the fee type. Untick to narrow; tick others to add them.</div></div>
                : <div className="mt-1 text-sm text-brand-navy/60" data-testid="emd-category-all">Applies to all categories (set by the fee type)</div>}
            </div>
            {(newCountries.length + newCats.length) > 0 && (
              <div className="md:col-span-4 text-xs bg-amber-50 border border-amber-300 text-amber-900 px-3 py-2" data-testid="emd-extend-note">
                Saving will also add {[...newCountries.map(countryName), ...newCats].join(", ")} to the fee type “{ft.name}”.
              </div>
            )}
            <label><span className="pmc-label">Currency</span>
              <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}
                data-testid="emd-currency" className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
              </select></label>
            <label><span className="pmc-label">Buyer tier</span>
              <select value={form.tier} onChange={(e) => setForm({ ...form, tier: e.target.value })}
                data-testid="emd-tier" className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                <option value="">All tiers</option>
                {pricing.tiers.map((t) => <option key={t}>{t}</option>)}
              </select></label>
            <label><span className="pmc-label">No fee below value</span>
              <input type="number" value={form.nil_below} onChange={(e) => setForm({ ...form, nil_below: e.target.value })}
                placeholder="e.g. 25000" data-testid="emd-nil-below" className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label className="flex items-end gap-2 pb-2">
              <input type="checkbox" checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                data-testid="emd-active" />
              <span className="text-sm">Active</span>
            </label>
            <label className="flex items-end gap-2 pb-2 md:col-span-2">
              <input type="checkbox" checked={!!form.progressive}
                onChange={(e) => setForm({ ...form, progressive: e.target.checked })}
                data-testid="emd-progressive" />
              <span className="text-sm">Stepped: each % applies only to the part of the value inside its range</span>
            </label>
            <label className="md:col-span-4"><span className="pmc-label">Notes</span>
              <input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
                data-testid="emd-notes" className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
          </div>

          <div className="mt-4">
            <div className="pmc-label mb-2">{ft?.amount_mode === "single" ? "Amount" : "Ranges (tender value → fee)"}</div>
            {form.slabs.map((s, i) => (
              <div key={i} className="grid gap-2 md:grid-cols-8 items-end mb-2 border-b border-brand-navy/10 pb-2"
                   data-testid={`emd-slab-${i}`}>
                {ft?.amount_mode !== "single" && <>
                <label><span className="text-[10px] uppercase text-slate-500">Min value</span>
                  <input type="number" value={s.tender_value_min}
                    onChange={(e) => setSlab(i, "tender_value_min", e.target.value)}
                    data-testid={`emd-slab-${i}-min`} className="mt-1 w-full px-2 py-1.5 border border-brand-navy/20 text-sm" /></label>
                <label><span className="text-[10px] uppercase text-slate-500">Max (blank = ∞)</span>
                  <input type="number" value={s.tender_value_max}
                    onChange={(e) => setSlab(i, "tender_value_max", e.target.value)}
                    data-testid={`emd-slab-${i}-max`} className="mt-1 w-full px-2 py-1.5 border border-brand-navy/20 text-sm" /></label>
                </>}
                <label><span className="text-[10px] uppercase text-slate-500">Type</span>
                  <select value={s.fee_type} onChange={(e) => setSlab(i, "fee_type", e.target.value)} disabled={ft && ft.calc !== "either"}
                    data-testid={`emd-slab-${i}-type`} className="mt-1 w-full px-2 py-1.5 border border-brand-navy/20 bg-white text-sm">
                    <option value="percentage">%</option><option value="fixed">Fixed</option>
                  </select></label>
                {s.fee_type === "fixed" ? (
                  <label className="md:col-span-2"><span className="text-[10px] uppercase text-slate-500">Fixed amount</span>
                    <input type="number" value={s.fixed_amount}
                      onChange={(e) => setSlab(i, "fixed_amount", e.target.value)}
                      data-testid={`emd-slab-${i}-fixed`} className="mt-1 w-full px-2 py-1.5 border border-brand-navy/20 text-sm" /></label>
                ) : (
                  <>
                    <label><span className="text-[10px] uppercase text-slate-500">%</span>
                      <input type="number" step="0.01" value={s.percentage}
                        onChange={(e) => setSlab(i, "percentage", e.target.value)}
                        data-testid={`emd-slab-${i}-pct`} className="mt-1 w-full px-2 py-1.5 border border-brand-navy/20 text-sm" /></label>
                    <label><span className="text-[10px] uppercase text-slate-500">Pct min</span>
                      <input type="number" value={s.pct_min}
                        onChange={(e) => setSlab(i, "pct_min", e.target.value)}
                        data-testid={`emd-slab-${i}-pctmin`} className="mt-1 w-full px-2 py-1.5 border border-brand-navy/20 text-sm" /></label>
                  </>
                )}
                {s.fee_type !== "fixed" && <label><span className="text-[10px] uppercase text-slate-500">Pct max (cap)</span>
                  <input type="number" value={s.pct_max}
                    onChange={(e) => setSlab(i, "pct_max", e.target.value)}
                    data-testid={`emd-slab-${i}-pctmax`} className="mt-1 w-full px-2 py-1.5 border border-brand-navy/20 text-sm" /></label>}
                <button type="button" onClick={() => setForm((f) => ({ ...f, slabs: f.slabs.filter((_, j) => j !== i) }))}
                  data-testid={`emd-slab-${i}-remove`}
                  className="px-2 py-1.5 text-[10px] uppercase tracking-widest border border-red-300 text-red-700 hover:bg-red-50">
                  Remove
                </button>
              </div>
            ))}
            {ft?.amount_mode !== "single" && <button type="button" onClick={() => setForm((f) => ({ ...f, slabs: [...f.slabs, { ...EMPTY_SLAB, fee_type: ft?.calc === "percentage" ? "percentage" : "fixed" }] }))}
              data-testid="emd-slab-add"
              className="px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
              + Add range
            </button>}
          </div>

          <div className="mt-4 flex justify-end gap-2">
            <button onClick={() => setEditing(null)} data-testid="emd-cancel"
              className="px-4 py-2 text-[10px] uppercase tracking-widest border border-brand-navy/30">Cancel</button>
            <button onClick={save} disabled={busy} data-testid="emd-save"
              className="px-4 py-2 text-[10px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
              {busy ? "Saving…" : editing === "new" ? "Create rule" : "Save changes"}
            </button>
          </div>
        </div>
      )}

      {rows.length === 0 ? (
        <div className="p-6 text-sm text-brand-navy/50 bg-white border border-brand-navy/10"
             data-testid="emd-empty">No EMD rules yet. Create the first one.</div>
      ) : (
        <div className="bg-white border border-brand-navy/10 divide-y divide-brand-navy/10"
             data-testid="emd-list">
          {rows.map((m) => (
            <div key={m.id} className="p-4 flex items-start justify-between gap-3 flex-wrap"
                 data-testid={`emd-row-${m.id}`}>
              <div className="min-w-0">
                <div className="text-sm font-semibold text-brand-navy">
                  {m.name} <span className="font-normal text-brand-navy/50">· {ftName(m.kind)}</span>
                </div>
                <div className="text-xs text-brand-navy/60 mt-0.5">
                  {m.bands?.length ? `Bands: ${m.bands.map((c) => pricing.bands.find((b) => b.code === c)?.name || c).join(", ")}` : m.countries?.length ? m.countries.map(countryName).join(", ") : countryName(m.country === "ALL" ? "All countries" : m.country)}{m.tier ? ` · ${m.tier} tier` : ""}{m.nil_below ? ` · nil below ${Number(m.nil_below).toLocaleString()}` : ""}{m.categories?.length ? ` · ${m.categories.join(", ")}` : m.category ? ` · ${m.category}` : " · all categories"} · {m.currency}
                  {!m.is_active && <span className="ml-2 text-red-700 font-semibold">INACTIVE</span>}
                </div>
                <div className="text-xs text-brand-navy/70 mt-1 font-mono">
                  {(m.slabs || []).map((s) => slabLabel(s, m.currency)).join("  |  ") || "no slabs"}
                </div>
              </div>
              <div className="flex gap-2 shrink-0">
                <button onClick={() => openEdit(m)} data-testid={`emd-edit-${m.id}`}
                  className="px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">Edit</button>
                <button onClick={() => remove(m)} data-testid={`emd-delete-${m.id}`}
                  className="px-3 py-1.5 text-[10px] uppercase tracking-widest border border-red-300 text-red-700 hover:bg-red-50">Delete</button>
              </div>
            </div>
          ))}
        </div>
      )}

      <div className="mt-5 bg-white border border-brand-navy/10 p-4" data-testid="emd-calc">
        <div className="pmc-label mb-2">Quick calculator</div>
        <div className="flex flex-wrap items-end gap-2">
          <label className="flex-1 min-w-[220px]"><span className="text-[10px] uppercase text-slate-500">Rule</span>
            <select value={calc.master_id} onChange={(e) => setCalc({ ...calc, master_id: e.target.value })}
              data-testid="emd-calc-master" className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white text-sm">
              <option value="">— pick a rule —</option>
              {rows.map((m) => <option key={m.id} value={m.id}>{m.name} · {m.countries?.length ? m.countries.join(", ") : m.country}</option>)}
            </select></label>
          <label><span className="text-[10px] uppercase text-slate-500">Tender value</span>
            <input type="number" value={calc.tender_value}
              onChange={(e) => setCalc({ ...calc, tender_value: e.target.value })}
              data-testid="emd-calc-value" className="mt-1 w-40 px-3 py-2 border border-brand-navy/20 text-sm" /></label>
          <button onClick={runCalc} data-testid="emd-calc-run"
            className="px-4 py-2 text-[10px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            Compute
          </button>
          {calcOut && (
            <div className="w-full mt-2 text-sm" data-testid="emd-calc-result">
              Fee: <b className="font-mono">{calcOut.currency} {Number(calcOut.amount).toLocaleString()}</b>
              {calcOut.type === "stepped" && <span className="text-brand-navy/60"> · stepped across value bands</span>}
              {calcOut.slab && <span className="text-brand-navy/60"> · {slabLabel(calcOut.slab, calcOut.currency)}</span>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
