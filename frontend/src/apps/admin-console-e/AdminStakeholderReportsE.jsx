import { useCallback, useEffect, useState } from "react";
import { stakeholderReportsApi, showApiError, downloadAuthedFile } from "@/lib/api";
import AdminEShell from "./AdminEShell";

/**
 * v50m — Stakeholder Reports (bug #45).
 * Pulls the four live reports exposed by routers/stakeholder_reports.py and
 * renders summary cards + a download-CSV link for each. Replaces the missing
 * "Save snapshot" tab that was emitting a JSON parse error because the admin
 * UI did not actually exist.
 */
const TABS = [
  ["tenders", "Tender pipeline", "Pipeline snapshot per notice — bids, EMDs, corrigenda."],
  ["awards",  "Awards",          "Awarded bids with PO/contract value and days-since-award."],
  ["escrow",  "Escrow & EMD",    "Joint accounts + aging transactions, SLA breach flag."],
  ["sla",     "SLA / Contracts", "Active contracts with milestone hit-rate and variations."],
];

function KpiCards({ kind, data }) {
  if (!data) return null;
  if (kind === "tenders") {
    const total = data.count;
    const published = (data.items || []).filter((r) => r.status === "PUBLISHED").length;
    const draft = total - published;
    const openCorr = (data.items || []).reduce((s, r) => s + (r.active_corrigenda || 0), 0);
    return <KpiRow kv={{ "Tenders tracked": total, "Published": published, "Draft": draft, "Active corrigenda": openCorr }} />;
  }
  if (kind === "awards") {
    return <KpiRow kv={{ "Awards": data.count, "Awards this week": (data.items||[]).filter((r) => (r.days_since_award ?? 999) < 7).length }} />;
  }
  if (kind === "escrow") {
    return <KpiRow kv={{ "Accounts": (data.accounts || []).length, "Transactions": (data.transactions || []).length, "SLA breaches": data.sla_breaches, "SLA threshold (days)": data.sla_threshold_days }} />;
  }
  if (kind === "sla") {
    const avg = (data.items || []).reduce((s, r) => s + (r.milestone_hit_rate_pct || 0), 0) / Math.max(1, (data.items || []).length);
    return <KpiRow kv={{ "Contracts": data.count, "Avg milestone hit-rate": `${avg.toFixed(1)}%` }} />;
  }
  return null;
}

function KpiRow({ kv }) {
  return (
    <div className="grid grid-cols-2 md:grid-cols-4 gap-3 mb-4">
      {Object.entries(kv).map(([k, v]) => (
        <div key={k} className="bg-white border border-brand-navy/10 p-3"
             data-testid={`sr-kpi-${k.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`}>
          <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">{k}</div>
          <div className="text-2xl font-serif mt-1">{v}</div>
        </div>
      ))}
    </div>
  );
}

function Table({ kind, data }) {
  if (!data) return null;
  const rows = kind === "escrow"
    ? (data.transactions || data.accounts || [])
    : (data.items || []);
  if (rows.length === 0) {
    return <div className="p-8 text-sm text-brand-navy/50 bg-white border border-brand-navy/10 text-center"
                data-testid={`sr-empty-${kind}`}>No data yet.</div>;
  }
  const cols = Object.keys(rows[0]);
  return (
    <div className="bg-white border border-brand-navy/10 overflow-x-auto">
      <table className="min-w-full text-xs" data-testid={`sr-table-${kind}`}>
        <thead>
          <tr className="bg-brand-pale text-brand-navy/70 uppercase tracking-widest">
            {cols.map((c) => <th key={c} className="text-left p-2 whitespace-nowrap">{c.replace(/_/g, " ")}</th>)}
          </tr>
        </thead>
        <tbody>
          {rows.map((r, i) => (
            <tr key={i} className="border-t border-brand-navy/5">
              {cols.map((c) => (
                <td key={c} className="p-2 whitespace-nowrap text-brand-navy/80">
                  {typeof r[c] === "boolean" ? (r[c] ? "✓" : "—") : String(r[c] ?? "—")}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function AdminStakeholderReportsE() {
  const [tab, setTab] = useState("tenders");
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await stakeholderReportsApi[tab]();
      setData(res);
    } catch (e) {
      showApiError(e, { fallbackTitle: "Could not load report" });
      setData(null);
    }
    finally { setLoading(false); }
  }, [tab]);
  useEffect(() => { load(); }, [load]);

  const meta = TABS.find((t) => t[0] === tab);

  return (
    <AdminEShell active="Stakeholder reports"
                 crumb={<>Events / <b>Stakeholder reports</b></>}>
      <div className="p-6" data-testid="admin-stakeholder-reports-e">
        <h1 className="text-2xl font-serif mb-1">Stakeholder reports</h1>
        <div className="text-sm text-brand-navy/60 mb-4">
          Live reports fed by the production collections. Each tab has a one-click CSV export.
        </div>

        <div className="flex gap-2 mb-4 border-b border-brand-navy/10 overflow-x-auto">
          {TABS.map(([k, l]) => (
            <button key={k} onClick={() => setTab(k)}
                    data-testid={`sr-tab-${k}`}
                    className={`px-4 py-2 text-xs uppercase tracking-widest whitespace-nowrap ${
                      tab === k ? "border-b-2 border-brand-navy font-semibold text-brand-navy"
                                : "text-slate-500 hover:text-brand-navy"}`}>
              {l}
            </button>
          ))}
        </div>

        <div className="flex justify-between items-start mb-4 flex-wrap gap-2">
          <div className="text-sm text-brand-navy/70">{meta?.[2]}</div>
          {/* v52br — authenticated blob download; a raw <a href> drops the
              Bearer token and the new tab shows {"detail":"Not authenticated"} */}
          <button type="button"
             onClick={async () => {
               try { await downloadAuthedFile(stakeholderReportsApi.csvUrl(tab), `stakeholder-${tab}.csv`); }
               catch (e) { showApiError(e, { fallbackTitle: "CSV download failed" }); }
             }}
             data-testid={`sr-csv-${tab}`}
             className="px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
            Download CSV
          </button>
        </div>

        {loading && <div className="p-6 text-sm text-brand-navy/50" data-testid="sr-loading">Loading…</div>}
        {!loading && (
          <>
            <KpiCards kind={tab} data={data} />
            <Table kind={tab} data={data} />
            {data?.generated_at && (
              <div className="mt-3 text-[11px] text-brand-navy/50 font-mono"
                   data-testid="sr-generated-at">
                Generated at {data.generated_at}
              </div>
            )}
          </>
        )}
      </div>
    </AdminEShell>
  );
}
