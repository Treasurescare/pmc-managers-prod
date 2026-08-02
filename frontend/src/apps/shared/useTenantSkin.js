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
    const params = new URLSearchParams(window.location.search);
    const code = params.get("tenant");
    if (!code) return;
    tenantApi.publicGet(code)
      .then((t) => {
        setTenant(t);
        if (t?.branding_color) {
          document.documentElement.style.setProperty("--brand-navy", t.branding_color);
          // sessionStorage lets sub-pages keep the skin without another lookup
          try { sessionStorage.setItem("pmc.tenant", JSON.stringify(t)); } catch { /* ignore */ }
        }
      })
      .catch(() => { /* silent — fall back to default brand */ });
  }, []);

  return tenant;
}
