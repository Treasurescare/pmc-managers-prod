import { useState } from "react";
import { toast } from "sonner";
import { registrationApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

/**
 * DocSlot — single-slot document uploader for the registration form.
 * Uploads via multipart to /api/v1/registrations/{id}/documents/{slot}
 * with the magic token in FormData. Renders view / download / delete.
 */
export default function DocSlot({ regId, token, slot, label, required, existing, onChange, ensureDraft }) {
  const { t } = useI18n();
  const [busy, setBusy] = useState(false);

  const upload = async (file) => {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      return toast.error(t("docs.too_big"));
    }
    setBusy(true);
    try {
      // Auto-create the draft transparently the first time the user actually
      // picks a file — so they never bump into "save the draft first".
      let rid = regId, tok = token;
      if ((!rid || !tok) && typeof ensureDraft === "function") {
        const r = await ensureDraft();
        if (!r) { setBusy(false); return; }
        rid = r.regId; tok = r.token;
      }
      if (!rid || !tok) {
        toast.error("Enter the vendor email first — the draft is auto-saved before the upload.");
        return;
      }
      const meta = await registrationApi.uploadDocument(rid, tok, slot, file);
      toast.success(`${label} · ${t("docs.uploaded_ok")}`);
      onChange({ ...meta });
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const remove = async () => {
    if (!confirm(t("docs.remove_confirm"))) return;
    setBusy(true);
    try {
      await registrationApi.deleteDocument(regId, token, slot);
      toast.success(`${label} · ${t("docs.removed_ok")}`);
      onChange(null);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const kb = existing?.size_bytes ? Math.round(existing.size_bytes / 1024) : null;
  const viewUrl = existing?.url ? `${process.env.REACT_APP_BACKEND_URL}${existing.url}` : null;

  return (
    <div className="border border-brand-navy/15 bg-brand-pale/40 p-4"
         data-testid={`docslot-${slot}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <div className="text-sm font-semibold text-brand-navy">
            {label}
            {required && <span className="ml-1 text-red-600">*</span>}
          </div>
          {existing ? (
            <div className="mt-1 text-xs text-brand-navy/70">
              {existing.file_name}{kb ? ` · ${kb} KB` : ""}
              <span className="ml-2 text-emerald-700">✓ {t("docs.uploaded_ok")}</span>
            </div>
          ) : (
            <div className="mt-1 text-xs text-brand-navy/50">
              {required ? t("docs.required") : t("docs.optional")} · {t("docs.max_size")}
            </div>
          )}
        </div>
        <div className="flex gap-1">
          {existing && (
            <>
              <a href={viewUrl} target="_blank" rel="noreferrer"
                 data-testid={`docslot-view-${slot}`}
                 className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy hover:bg-white">{t("docs.view")}</a>
              <a href={viewUrl} download={existing.file_name}
                 data-testid={`docslot-download-${slot}`}
                 className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy hover:bg-white">{t("docs.download")}</a>
              <button type="button" onClick={remove} disabled={busy}
                      data-testid={`docslot-delete-${slot}`}
                      className="text-[10px] uppercase tracking-widest px-2 py-1 border border-red-500 text-red-600 hover:bg-red-50 disabled:opacity-50">
                {t("docs.delete")}
              </button>
            </>
          )}
          {!existing && (
            <label className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white cursor-pointer"
                   data-testid={`docslot-upload-label-${slot}`}>
              {busy ? t("docs.uploading") : t("docs.upload")}
              <input type="file" accept=".pdf,.jpg,.jpeg,.png,.docx"
                     onChange={(e) => upload(e.target.files?.[0])}
                     data-testid={`docslot-input-${slot}`}
                     disabled={busy} className="hidden" />
            </label>
          )}
        </div>
      </div>
    </div>
  );
}

export function DocSlotsBlock({ regId, token, slots, existing, onChange, title, ensureDraft }) {
  const { t } = useI18n();
  const required = slots.filter(([, m]) => m.required);
  const requiredDone = required.filter(([slot]) => !!existing?.[slot]).length;
  const requiredTotal = required.length;
  const optionalDone = slots.filter(([slot, m]) => !m.required && !!existing?.[slot]).length;
  const pct = requiredTotal === 0 ? 100 : Math.round((requiredDone / requiredTotal) * 100);
  return (
    <div className="mt-8 border-t border-brand-navy/10 pt-6"
         data-testid="docslots-block">
      <div className="flex items-baseline justify-between flex-wrap gap-2">
        <div className="pmc-label">{title || t("docs.default_title")}</div>
        <div className="text-xs" data-testid="docslots-meter">
          <span className={requiredDone === requiredTotal ? "text-emerald-700 font-semibold" : "text-amber-700 font-semibold"}>
            {requiredDone} / {requiredTotal} {t("docs.required_meter")}
          </span>
          {optionalDone > 0 && <span className="text-brand-navy/50"> · {optionalDone} {t("docs.optional_meter")}</span>}
        </div>
      </div>
      <div className="mt-2 h-1.5 w-full bg-brand-navy/10 overflow-hidden rounded-full"
           data-testid="docslots-progress">
        <div className={"h-full transition-all " + (requiredDone === requiredTotal ? "bg-emerald-600" : "bg-amber-500")}
             style={{ width: `${pct}%` }} />
      </div>
      <div className="text-xs text-brand-navy/60 mt-2">
        {t("docs.replace_hint")}
      </div>
      <div className="grid gap-3 md:grid-cols-2 mt-4">
        {slots.map(([slot, meta]) => (
          <DocSlot
            key={slot}
            regId={regId}
            token={token}
            ensureDraft={ensureDraft}
            slot={slot}
            label={meta.label}
            required={meta.required}
            existing={existing?.[slot]}
            onChange={(newMeta) => onChange(slot, newMeta)}
          />
        ))}
      </div>
    </div>
  );
}
