import { useState } from "react";
import { Field, Input } from "./FormPrimitives";

/**
 * v52ci — Structured "Operation Regions / Offices" editor.
 *
 * Replaces the earlier plain comma-separated input that let vendors type any
 * region name. The user now adds one row per office with:
 *   office_name · address · country_code · zip · city · state
 *
 * Backwards compatible: if `value` is a legacy string[] we show them as
 * read-only chips above the editor and start the structured list empty.
 */
export default function RegionOfficeEditor({ value, onChange, countries }) {
  const list = Array.isArray(value) ? value : [];
  const legacyStrings = list.filter((v) => typeof v === "string").filter(Boolean);
  const offices = list.filter((v) => v && typeof v === "object");
  const [draft, setDraft] = useState({
    office_name: "", address: "", country_code: "", zip: "", city: "", state: "",
  });

  const patchOffice = (idx, patch) => {
    const next = [...offices];
    next[idx] = { ...next[idx], ...patch };
    onChange([...legacyStrings, ...next]);
  };
  const removeOffice = (idx) => {
    const next = offices.filter((_, i) => i !== idx);
    onChange([...legacyStrings, ...next]);
  };
  const addOffice = () => {
    const required = ["office_name", "address", "country_code", "city", "state"];
    const missing = required.filter((k) => !String(draft[k] || "").trim());
    if (missing.length) {
      alert("Fill all required office fields before adding: " + missing.join(", "));
      return;
    }
    onChange([...legacyStrings, ...offices, { ...draft }]);
    setDraft({ office_name: "", address: "", country_code: "", zip: "", city: "", state: "" });
  };

  return (
    <div className="space-y-3" data-testid="op-regions-editor">
      {legacyStrings.length > 0 && (
        <div className="text-xs text-brand-navy/60 bg-amber-50 border border-amber-200 px-3 py-2"
             data-testid="op-regions-legacy">
          Previously declared regions (please re-add as offices below):{" "}
          <span className="font-semibold">{legacyStrings.join(", ")}</span>
        </div>
      )}

      {offices.map((o, i) => (
        <div key={i} className="border border-brand-navy/15 bg-white p-3"
             data-testid={`op-region-row-${i}`}>
          <div className="flex items-center justify-between mb-2">
            <div className="text-[11px] uppercase tracking-widest text-brand-navy-soft">
              Office {i + 1}
            </div>
            <button type="button" onClick={() => removeOffice(i)}
                    data-testid={`op-region-remove-${i}`}
                    className="text-[10px] uppercase text-red-700 hover:underline">
              ✕ remove
            </button>
          </div>
          <div className="grid gap-2 md:grid-cols-2">
            <Field label="Office name *">
              <Input value={o.office_name || ""}
                     onChange={(e) => patchOffice(i, { office_name: e.target.value })}
                     testId={`op-region-name-${i}`} />
            </Field>
            <Field label="Country *">
              <select value={o.country_code || ""}
                      onChange={(e) => patchOffice(i, { country_code: e.target.value })}
                      data-testid={`op-region-country-${i}`}
                      className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white">
                <option value="">Pick a country…</option>
                {(countries || []).map((c) => (
                  <option key={c.code} value={c.code}>
                    {c.name ? `${c.code} — ${c.name}` : c.code}
                  </option>
                ))}
              </select>
            </Field>
            <Field label="Address *" className="md:col-span-2">
              <textarea rows={2} value={o.address || ""}
                        onChange={(e) => patchOffice(i, { address: e.target.value })}
                        data-testid={`op-region-address-${i}`}
                        className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white" />
            </Field>
            <Field label="City *">
              <Input value={o.city || ""}
                     onChange={(e) => patchOffice(i, { city: e.target.value })}
                     testId={`op-region-city-${i}`} />
            </Field>
            <Field label="State / Province *">
              <Input value={o.state || ""}
                     onChange={(e) => patchOffice(i, { state: e.target.value })}
                     testId={`op-region-state-${i}`} />
            </Field>
            <Field label="ZIP / Postal code">
              <Input value={o.zip || ""}
                     onChange={(e) => patchOffice(i, { zip: e.target.value })}
                     testId={`op-region-zip-${i}`} />
            </Field>
          </div>
        </div>
      ))}

      <div className="border border-dashed border-brand-navy/30 bg-brand-pale/30 p-3"
           data-testid="op-region-new">
        <div className="text-[11px] uppercase tracking-widest text-brand-navy/60 mb-2">
          Add another office
        </div>
        <div className="grid gap-2 md:grid-cols-2">
          <Field label="Office name *">
            <Input value={draft.office_name}
                   onChange={(e) => setDraft({ ...draft, office_name: e.target.value })}
                   testId="op-region-new-name" />
          </Field>
          <Field label="Country *">
            <select value={draft.country_code}
                    onChange={(e) => setDraft({ ...draft, country_code: e.target.value })}
                    data-testid="op-region-new-country"
                    className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white">
              <option value="">Pick a country…</option>
              {(countries || []).map((c) => (
                <option key={c.code} value={c.code}>
                  {c.name ? `${c.code} — ${c.name}` : c.code}
                </option>
              ))}
            </select>
          </Field>
          <Field label="Address *" className="md:col-span-2">
            <textarea rows={2} value={draft.address}
                      onChange={(e) => setDraft({ ...draft, address: e.target.value })}
                      data-testid="op-region-new-address"
                      className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white" />
          </Field>
          <Field label="City *">
            <Input value={draft.city}
                   onChange={(e) => setDraft({ ...draft, city: e.target.value })}
                   testId="op-region-new-city" />
          </Field>
          <Field label="State / Province *">
            <Input value={draft.state}
                   onChange={(e) => setDraft({ ...draft, state: e.target.value })}
                   testId="op-region-new-state" />
          </Field>
          <Field label="ZIP / Postal code">
            <Input value={draft.zip}
                   onChange={(e) => setDraft({ ...draft, zip: e.target.value })}
                   testId="op-region-new-zip" />
          </Field>
        </div>
        <button type="button" onClick={addOffice}
                data-testid="op-region-add-btn"
                className="mt-3 px-4 py-2 text-[11px] uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          + Add office
        </button>
      </div>
    </div>
  );
}
