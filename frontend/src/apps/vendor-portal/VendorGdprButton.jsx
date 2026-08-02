import { useState } from "react";
import { toast } from "sonner";
import { gdprApi, formatApiError } from "@/lib/api";

/**
 * GDPR self-service — vendor can anonymise their own profile after re-entering
 * their password. Also anonymises linked registrations. On success, we sign
 * the vendor out (their account is disabled).
 */
export default function VendorGdprButton({ onSuccess }) {
  const [open, setOpen] = useState(false);
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [ack, setAck] = useState(false);

  const confirm = async () => {
    if (!password) return toast.error("Enter your password to confirm");
    if (!ack) return toast.error("Please tick the acknowledgement checkbox");
    setSubmitting(true);
    try {
      await gdprApi.vendorSelfForget(password);
      toast.success("Your profile has been anonymised.");
      setOpen(false);
      if (onSuccess) onSuccess();
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setSubmitting(false); }
  };

  return (
    <>
      <button type="button" onClick={() => setOpen(true)}
              data-testid="vendor-gdpr-open"
              className="text-white/80 hover:text-white underline text-sm">
        Delete my data
      </button>

      {open && (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4"
             data-testid="vendor-gdpr-modal" onClick={() => !submitting && setOpen(false)}>
          <div className="bg-white max-w-md w-full p-6 rounded-lg space-y-4"
               onClick={(e) => e.stopPropagation()}>
            <h3 className="font-serif text-lg text-red-700">Delete my account (GDPR)</h3>
            <p className="text-sm text-slate-600">
              This will anonymise your profile and all linked registrations. This action
              is irreversible — your bids will remain (audit trail) but with your details
              redacted. You will be signed out immediately.
            </p>
            <label className="block text-sm">
              <span className="text-slate-700">Confirm your password</span>
              <input type="password" value={password}
                     onChange={(e) => setPassword(e.target.value)}
                     data-testid="vendor-gdpr-password"
                     className="mt-1 w-full px-3 py-2 border rounded text-sm" />
            </label>
            <label className="flex items-start gap-2 text-xs text-slate-700">
              <input type="checkbox" checked={ack}
                     onChange={(e) => setAck(e.target.checked)}
                     data-testid="vendor-gdpr-ack" />
              I understand this is permanent and cannot be undone.
            </label>
            <div className="flex justify-end gap-2 pt-2">
              <button onClick={() => setOpen(false)} disabled={submitting}
                      className="px-4 py-2 text-sm border rounded">Cancel</button>
              <button onClick={confirm} disabled={submitting}
                      data-testid="vendor-gdpr-confirm"
                      className="px-4 py-2 text-sm bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50">
                {submitting ? "Deleting…" : "Delete permanently"}
              </button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
