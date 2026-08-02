import { Field, Input } from "./FormPrimitives";
import { DocSlotsBlock } from "./DocSlot";

const SECTION_D_SLOTS = [
  ["signed_declaration", { label: "Signed Declarations & Consent (PDF)", required: false }],
];

export default function SectionD({ reg, update, kzMeta, regId, token, onDocChange }) {
  return (
    <div className="grid gap-5">
      <Field label="Primary sector">
        <Input testId="f-primary-sector" value={reg.primary_sector || ""} onChange={(e) => update({ primary_sector: e.target.value })} />
      </Field>
      <Field label="Business description">
        <textarea data-testid="f-business-desc" value={reg.business_description || ""} onChange={(e) => update({ business_description: e.target.value })} rows={4}
          className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
      </Field>
      <Field label="Operating regions (comma separated)">
        <Input testId="f-op-regions" value={(reg.operating_regions || []).join(", ")}
          onChange={(e) => update({ operating_regions: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} />
      </Field>
      <Field label="Business categories (comma separated)">
        <Input testId="f-categories" value={(reg.business_categories || []).join(", ")}
          onChange={(e) => update({ business_categories: e.target.value.split(",").map((s) => s.trim()).filter(Boolean) })} />
      </Field>
      <Field label="Kazakhstan licenses held" hint="Only select licenses your company currently holds. These gate access to KZ tenders that require them.">
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
      <Field label="ISO certifications">
        <Input testId="f-iso" value={reg.iso_certifications || ""} onChange={(e) => update({ iso_certifications: e.target.value })} />
      </Field>
      <Field label="Insurance details">
        <Input testId="f-insurance" value={reg.insurance_details || ""} onChange={(e) => update({ insurance_details: e.target.value })} />
      </Field>
      <Field label="Litigation history">
        <textarea data-testid="f-litigation" rows={2} value={reg.litigation_history || ""} onChange={(e) => update({ litigation_history: e.target.value })}
          className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
      </Field>
      <DocSlotsBlock
        title="Signed declarations upload (Section D)"
        regId={regId} token={token}
        slots={SECTION_D_SLOTS}
        existing={reg.document_slots || {}}
        onChange={onDocChange}
      />
    </div>
  );
}
