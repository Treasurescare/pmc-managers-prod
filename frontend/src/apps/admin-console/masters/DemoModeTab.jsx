import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, formatApiError } from "@/lib/api";

/**
 * DemoModeTab — one-click investor showcase seed / reset.
 * Seeds 3 curated notices, 3 approved vendors with KZ licenses, and 5 bids
 * spanning the full pipeline (submitted → awarded + 1 signed contract).
 * Every row is tagged is_demo:true so it can be wiped cleanly.
 */
export default function DemoModeTab() {
  const [status, setStatus] = useState(null);
  const [busy, setBusy] = useState(false);

  const refresh = useCallback(async () => {
    try { setStatus(await adminApi.demoStatus()); }
    catch (e) { toast.error(formatApiError(e)); }
  }, []);

  useEffect(() => { refresh(); }, [refresh]);

  const seed = async () => {
    if (!confirm("Seed the curated Investor Demo dataset into this tenant?\n\nRows are tagged is_demo=true and can be wiped anytime.")) return;
    setBusy(true);
    try {
      const r = await adminApi.demoSeed();
      const c = r.created || {};
      toast.success(
        `Demo ready — created ${c.notices || 0} notices, ${c.vendors || 0} vendors, ${c.bids || 0} bids, ${c.contracts || 0} contracts.`,
      );
      await refresh();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const reset = async () => {
    if (!confirm("Delete every demo-tagged row from this tenant? This cannot be undone.")) return;
    setBusy(true);
    try {
      const r = await adminApi.demoReset();
      const d = r.deleted || {};
      toast.success(
        `Demo wiped — removed ${d.notices || 0} notices, ${d.vendors || 0} vendors, ${d.bids || 0} bids, ${d.contracts || 0} contracts.`,
      );
      await refresh();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const total = status
    ? (status.notices || 0) + (status.vendors || 0) + (status.bids || 0) + (status.contracts || 0)
    : 0;

  return (
    <div data-testid="admin-demo-mode-tab" className="space-y-6">
      <div>
        <div className="pmc-label">Investor Demo Mode</div>
        <h3 className="font-display text-2xl text-brand-navy mt-1">One-click showcase dataset</h3>
        <p className="text-sm text-brand-navy/60 mt-2 max-w-2xl">
          Populates a curated slice of the platform — three real-world flavored
          notices (Astana Metro Line 2 · Data Lake · Electric Bus Fleet),
          three approved KZ vendors with licenses, and five bids covering
          every stage of the approval pipeline including a signed contract.
          Every row is tagged <code className="font-mono text-xs">is_demo:true</code> so
          it never mixes with production data.
        </p>
      </div>

      <div className="grid gap-3 md:grid-cols-4" data-testid="demo-status-tiles">
        {[
          ["Notices", status?.notices],
          ["Vendors", status?.vendors],
          ["Bids", status?.bids],
          ["Contracts", status?.contracts],
        ].map(([label, value]) => (
          <div key={label} className="border border-brand-navy/10 bg-white p-4">
            <div className="pmc-label">{label}</div>
            <div className="pmc-stat-lg mt-1 text-brand-navy">{value ?? "—"}</div>
          </div>
        ))}
      </div>

      <div className="flex gap-3 flex-wrap">
        <button type="button" onClick={seed} disabled={busy}
                data-testid="demo-seed-btn"
                className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-40">
          {busy ? "Working…" : total > 0 ? "Top up demo dataset" : "Seed investor demo"}
        </button>
        <button type="button" onClick={reset} disabled={busy || total === 0}
                data-testid="demo-reset-btn"
                className="px-6 py-3 text-[12px] font-semibold uppercase tracking-widest border border-red-400 text-red-600 hover:bg-red-50 disabled:opacity-40">
          Reset demo (delete all)
        </button>
        <button type="button" onClick={refresh} disabled={busy}
                data-testid="demo-refresh-btn"
                className="px-4 py-3 text-[12px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5 disabled:opacity-40">
          Refresh
        </button>
      </div>

      <div className="text-xs text-brand-navy/50 max-w-2xl">
        Vendor demo password: <code className="font-mono">Demo@12345</code> ·
        emails end in <code className="font-mono">.demo</code> so they never
        collide with real accounts. Safe to seed and reset repeatedly during
        an investor session.
      </div>
    </div>
  );
}
