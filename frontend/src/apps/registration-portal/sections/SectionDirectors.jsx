import { useMemo } from "react";
import { Field, Input } from "./FormPrimitives";
import { useI18n } from "@/context/I18nContext";

// v44 — Directors & Beneficial Owners section.
// Persists into reg.directors as an array of { full_name, role, nationality,
// id_number, ownership_percent, address } records. At least one row is
// required for final submission (enforced in RegistrationResume submit gate).

const ROLE_OPTIONS = ["Director", "Shareholder", "UBO", "Officer", "Other"];

const emptyRow = () => ({
  full_name: "",
  role: "Director",
  nationality: "",
  id_number: "",
  ownership_percent: "",
  address: "",
});

export default function SectionDirectors({ reg, update }) {
  const { t } = useI18n();
  const rows = useMemo(
    () => (Array.isArray(reg.directors) && reg.directors.length > 0
      ? reg.directors
      : [emptyRow()]),
    [reg.directors]
  );

  const setRow = (idx, patch) => {
    const next = rows.map((r, i) => (i === idx ? { ...r, ...patch } : r));
    update({ directors: next });
  };

  const addRow = () => update({ directors: [...rows, emptyRow()] });

  const removeRow = (idx) => {
    const next = rows.filter((_, i) => i !== idx);
    update({ directors: next.length ? next : [emptyRow()] });
  };

  return (
    <div className="grid gap-6" data-testid="section-directors">
      <div>
        <div className="pmc-label mb-1">{t("section_directors.title")}</div>
        <p className="text-[12px] text-brand-navy/60">
          {t("section_directors.hint")}
        </p>
      </div>

      {rows.map((row, idx) => (
        <div key={idx}
             className="border border-brand-navy/15 bg-brand-pale/40 p-5 grid gap-4"
             data-testid={`director-row-${idx}`}>
          <div className="flex items-center justify-between">
            <div className="pmc-label">
              {t("section_directors.person_n")} #{idx + 1}
            </div>
            {rows.length > 1 && (
              <button type="button"
                      data-testid={`director-remove-${idx}`}
                      onClick={() => removeRow(idx)}
                      className="text-[11px] uppercase tracking-widest text-red-600 hover:underline">
                {t("section_directors.remove")}
              </button>
            )}
          </div>
          <div className="grid gap-4 md:grid-cols-2">
            <Field label={t("section_directors.full_name")}>
              <Input testId={`director-name-${idx}`}
                     value={row.full_name || ""}
                     onChange={(e) => setRow(idx, { full_name: e.target.value })} />
            </Field>
            <Field label={t("section_directors.role")}>
              <select data-testid={`director-role-${idx}`}
                      value={row.role || "Director"}
                      onChange={(e) => setRow(idx, { role: e.target.value })}
                      className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white">
                {ROLE_OPTIONS.map((opt) => (
                  <option key={opt} value={opt}>{t(`section_directors.roles.${opt}`, opt)}</option>
                ))}
              </select>
            </Field>
            <Field label={t("section_directors.nationality")}>
              <Input testId={`director-nationality-${idx}`}
                     value={row.nationality || ""}
                     onChange={(e) => setRow(idx, { nationality: e.target.value })} />
            </Field>
            <Field label={t("section_directors.id_number")}>
              <Input testId={`director-id-${idx}`}
                     value={row.id_number || ""}
                     onChange={(e) => setRow(idx, { id_number: e.target.value })} />
            </Field>
            <Field label={t("section_directors.ownership_percent")}>
              <Input testId={`director-ownership-${idx}`}
                     type="number" min="0" max="100" step="0.01"
                     value={row.ownership_percent || ""}
                     onChange={(e) => setRow(idx, { ownership_percent: e.target.value })} />
            </Field>
            <Field label={t("section_directors.address")}>
              <Input testId={`director-address-${idx}`}
                     value={row.address || ""}
                     onChange={(e) => setRow(idx, { address: e.target.value })} />
            </Field>
          </div>
        </div>
      ))}

      <div>
        <button type="button"
                data-testid="director-add"
                onClick={addRow}
                className="px-5 py-2.5 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy-soft text-brand-navy-soft hover:bg-brand-navy-soft hover:text-white">
          + {t("section_directors.add")}
        </button>
      </div>
    </div>
  );
}
