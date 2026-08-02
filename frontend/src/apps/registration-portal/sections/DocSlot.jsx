import { useState } from "react";
import { toast } from "sonner";
import { registrationApi, formatApiError } from "@/lib/api";

/**
 * DocSlot — single-slot document uploader for the registration form.
 * Uploads via multipart to /api/v1/registrations/{id}/documents/{slot}
 * with the magic token in FormData. Renders view / download / delete.
 */
export default function DocSlot({ regId, token, slot, label, required, existing, onChange }) {
  const [busy, setBusy] = useState(false);

  const upload = async (file) => {
    if (!file) return;
    if (file.size > 5 * 1024 * 1024) {
      return toast.error("File too big (max 5 MB in pilot)");
    }
    setBusy(true);
    try {
      const meta = await registrationApi.uploadDocument(regId, token, slot, file);
      toast.success(`${label} uploaded`);
      onChange({ ...meta });
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setBusy(false); }
  };

  const remove = async () => {
    if (!confirm(`Remove the uploaded "${label}"?`)) return;
    setBusy(true);
    try {
      await registrationApi.deleteDocument(regId, token, slot);
      toast.success(`${label} removed`);
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
              <span className="ml-2 text-emerald-700">✓ uploaded</span>
            </div>
          ) : (
            <div className="mt-1 text-xs text-brand-navy/50">
              {required ? "Required" : "Optional"} · PDF, JPG or PNG · max 5 MB
            </div>
          )}
        </div>
        <div className="flex gap-1">
          {existing && (
            <>
              <a href={viewUrl} target="_blank" rel="noreferrer"
                 data-testid={`docslot-view-${slot}`}
                 className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy hover:bg-white">View</a>
              <a href={viewUrl} download={existing.file_name}
                 data-testid={`docslot-download-${slot}`}
                 className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy/20 text-brand-navy hover:bg-white">Download</a>
              <button type="button" onClick={remove} disabled={busy}
                      data-testid={`docslot-delete-${slot}`}
                      className="text-[10px] uppercase tracking-widest px-2 py-1 border border-red-500 text-red-600 hover:bg-red-50 disabled:opacity-50">
                Delete
              </button>
            </>
          )}
          {!existing && (
            <label className="text-[10px] uppercase tracking-widest px-2 py-1 border border-brand-navy text-brand-navy hover:bg-brand-navy hover:text-white cursor-pointer"
                   data-testid={`docslot-upload-label-${slot}`}>
              {busy ? "Uploading…" : "Upload"}
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

export function DocSlotsBlock({ regId, token, slots, existing, onChange, title = "Required documents" }) {
  return (
    <div className="mt-8 border-t border-brand-navy/10 pt-6"
         data-testid="docslots-block">
      <div className="pmc-label">{title}</div>
      <div className="text-xs text-brand-navy/60 mt-1">
        Upload once — you can replace or delete anytime before submitting.
      </div>
      <div className="grid gap-3 md:grid-cols-2 mt-4">
        {slots.map(([slot, meta]) => (
          <DocSlot
            key={slot}
            regId={regId}
            token={token}
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
