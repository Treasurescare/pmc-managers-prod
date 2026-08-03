import { useEffect, useState } from "react";
import { tenantApi } from "@/lib/api";

/**
 * useTenantSkin — resolves the active tenant in **three** priority steps:
 *   1) CNAME subdomain (e.g. `acme.pmcmanagers.com` → tenant.subdomain = "acme")
 *      OR full-host alias (e.g. `tenders.acme.com` → tenant.host_alias)
 *      → hits `/api/v1/tenants/by-host?host=…`
 *   2) `?tenant=CODE` query-string fallback (legacy path, still supported).
 *   3) `sessionStorage` cache to survive client-side route changes.
 *
 * The resolved branding_color is written to `--brand-navy` so the whole
 * design system reskins in one line. Returns the tenant object.
 */
export default function useTenantSkin() {
  const [tenant, setTenant] = useState(null);

  useEffect(() => {
    // Mount-only. Adding internal locals to deps would cause infinite re-runs.
    const host = typeof window !== "undefined" ? window.location.host : "";
    const params = new URLSearchParams(window.location.search);
    const urlCode = params.get("tenant");
    let cached = null;
    try {
      const raw = sessionStorage.getItem("pmc.tenant");
      if (raw) cached = JSON.parse(raw);
    } catch { /* ignore parse errors on stale cache */ }

    // Instant paint from cache — matches either code OR host so subdomain
    // navigations feel zero-flash.
    if (cached && (cached.code === urlCode || cached._host === host)) {
      setTenant(cached);
      if (cached.branding_color) {
        document.documentElement.style.setProperty("--brand-navy", cached.branding_color);
      }
    }

    const applyTenant = (t) => {
      const merged = { ...t, _host: host };
      setTenant(merged);
      if (t?.branding_color) {
        document.documentElement.style.setProperty("--brand-navy", t.branding_color);
      }
      try { sessionStorage.setItem("pmc.tenant", JSON.stringify(merged)); } catch { /* quota */ }
    };

    // Step 1 — host-based lookup (CNAME / host_alias).
    tenantApi.publicByHost(host)
      .then(applyTenant)
      .catch(() => {
        // Step 2 — fallback to ?tenant=CODE
        if (urlCode) {
          tenantApi.publicGet(urlCode).then(applyTenant).catch(() => {
            /* default PMC brand wins */
          });
        }
      });
  }, []);

  return tenant;
}
