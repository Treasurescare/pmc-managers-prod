import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { tenderProApi, mastersApi, publicApi, showApiError } from "@/lib/api";

/**
 * v50q — EMD / Fee Master Editor (bug-tracker "EMD Master Editor UI").
 * Lets finance/admin tune EMD & fee rules (per country, optional category,
 * slabbed percentage/fixed amounts) without touching code.
 * Backend: /api/v1/tender-pro/emd-masters (list/create/patch/delete/compute).
 */

const KINDS = ["emd", "tender_fee", "registration", "subscription",
               "premium_subscription", "transaction", "data_intel"];
const CURRENCIES = ["USD", "EUR", "GBP", "INR", "KZT", "AED"];

const EMPTY_SLAB = { tender_value_min: 0, tender_value_max: "", fee_type: "percentage",
                     fixed_amount: "", percentage: "", pct_min: "", pct_max: "" };
const EMPTY = { name: "", country: "KZ", kind: "emd", category: "", currency: "USD",
                is_active: true, notes: "", slabs: [ { ...EMPTY_SLAB } ] };

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

  const load = useCallback(async () => {
    try {
      const [m, c, cats] = await Promise.all([
        tenderProApi.listEmdMasters({}),
        publicApi.countries().catch(() => []),
        mastersApi.listCategories({ limit: 500 }).catch(() => []),
      ]);
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
      name: m.name, country: m.country, kind: m.kind,
      category: m.category || "", currency: m.currency || "USD",
      is_active: m.is_active !== false, notes: m.notes || "",
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
    if (!form.slabs.length) return toast.error("Add at least one slab.");
    for (const s of form.slabs) {
      if (s.fee_type === "fixed" && (s.fixed_amount === "" || s.fixed_amount == null))
        return toast.error("Fixed slabs need a fixed amount.");
      if (s.fee_type === "percentage" && (s.percentage === "" || s.percentage == null))
        return toast.error("Percentage slabs need a percentage.");
    }
    const payload = {
      name: form.name.trim(), country: form.country, kind: form.kind,
      category: form.category || null, currency: form.currency,
      is_active: !!form.is_active, notes: form.notes || null,
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
      toast.success(editing === "new" ? "EMD master created" : "EMD master updated");
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
      const r = await tenderProApi.computeEmdMaster(calc.master_id, Number(calc.tender_value) || 0);
      setCalcOut(r);
    } catch (e) { showApiError(e); setCalcOut(null); }
  };

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
          New EMD rule
        </button>
      </div>

      {editing && (
        <div className="bg-white border border-brand-navy/20 p-4 mb-4" data-testid="emd-form">
          <div className="grid gap-3 md:grid-cols-4">
            <label className="md:col-span-2"><span className="pmc-label">Rule name *</span>
              <input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value })}
                placeholder="e.g. KZ EMD 2% capped"
                data-testid="emd-name" className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
            <label><span className="pmc-label">Country *</span>
              <select value={form.country} onChange={(e) => setForm({ ...form, country: e.target.value })}
                data-testid="emd-country" className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                {countries.map((c) => {
                  const code = Array.isArray(c) ? c[0] : (c.code || c.iso || c.value);
                  const name = Array.isArray(c) ? c[1] : (c.name || c.label || code);
                  return <option key={code} value={code}>{name}</option>;
                })}
                {countries.length === 0 && ["KZ", "IN", "AE", "GB", "US"].map((c) => <option key={c}>{c}</option>)}
              </select></label>
            <label><span className="pmc-label">Kind</span>
              <select value={form.kind} onChange={(e) => setForm({ ...form, kind: e.target.value })}
                data-testid="emd-kind" className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                {KINDS.map((k) => <option key={k} value={k}>{k.replace(/_/g, " ")}</option>)}
              </select></label>
            <label><span className="pmc-label">Category (optional — applies to all when empty)</span>
              <select value={form.category} onChange={(e) => setForm({ ...form, category: e.target.value })}
                data-testid="emd-category" className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                <option value="">— all categories —</option>
                {categories.map((c) => <option key={c.id || c.code || c.name} value={c.name}>{c.name}</option>)}
              </select></label>
            <label><span className="pmc-label">Currency</span>
              <select value={form.currency} onChange={(e) => setForm({ ...form, currency: e.target.value })}
                data-testid="emd-currency" className="mt-1 w-full px-3 py-2 border border-brand-navy/20 bg-white">
                {CURRENCIES.map((c) => <option key={c}>{c}</option>)}
              </select></label>
            <label className="flex items-end gap-2 pb-2">
              <input type="checkbox" checked={form.is_active}
                onChange={(e) => setForm({ ...form, is_active: e.target.checked })}
                data-testid="emd-active" />
              <span className="text-sm">Active</span>
            </label>
            <label className="md:col-span-4"><span className="pmc-label">Notes</span>
              <input value={form.notes} onChange={(e) => setForm({ ...form, notes: e.target.value })}
                data-testid="emd-notes" className="mt-1 w-full px-3 py-2 border border-brand-navy/20" /></label>
          </div>

          <div className="mt-4">
            <div className="pmc-label mb-2">Slabs (tender value ranges → fee)</div>
            {form.slabs.map((s, i) => (
              <div key={i} className="grid gap-2 md:grid-cols-8 items-end mb-2 border-b border-brand-navy/10 pb-2"
                   data-testid={`emd-slab-${i}`}>
                <label><span className="text-[10px] uppercase text-slate-500">Min value</span>
                  <input type="number" value={s.tender_value_min}
                    onChange={(e) => setSlab(i, "tender_value_min", e.target.value)}
                    data-testid={`emd-slab-${i}-min`} className="mt-1 w-full px-2 py-1.5 border border-brand-navy/20 text-sm" /></label>
                <label><span className="text-[10px] uppercase text-slate-500">Max (blank = ∞)</span>
                  <input type="number" value={s.tender_value_max}
                    onChange={(e) => setSlab(i, "tender_value_max", e.target.value)}
                    data-testid={`emd-slab-${i}-max`} className="mt-1 w-full px-2 py-1.5 border border-brand-navy/20 text-sm" /></label>
                <label><span className="text-[10px] uppercase text-slate-500">Type</span>
                  <select value={s.fee_type} onChange={(e) => setSlab(i, "fee_type", e.target.value)}
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
                <label><span className="text-[10px] uppercase text-slate-500">Pct max (cap)</span>
                  <input type="number" value={s.pct_max}
                    onChange={(e) => setSlab(i, "pct_max", e.target.value)}
                    data-testid={`emd-slab-${i}-pctmax`} className="mt-1 w-full px-2 py-1.5 border border-brand-navy/20 text-sm" /></label>
                <button type="button" onClick={() => setForm((f) => ({ ...f, slabs: f.slabs.filter((_, j) => j !== i) }))}
                  data-testid={`emd-slab-${i}-remove`}
                  className="px-2 py-1.5 text-[10px] uppercase tracking-widest border border-red-300 text-red-700 hover:bg-red-50">
                  Remove
                </button>
              </div>
            ))}
            <button type="button" onClick={() => setForm((f) => ({ ...f, slabs: [...f.slabs, { ...EMPTY_SLAB }] }))}
              data-testid="emd-slab-add"
              className="px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5">
              + Add slab
            </button>
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
                  {m.name} <span className="font-normal text-brand-navy/50">· {m.kind.replace(/_/g, " ")}</span>
                </div>
                <div className="text-xs text-brand-navy/60 mt-0.5">
                  {countryName(m.country)}{m.category ? ` · ${m.category}` : " · all categories"} · {m.currency}
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
              {rows.map((m) => <option key={m.id} value={m.id}>{m.name} · {m.country}</option>)}
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
              {calcOut.slab && <span className="text-brand-navy/60"> · {slabLabel(calcOut.slab, calcOut.currency)}</span>}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
