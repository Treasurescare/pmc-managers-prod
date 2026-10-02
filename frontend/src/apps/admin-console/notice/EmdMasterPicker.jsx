import { useEffect, useState } from "react";
import { toast } from "sonner";
import { tenderProApi, showApiError } from "@/lib/api";

/**
 * v45 · Phase B — EMD picker on the Notice creation form.
 * Loads all EMD masters (optionally filtered by country) and lets the admin
 * pick one. On pick + tender_value it calls /emd-masters/compute and writes
 * the resolved amount back into the parent's emd_config.
 */
export default function EmdMasterPicker({ country, category, tenderValue, emdConfig, onPick }) {
  const [masters, setMasters]  = useState([]);
  const [pickId, setPickId]    = useState("");
  const [computed, setComputed] = useState(null);
  const [busy, setBusy]        = useState(false);
  const [autoPicked, setAutoPicked] = useState(false);

  useEffect(() => {
    let alive = true;
    // v50h — refine EMD masters by country AND category so admins can
    // maintain distinct EMD slabs per (country, category) combination.
    tenderProApi.listEmdMasters(country || undefined, "emd", category || undefined)
      .then((r) => {
        if (!alive) return;
        const rows = r || [];
        setMasters(rows);
        if (rows.length && !pickId) {
          // Prefer category-exact match, then is_default, then first row.
          const exact = category ? rows.find((m) => (m.category || "") === category) : null;
          const preferred = exact || rows.find((m) => m.is_default) || rows[0];
          setAutoPicked(true);
          compute(preferred.id, rows);
        }
      })
      .catch(() => { if (alive) setMasters([]); });
    return () => { alive = false; };
  }, [country, category]);

  const compute = async (mid, mastersOverride) => {
    setPickId(mid);
    setComputed(null);
    const pool = mastersOverride || masters;
    if (!mid || !tenderValue || tenderValue <= 0) {
      onPick?.({ fixed_amount: emdConfig?.fixed_amount || 0,
                  percentage: emdConfig?.percentage || 0,
                  currency: emdConfig?.currency || "USD",
                  emd_master_id: mid || null });
      return;
    }
    setBusy(true);
    try {
      const r = await tenderProApi.computeEmd(mid, tenderValue);
      setComputed(r);
      const master = pool.find((m) => m.id === mid);
      onPick?.({
        fixed_amount: r.type === "fixed" ? r.amount : 0,
        percentage:   r.type === "percentage" ? r.percentage : 0,
        currency:     r.currency || emdConfig?.currency || "USD",
        emd_master_id: mid,
        emd_master_name: master?.name,
        auto_computed_amount: r.amount,
      });
      if (!autoPicked) {
        toast.success(`EMD computed · ${r.amount.toLocaleString()} ${r.currency}`);
      }
    } catch (e) { showApiError(e); }
    finally { setBusy(false); }
  };

  // Recompute when tender value changes (admin edits Budget after picking master).
  useEffect(() => {
    if (pickId && tenderValue > 0) compute(pickId);
  }, [tenderValue]);

  return (
    <div className="border border-emerald-200 bg-emerald-50/60 p-3 md:col-span-2 space-y-2"
         data-testid="emd-master-picker">
      <div className="flex items-baseline justify-between">
        <div className="pmc-label text-emerald-900">
          Auto-EMD from master {autoPicked && pickId && <span className="normal-case tracking-normal text-[10px] ml-2 bg-emerald-100 px-1.5 py-0.5">Auto-picked</span>}
        </div>
        <span className="text-[11px] text-brand-navy/50">Masters → Rating & Fees tab</span>
      </div>
      <select value={pickId} onChange={(e) => compute(e.target.value)}
              disabled={busy || !masters.length}
              data-testid="emd-master-select"
              className="w-full px-3 py-2 border border-brand-navy/20 bg-white text-sm">
        <option value="">— Type amounts manually below —</option>
        {masters.map((m) => (
          <option key={m.id} value={m.id}>
            {m.name} · {m.country}{m.category ? ` · ${m.category}` : ""} · {(m.slabs || []).length} slab(s)
          </option>
        ))}
      </select>
      {!masters.length && (
        <div className="text-[11px] text-brand-navy/60">
          No EMD masters {country ? `for ${country}` : ""} yet — create one under Masters → Rating & Fees.
        </div>
      )}
      {computed && (
        <div className="text-xs text-emerald-900 border border-emerald-300 bg-white p-2"
             data-testid="emd-computed">
          <strong>{computed.amount.toLocaleString()} {computed.currency}</strong> ·
          {computed.type === "percentage"
            ? ` ${computed.percentage}% of ${(tenderValue || 0).toLocaleString()}`
            : " fixed slab"}
          {" "}(slab {computed.slab?.tender_value_min?.toLocaleString()} — {(computed.slab?.tender_value_max ?? "∞")})
        </div>
      )}
    </div>
  );
}
