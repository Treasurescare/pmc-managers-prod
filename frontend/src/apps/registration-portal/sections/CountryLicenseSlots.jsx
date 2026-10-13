import { useEffect, useMemo, useState } from "react";
import { mastersGeoApi } from "@/lib/api";
import { DocSlotsBlock } from "./DocSlot";

/**
 * v52cn — Dynamic country-specific license upload slots.
 *
 * Pulls the Country Licenses master for every country attached to the
 * registration (main `country` plus every structured office's
 * `country_code`) and renders a dedicated DocSlotsBlock per country.
 *
 * Slot keys use the convention `country_license_{CC}_{code}` so admins
 * can see exactly which jurisdiction each document belongs to. The
 * registration upload endpoint allows this prefix (see
 * routers/registrations.py :: upload_registration_doc).
 */
export default function CountryLicenseSlots({ reg, regId, token, ensureDraft, onDocChange }) {
  const [bundles, setBundles] = useState([]); // [{country_code, licenses:[{code,name,mandatory}]}]

  // Collect every country the vendor operates in.
  const codes = useMemo(() => {
    const set = new Set();
    if (reg?.country) set.add(String(reg.country).toUpperCase());
    for (const o of reg?.operating_regions || []) {
      if (o && typeof o === "object" && o.country_code) {
        set.add(String(o.country_code).toUpperCase());
      }
    }
    return Array.from(set).sort();
  }, [reg?.country, reg?.operating_regions]);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      const results = [];
      for (const cc of codes) {
        try {
          const r = await mastersGeoApi.getCountryLicenses(cc);
          const list = Array.isArray(r?.licenses) ? r.licenses : [];
          if (list.length) results.push({ country_code: cc, licenses: list });
        } catch { /* skip countries without entries */ }
      }
      if (!cancelled) setBundles(results);
    })();
    return () => { cancelled = true; };
  }, [codes.join(",")]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!bundles.length) {
    if (!codes.length) return null;
    return (
      <div className="mt-6 border border-dashed border-brand-navy/20 bg-brand-pale/30 p-3 text-xs text-brand-navy/60"
           data-testid="country-licenses-empty">
        No country-specific licenses configured for{" "}
        <span className="font-mono">{codes.join(", ")}</span> yet. Ask the admin to
        set them in Masters → Country Licenses.
      </div>
    );
  }

  return (
    <div className="mt-6 space-y-6" data-testid="country-licenses-block">
      {bundles.map((b) => {
        const slots = b.licenses.map((lic) => [
          `country_license_${b.country_code}_${lic.code}`,
          { label: `${b.country_code} · ${lic.name}`, required: !!lic.mandatory },
        ]);
        return (
          <DocSlotsBlock
            key={b.country_code}
            title={`Country licenses — ${b.country_code}`}
            regId={regId} token={token} ensureDraft={ensureDraft}
            slots={slots}
            existing={reg.document_slots || {}}
            onChange={onDocChange} />
        );
      })}
    </div>
  );
}
