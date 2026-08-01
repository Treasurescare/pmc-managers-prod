import { useEffect, useState, useCallback } from "react";
import { toast } from "sonner";
import { api, formatApiError } from "@/lib/api";

function KpiTile({ label, value }) {
  return (
    <div className="border border-brand-navy/10 bg-white p-4">
      <div className="pmc-label">{label}</div>
      <div className="pmc-stat-lg mt-1 text-brand-navy">{value ?? "—"}</div>
    </div>
  );
}

export default function VendorsPanel() {
  const [vendors, setVendors] = useState([]);
  const [search, setSearch] = useState("");
  const [selected, setSelected] = useState(null);
  const [kpi, setKpi] = useState(null);
  const [loadingKpi, setLoadingKpi] = useState(false);

  const load = useCallback(() => {
    api.get("/api/v1/vendors", { params: search ? { search } : {} })
      .then((r) => setVendors(r.data || []))
      .catch((e) => toast.error(formatApiError(e)));
  }, [search]);
  useEffect(() => { load(); }, [load]);

  useEffect(() => {
    if (!selected) { setKpi(null); return; }
    setLoadingKpi(true);
    api.get(`/api/v1/vendors/${selected.vendor_ref}/kpi`)
      .then((r) => setKpi(r.data))
      .catch((e) => toast.error(formatApiError(e)))
      .finally(() => setLoadingKpi(false));
  }, [selected]);

  return (
    <div className="grid gap-6 lg:grid-cols-[5fr_7fr]" data-testid="admin-vendors-panel">
      <div>
        <input
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by name or ref…"
          data-testid="vendor-search"
          className="w-full px-4 py-2 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white text-sm mb-3"
        />
        <div className="border border-brand-navy/10 bg-white">
          {vendors.length === 0 && (
            <div className="p-6 text-brand-navy/50 text-sm">
              No approved vendors yet. Approve a registration first.
            </div>
          )}
          {vendors.map((v) => (
            <button
              key={v.id}
              type="button"
              onClick={() => setSelected(v)}
              data-testid={`vendor-row-${v.vendor_ref}`}
              className={"w-full text-left p-4 border-b border-brand-navy/10 hover:bg-brand-navy/5 " + (selected?.id === v.id ? "bg-brand-navy/5" : "")}
            >
              <div className="text-sm font-semibold text-brand-navy">{v.company_name || "(no name)"}</div>
              <div className="text-xs font-mono text-brand-navy-soft mt-1">{v.vendor_ref}</div>
              <div className="text-xs text-brand-navy/50 mt-0.5">{v.email} · {v.country}</div>
            </button>
          ))}
        </div>
      </div>

      <div>
        {!selected ? (
          <div className="border border-dashed border-brand-navy/20 bg-white p-14 text-center text-brand-navy/50">
            Select an approved vendor on the left to see their trust dashboard.
          </div>
        ) : loadingKpi || !kpi ? (
          <div className="border border-brand-navy/10 bg-white p-14 text-center text-brand-navy/50">Loading vendor KPI…</div>
        ) : (
          <div className="border border-brand-navy/10 bg-white p-6" data-testid="vendor-kpi">
            <div className="pmc-label">Approved supplier</div>
            <h3 className="font-display text-2xl text-brand-navy mt-1">{kpi.company_name || "(no name)"}</h3>
            <div className="text-sm font-mono text-brand-navy-soft mt-1">{kpi.vendor_ref}</div>
            <div className="text-xs text-brand-navy/50 mt-0.5">{kpi.email} · {kpi.country} · {kpi.primary_sector || "sector n/a"}</div>

            <div className="mt-6 grid gap-3 md:grid-cols-4">
              <KpiTile label="Days approved" value={kpi.approved_days_ago} />
              <KpiTile label="Review turnaround (h)" value={kpi.time_to_decision_hours} />
              <KpiTile label="KZ licenses" value={kpi.kz_licenses_count} />
              <KpiTile label="Categories" value={kpi.categories_count} />
            </div>

            <div className="mt-6 grid gap-4 md:grid-cols-2 text-sm">
              <div>
                <div className="pmc-label">KZ licenses held</div>
                {kpi.kz_licenses_held.length === 0
                  ? <div className="text-brand-navy/50 mt-1">None</div>
                  : (
                    <ul className="mt-1 text-brand-navy">
                      {kpi.kz_licenses_held.map((l) => <li key={l}>· {l}</li>)}
                    </ul>
                  )}
              </div>
              <div>
                <div className="pmc-label">Operating regions</div>
                {kpi.operating_regions.length === 0
                  ? <div className="text-brand-navy/50 mt-1">Not declared</div>
                  : <div className="mt-1 text-brand-navy">{kpi.operating_regions.join(", ")}</div>}
              </div>
              <div className="md:col-span-2">
                <div className="pmc-label">Business categories declared</div>
                {kpi.categories_declared.length === 0
                  ? <div className="text-brand-navy/50 mt-1">None</div>
                  : <div className="mt-1 text-brand-navy">{kpi.categories_declared.join(" · ")}</div>}
              </div>
            </div>

            <div className="mt-8 grid gap-3 md:grid-cols-3 opacity-60">
              <KpiTile label="Bids submitted" value={kpi.bids_submitted} />
              <KpiTile label="Bids won" value={kpi.bids_won} />
              <KpiTile label="Packages awarded" value={kpi.packages_awarded} />
            </div>
            <div className="text-[11px] text-brand-navy/50 mt-2 italic">{kpi.phase_2_metrics}</div>
          </div>
        )}
      </div>
    </div>
  );
}
