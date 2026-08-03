import { useEffect, useState } from "react";
import { tenantApi } from "@/lib/api";

/**
 * useTenantSkin — reads `?tenant=CODE` from the URL and applies the tenant's
 * primary branding color to `--brand-navy` on document.documentElement.
 * Returns the tenant object so callers can render the tenant name too.
 *
 * If no tenant param is present, does nothing (default PMC brand wins).
 */
export default function useTenantSkin() {
  const [tenant, setTenant] = useState(null);

  useEffect(() => {
    // Mount-only: reads URL param + sessionStorage once, then hits API.
    // Adding all internal locals to deps would cause infinite re-runs.
    const params = new URLSearchParams(window.location.search);
    const urlCode = params.get("tenant");
    let cached = null;
    try {
      const raw = sessionStorage.getItem("pmc.tenant");
      if (raw) cached = JSON.parse(raw);
    } catch { /* ignore parse errors on stale cache */ }
    const code = urlCode || cached?.code;
    if (!code) return;

    if (cached && cached.code === code) {
      setTenant(cached);
      if (cached.branding_color) {
        document.documentElement.style.setProperty("--brand-navy", cached.branding_color);
      }
    }

    tenantApi.publicGet(code)
      .then((t) => {
        setTenant(t);
        if (t?.branding_color) {
          document.documentElement.style.setProperty("--brand-navy", t.branding_color);
          try { sessionStorage.setItem("pmc.tenant", JSON.stringify(t)); } catch { /* quota exceeded */ }
        }
      })
      .catch(() => { /* silent — fall back to default brand */ });
  }, []);

  return tenant;
}
