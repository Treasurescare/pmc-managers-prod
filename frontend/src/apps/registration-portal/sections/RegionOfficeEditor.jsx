import { useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Field, Input } from "./FormPrimitives";
import { api } from "@/lib/api";

/**
 * v52ci / v52cm — Structured "Operation Regions / Offices" editor.
 *
 * v52cm — country/state/city are now cascading dropdowns backed by the
 * masters_countries / masters_states / masters_cities collections
 * (dr5hn 250c × 5.3k states × 152k cities). ZIP stays free text but is
 * live-validated against the country's `postal_code_regex`.
 *
 * Backwards compatible: legacy string[] entries continue to render in a
 * dismissible banner above the editor.
 */
export default function RegionOfficeEditor({ value, onChange, countries }) {
  const list = Array.isArray(value) ? value : [];
  const legacyStrings = list.filter((v) => typeof v === "string").filter(Boolean);
  const offices = list.filter((v) => v && typeof v === "object");

  const [draft, setDraft] = useState({
    office_name: "", address: "", country_code: "", zip: "",
    city: "", state: "", state_code: "",
  });
  const [states, setStates] = useState([]);
  const [cities, setCities] = useState([]);
  const [cityQ, setCityQ] = useState("");

  // Master country dict for postal_code_regex lookup.
  const countryByCode = useMemo(() => {
    const m = new Map();
    for (const c of (countries || [])) m.set(c.code, c);
    return m;
  }, [countries]);

  // Cascade: load states when country changes.
  useEffect(() => {
    if (!draft.country_code) { setStates([]); return; }
    api.get(`/api/v1/masters/states?country_code=${draft.country_code}`)
       .then((r) => setStates(r.data || []))
       .catch(() => setStates([]));
  }, [draft.country_code]);

  // Cascade: load cities when state changes OR user types.
  useEffect(() => {
    if (!draft.country_code || !draft.state_code) { setCities([]); return; }
    const q = cityQ.trim();
    const url = `/api/v1/masters/cities?country_code=${draft.country_code}&state_code=${encodeURIComponent(draft.state_code)}${q ? `&q=${encodeURIComponent(q)}` : ""}&limit=200`;
    api.get(url).then((r) => setCities(r.data || [])).catch(() => setCities([]));
  }, [draft.country_code, draft.state_code, cityQ]);

  // Live ZIP validation against the country's regex.
  const zipPattern = draft.country_code ? countryByCode.get(draft.country_code)?.postal_code_regex : null;
  const zipFormat  = draft.country_code ? countryByCode.get(draft.country_code)?.postal_code_format : null;
  const zipValid   = !draft.zip || !zipPattern || new RegExp(zipPattern).test(draft.zip);

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
    const required = ["office_name", "address", "country_code", "state", "city"];
    const missing = required.filter((k) => !String(draft[k] || "").trim());
    if (missing.length) {
      toast.error("Fill all REQUIRED office fields before adding: " + missing.join(", "));
      return;
    }
    if (!zipValid) {
      toast.error(`ZIP doesn't match the ${draft.country_code} format (${zipFormat || "country rule"}).`);
      return;
    }
    onChange([...legacyStrings, ...offices, { ...draft }]);
    setDraft({ office_name: "", address: "", country_code: "", zip: "",
               city: "", state: "", state_code: "" });
    setCityQ("");
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
            <Field label="Office name"><Input value={o.office_name || ""}
              onChange={(e) => patchOffice(i, { office_name: e.target.value })}
              testId={`op-region-name-${i}`} /></Field>
            <Field label="Country">
              <select value={o.country_code || ""} disabled
                      data-testid={`op-region-country-${i}`}
                      className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white disabled:bg-brand-pale/50">
                <option value={o.country_code || ""}>
                  {o.country_code
                    ? `${o.country_code} — ${countryByCode.get(o.country_code)?.name || ""}`
                    : "—"}
                </option>
              </select>
            </Field>
            <Field label="Address" className="md:col-span-2">
              <textarea rows={2} value={o.address || ""}
                        onChange={(e) => patchOffice(i, { address: e.target.value })}
                        data-testid={`op-region-address-${i}`}
                        className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white" />
            </Field>
            <Field label="City"><Input value={o.city || ""} readOnly
              testId={`op-region-city-${i}`} /></Field>
            <Field label="State / Province"><Input value={o.state || ""} readOnly
              testId={`op-region-state-${i}`} /></Field>
            <Field label="ZIP / Postal code"><Input value={o.zip || ""}
              onChange={(e) => patchOffice(i, { zip: e.target.value })}
              testId={`op-region-zip-${i}`} /></Field>
          </div>
        </div>
      ))}

      <div className="border border-dashed border-brand-navy/30 bg-brand-pale/30 p-3"
           data-testid="op-region-new">
        <div className="text-[11px] uppercase tracking-widest text-brand-navy/60 mb-2">
          Add another office
        </div>
        <div className="grid gap-2 md:grid-cols-2">
          <Field label="Office name" required><Input value={draft.office_name}
            onChange={(e) => setDraft({ ...draft, office_name: e.target.value })}
            testId="op-region-new-name" /></Field>

          <Field label="Country" required>
            <select value={draft.country_code}
                    onChange={(e) => setDraft({ ...draft, country_code: e.target.value,
                                                 state_code: "", state: "", city: "", zip: "" })}
                    data-testid="op-region-new-country"
                    className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white">
              <option value="">Pick a country…</option>
              {(countries || []).map((c) => (
                <option key={c.code} value={c.code}>
                  {c.emoji ? `${c.emoji} ` : ""}{c.code} — {c.name}
                </option>
              ))}
            </select>
          </Field>

          <Field label="Address" required className="md:col-span-2">
            <textarea rows={2} value={draft.address}
                      onChange={(e) => setDraft({ ...draft, address: e.target.value })}
                      data-testid="op-region-new-address"
                      className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white" />
          </Field>

          <Field label="State / Province" required>
            <select value={draft.state_code}
                    onChange={(e) => {
                      const s = states.find((x) => x.state_code === e.target.value);
                      setDraft({ ...draft, state_code: e.target.value,
                                 state: s?.name || "", city: "" });
                    }}
                    disabled={!draft.country_code}
                    data-testid="op-region-new-state"
                    className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white disabled:bg-brand-pale/50">
              <option value="">
                {draft.country_code ? (states.length ? "Pick a state…" : "No states for country") : "Pick a country first"}
              </option>
              {states.map((s) => <option key={s.state_code} value={s.state_code}>{s.name}</option>)}
            </select>
          </Field>

          <Field label="City" required>
            <input list="op-region-city-dl" value={draft.city}
                   onChange={(e) => { setCityQ(e.target.value); setDraft({ ...draft, city: e.target.value }); }}
                   disabled={!draft.state_code}
                   data-testid="op-region-new-city"
                   placeholder={draft.state_code ? "Type to search city…" : "Pick a state first"}
                   className="mt-1 w-full px-4 py-3 border border-brand-navy/20 bg-white disabled:bg-brand-pale/50" />
            <datalist id="op-region-city-dl">
              {cities.map((c, i) => <option key={i} value={c.name} />)}
            </datalist>
          </Field>

          <Field label={`ZIP / Postal code${zipFormat ? ` (format: ${zipFormat})` : ""}`}>
            <Input value={draft.zip}
                   onChange={(e) => setDraft({ ...draft, zip: e.target.value })}
                   testId="op-region-new-zip" />
            {!zipValid && (
              <div className="text-[11px] text-red-700 mt-1" data-testid="op-region-zip-error">
                Doesn't match {draft.country_code} format.
              </div>
            )}
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
