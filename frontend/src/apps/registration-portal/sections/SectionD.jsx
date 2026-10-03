import { useEffect, useMemo, useState } from "react";
import { Field, Input } from "./FormPrimitives";
import { DocSlotsBlock } from "./DocSlot";
import { useI18n } from "@/context/I18nContext";
import { mastersApi } from "@/lib/api";

/**
 * v50y — Section D with a real multi-select "Business verticals"
 * (business_categories) fed by the Categories master (UNSPSC-backed).
 * Replaces the earlier free-text comma-separated input that let vendors
 * type anything and bypassed the admin taxonomy.
 */
export default function SectionD({ reg, update, kzMeta, regId, token, onDocChange, ensureDraft }) {
  const { t, lang } = useI18n();
  const slots = [
    ["signed_declaration", { label: t("section_d.doc_signed_declaration"), required: false }],
  ];

  const [catalogue, setCatalogue] = useState([]);
  const [catQuery, setCatQuery] = useState("");

  useEffect(() => {
    mastersApi.listCategoriesPublic(reg.country || undefined)
      .then((rows) => setCatalogue(Array.isArray(rows) ? rows : []))
      .catch(() => setCatalogue([]));
  }, [reg.country]);

  const selected = reg.business_categories || [];
  const toggle = (name) => {
    const set = new Set(selected);
    if (set.has(name)) set.delete(name); else set.add(name);
    update({ business_categories: Array.from(set) });
  };

  const filtered = useMemo(() => {
    const q = catQuery.trim().toLowerCase();
    if (!q) return catalogue;
    return catalogue.filter((c) =>
      [c.name, c.name_ru, c.name_kz, c.code, c.unspsc_code]
        .filter(Boolean)
        .some((s) => String(s).toLowerCase().includes(q)));
  }, [catalogue, catQuery]);

  const label = (c) =>
    (lang === "ru" && c.name_ru) ? c.name_ru
    : (lang === "kz" && c.name_kz) ? c.name_kz
    : c.name;

  return (
    <div className="grid gap-5">
      <Field label={t("section_d.primary_sector")}>
        <Input testId="f-primary-sector" value={reg.primary_sector || ""} onChange={(e) => update({ primary_sector: e.target.value })} />
      </Field>
      <Field label={t("section_d.business_description")}>
        <textarea data-testid="f-business-desc" value={reg.business_description || ""} onChange={(e) => update({ business_description: e.target.value })} rows={4}
          className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
      </Field>
      <Field label={t("section_d.operating_regions")}>
        <Input testId="f-op-regions" value={(reg.operating_regions || []).join(", ")}
          onChange={(e) => update({ operating_regions: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} />
      </Field>

      {/* v50y — business verticals from the Categories master */}
      <Field label={t("section_d.business_categories")}
             hint="Choose from PMC's Categories master (UNSPSC-backed). Admin controls the list from Masters → Categories.">
        <div data-testid="f-categories-picker"
             className="mt-1 border border-brand-navy/20 bg-white">
          <input value={catQuery}
                 onChange={(e) => setCatQuery(e.target.value)}
                 placeholder={catalogue.length
                   ? `Search ${catalogue.length} verticals…`
                   : "Loading verticals from Categories master…"}
                 className="w-full px-3 py-2 border-b border-brand-navy/10 text-sm"
                 data-testid="f-categories-search" />
          {selected.length > 0 && (
            <div className="flex flex-wrap gap-1 p-2 border-b border-brand-navy/10 bg-brand-pale/40"
                 data-testid="f-categories-selected">
              {selected.map((name) => (
                <button type="button" key={name} onClick={() => toggle(name)}
                        className="text-[11px] uppercase tracking-widest px-2 py-1 bg-emerald-100 text-emerald-900 hover:bg-red-100 hover:text-red-700"
                        data-testid={`f-cat-chip-${name}`}>
                  ✓ {name} ×
                </button>
              ))}
            </div>
          )}
          <div className="max-h-48 overflow-y-auto">
            {filtered.length === 0 ? (
              <div className="p-3 text-xs text-brand-navy/50">
                {catalogue.length === 0
                  ? "The Categories master is empty — ask the admin to seed it from Masters → Categories."
                  : "No matches — try a different search."}
              </div>
            ) : filtered.slice(0, 100).map((c) => {
              const isOn = selected.includes(c.name);
              return (
                <label key={c.id || c.code}
                       className={`flex items-center gap-2 px-3 py-2 text-sm cursor-pointer border-b border-brand-navy/5 ${isOn ? "bg-emerald-50" : "hover:bg-brand-pale/30"}`}
                       data-testid={`f-cat-row-${c.code}`}>
                  <input type="checkbox" checked={isOn}
                         onChange={() => toggle(c.name)} />
                  <span className="flex-1">{label(c)}</span>
                  {c.unspsc_code && (
                    <span className="text-[10px] font-mono text-brand-navy/40">
                      {c.unspsc_code}
                    </span>
                  )}
                </label>
              );
            })}
            {filtered.length > 100 && (
              <div className="p-2 text-xs text-brand-navy/50">
                Showing first 100 of {filtered.length} — refine your search for the rest.
              </div>
            )}
          </div>
        </div>
      </Field>

      <Field label={t("section_d.kz_licenses")} hint={t("section_d.kz_licenses_hint")}>
        <div className="grid md:grid-cols-2 gap-2 mt-2">
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
