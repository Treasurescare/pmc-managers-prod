import { useEffect, useMemo, useState } from "react";
import { Field, Input } from "./FormPrimitives";
import { DocSlotsBlock } from "./DocSlot";
import { useI18n } from "@/context/I18nContext";
import { api, publicApi } from "@/lib/api";
import RegionOfficeEditor from "./RegionOfficeEditor";
import CountryLicenseSlots from "./CountryLicenseSlots";
import UnspscMultiPicker from "@/components/UnspscMultiPicker";

/**
 * Section D — Compliance.
 *
 * v52co changes:
 *  - Business categories picker is now a UNSPSC multi-select hitting the
 *    full 158k codeset (matches Section C) instead of the curated ~90-row
 *    `/categories/public` list. Vendors from any country can now actually
 *    find biogas / solar / construction / etc.
 *  - Legacy "Kazakhstan Licenses Held" checklist is now gated on KZ being
 *    the main country OR appearing in operating regions. Bangladesh /
 *    Bosnia / etc vendors no longer see it.
 *  - Country-specific license uploads (CountryLicenseSlots) stay for the
 *    actual country the vendor registered under + every office country.
 */
export default function SectionD({ reg, update, kzMeta, regId, token, onDocChange, ensureDraft }) {
  const { t } = useI18n();
  const slots = [
    ["signed_declaration", { label: t("section_d.doc_signed_declaration"), required: false }],
  ];

  // v52cm — load countries from the new masters endpoint (full 250) for
  // the office editor; falls back to [] silently.
  const [countries, setCountries] = useState([]);
  const [sectors, setSectors] = useState([]);
  const [contractTypes, setContractTypes] = useState([]);
  useEffect(() => {
    api.get("/api/v1/masters/countries")
      .then((r) => setCountries(Array.isArray(r.data) ? r.data : []))
      .catch(() => setCountries([]));
    publicApi.listSectorsPublic().then((r) => setSectors(Array.isArray(r) ? r : [])).catch(() => setSectors([]));
    publicApi.listContractTypesPublic().then((r) => setContractTypes(Array.isArray(r) ? r : [])).catch(() => setContractTypes([]));
  }, []);

  // v52co — normalise business_categories. Existing drafts stored names as
  // strings; new drafts store {code, title}. The picker understands both.
  const businessCategories = useMemo(() => {
    const raw = reg.business_categories || [];
    return raw.map((v) => (typeof v === "string" ? { code: v, title: v } : v));
  }, [reg.business_categories]);

  // v52co — the hardcoded Kazakhstan-licenses block is only relevant to KZ
  // vendors. Gate it on KZ being either the main country or an office country.
  const kzIsRelevant = useMemo(() => {
    if ((reg.country || "").toUpperCase() === "KZ") return true;
    for (const o of reg.operating_regions || []) {
      if (o && typeof o === "object" && (o.country_code || "").toUpperCase() === "KZ") return true;
    }
    return false;
  }, [reg.country, reg.operating_regions]);

  return (
    <div className="grid gap-5">
      <Field label={t("section_d.primary_sector")}>
        <Input testId="f-primary-sector" value={reg.primary_sector || ""} onChange={(e) => update({ primary_sector: e.target.value })} />
      </Field>
      <Field label={t("section_d.business_description")}>
        <textarea data-testid="f-business-desc" value={reg.business_description || ""} onChange={(e) => update({ business_description: e.target.value })} rows={4}
          className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
      </Field>

      {/* v56s — Sector → Contract type taxonomy (cascading). Optional now;
          becomes mandatory on submit once an admin switches the portal to go-live. */}
      <Field label="Sector" hint="Industry/domain you operate in. Optional now; required once the portal goes live.">
        <select data-testid="f-sector-code" value={reg.sector_code || ""}
          onChange={(e) => {
            const s = sectors.find((x) => x.code === e.target.value);
            update({ sector_code: e.target.value, sector_name: s ? s.name : "", contract_type_code: "", contract_type_name: "" });
          }}
          className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white text-brand-navy focus:outline-none focus:border-brand-navy-soft">
          <option value="">Select a sector…</option>
          {sectors.map((s) => <option key={s.code} value={s.code}>{s.name}</option>)}
        </select>
      </Field>
      <Field label="Contract type" hint="Delivery model you bid for (EPC, O&M, PPP…). Optional now; required at go-live.">
        <select data-testid="f-contract-type-code" value={reg.contract_type_code || ""}
          disabled={!reg.sector_code}
          onChange={(e) => {
            const c = contractTypes.find((x) => x.code === e.target.value);
            update({ contract_type_code: e.target.value, contract_type_name: c ? c.name : "" });
          }}
          className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white text-brand-navy focus:outline-none focus:border-brand-navy-soft disabled:opacity-50">
          <option value="">{reg.sector_code ? "Select a contract type…" : "Pick a sector first"}</option>
          {contractTypes.filter((c) => !reg.sector_code || !c.parent_code || c.parent_code === reg.sector_code).map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
        </select>
      </Field>
      <Field label={t("section_d.operating_regions")}
             hint="Add one entry per office with name, address, country, city, state and ZIP. Previously comma-separated regions remain visible above and can be re-added as offices.">
        <RegionOfficeEditor
          value={reg.operating_regions || []}
          onChange={(v) => update({ operating_regions: v })}
          countries={countries} />
      </Field>

      {/* v52co — business verticals via full UNSPSC multi-select. Same
          search backend as Section C; works for every country including
          Bangladesh / Bosnia / etc. */}
      <Field label={t("section_d.business_categories")}
             hint="Search the full UNSPSC codeset — biogas, solar plant, construction, CBG, STP, etc. Picks accumulate as chips you can remove.">
        <UnspscMultiPicker
          value={businessCategories}
          onChange={(next) => update({ business_categories: next })}
          testidPrefix="f-categories" />
      </Field>

      {/* v52co — legacy KZ licence checklist gated on KZ being relevant. */}
      {kzIsRelevant && (
        <Field label={t("section_d.kz_licenses")} hint={t("section_d.kz_licenses_hint")}>
          <div className="grid md:grid-cols-2 gap-2 mt-2" data-testid="f-kz-licenses-block">
            {(kzMeta?.licenses || []).map((lic) => {
              const held = (reg.kz_licenses || []).includes(lic);
              return (
                <label key={lic} className="flex items-center gap-2 border border-brand-navy/10 px-3 py-2 bg-white cursor-pointer hover:border-brand-navy-soft/60">
                  <input
                    type="checkbox"
                    data-testid={`f-kz-license-${lic.split(" ")[0].toLowerCase()}`}
                    checked={held}
                    onChange={() => {
                      const cur = new Set(reg.kz_licenses || []);
                      if (held) cur.delete(lic); else cur.add(lic);
                      update({ kz_licenses: Array.from(cur) });
                    }}
                  />
                  <span className="text-sm text-brand-navy">{lic}</span>
                </label>
              );
            })}
          </div>
        </Field>
      )}

      {/* v52cn — Country-specific license requirements. Pulled from the
          Country Licenses master based on the main country + every office
          country added above. Admin can edit the master from
          Masters → Country Licenses. */}
      <CountryLicenseSlots
        reg={reg} regId={regId} token={token}
        ensureDraft={ensureDraft} onDocChange={onDocChange} />
      <Field label={t("section_d.iso_certifications")}>
        <Input testId="f-iso" value={reg.iso_certifications || ""} onChange={(e) => update({ iso_certifications: e.target.value })} />
      </Field>
      <Field label={t("section_d.insurance_details")}>
        <Input testId="f-insurance" value={reg.insurance_details || ""} onChange={(e) => update({ insurance_details: e.target.value })} />
      </Field>
      <Field label={t("section_d.litigation_history")}>
        <textarea data-testid="f-litigation" rows={2} value={reg.litigation_history || ""} onChange={(e) => update({ litigation_history: e.target.value })}
          className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
      </Field>
      <DocSlotsBlock
        title={t("section_d.docs_title")}
        regId={regId} token={token} ensureDraft={ensureDraft}
        slots={slots}
        existing={reg.document_slots || {}}
        onChange={onDocChange}
      />
    </div>
  );
}
