import { useEffect, useRef, useState } from "react";
import { toast } from "sonner";
import { adminApi, vendorApi, formatApiError } from "@/lib/api";

/**
 * ProfileModal — unified self-service profile panel.
 *
 * Props:
 *   open      — boolean
 *   onClose   — fn
 *   role      — "admin" | "vendor"
 *   me        — user object with email / avatar_data_url / name?
 *   onChange  — fn(me) called after successful avatar upload/removal
 */
export default function ProfileModal({ open, onClose, role, me, onChange }) {
  const api = role === "vendor" ? vendorApi : adminApi;
  const fileRef = useRef(null);
  const [avatar, setAvatar] = useState(me?.avatar_data_url || "");
  const [tab, setTab] = useState("avatar");

  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    if (open) {
      setAvatar(me?.avatar_data_url || "");
      setCurrent(""); setNext(""); setConfirm("");
      setTab("avatar");
    }
  }, [open, me]);

  if (!open) return null;

  const pickFile = () => fileRef.current?.click();

  const onFile = async (e) => {
    const file = e.target.files?.[0];
    if (!file) return;
    if (!/^image\/(png|jpe?g|webp)$/.test(file.type))
      return toast.error("Please pick a PNG, JPG or WEBP image.");
    // Resize to 256x256 square, JPEG quality 0.85
    const dataUrl = await resizeSquare(file, 256);
    if (!dataUrl) return toast.error("Could not read image file.");
    if (dataUrl.length > 340 * 1024) return toast.error("Image still too large — pick a smaller one.");
    setAvatar(dataUrl);
  };

  const saveAvatar = async () => {
    if (!avatar) return toast.error("Pick a photo first.");
    setBusy(true);
    try {
      await api.uploadAvatar(avatar);
      toast.success("Photo updated.");
      onChange && onChange({ ...me, avatar_data_url: avatar });
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const removeAvatar = async () => {
    setBusy(true);
    try {
      await api.removeAvatar();
      setAvatar("");
      toast.success("Photo removed.");
      onChange && onChange({ ...me, avatar_data_url: null });
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  const changePwd = async (e) => {
    e.preventDefault();
    if (next.length < 10) return toast.error("New password must be at least 10 characters.");
    if (next !== confirm) return toast.error("New passwords don't match.");
    if (next === current) return toast.error("New password must differ from the current one.");
    setBusy(true);
    try {
      await api.changePassword(current, next);
      toast.success("Password changed. Please sign in again next time.");
      setCurrent(""); setNext(""); setConfirm("");
    } catch (err) { toast.error(formatApiError(err)); }
    finally { setBusy(false); }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4"
         data-testid="profile-modal">
      <div className="absolute inset-0 bg-black/50" onClick={onClose} />
      <div className="relative bg-white border border-brand-navy/10 shadow-2xl w-full max-w-lg">
        <div className="flex items-center justify-between px-6 py-4 border-b border-brand-navy/10">
          <div>
            <div className="pmc-label">My profile</div>
            <div className="font-display text-brand-navy text-lg leading-tight">{me?.email}</div>
          </div>
          <button onClick={onClose} data-testid="profile-close"
                  className="w-9 h-9 border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">✕</button>
        </div>

        <div className="flex border-b border-brand-navy/10 text-[11px] font-semibold uppercase tracking-widest">
          {[["avatar", "Photo"], ["password", "Password"]].map(([k, l]) => (
            <button key={k} onClick={() => setTab(k)} data-testid={`profile-tab-${k}`}
                    className={"px-6 py-3 " +
                      (tab === k ? "bg-brand-navy text-white"
                                 : "text-brand-navy/60 hover:bg-brand-navy/5")}>
              {l}
            </button>
          ))}
        </div>

        {tab === "avatar" && (
          <div className="p-6 space-y-4">
            <div className="flex items-center gap-5">
              <div className="w-24 h-24 rounded-full bg-brand-navy/5 border border-brand-navy/10 overflow-hidden flex items-center justify-center">
                {avatar
                  ? <img src={avatar} alt="Avatar" className="w-full h-full object-cover"
                         data-testid="profile-avatar-preview" />
                  : <span className="text-brand-navy/40 font-display text-3xl">
                      {(me?.email || "?").slice(0, 1).toUpperCase()}
                    </span>}
              </div>
              <div className="flex-1 space-y-2">
                <input type="file" hidden ref={fileRef}
                       accept="image/png,image/jpeg,image/webp"
                       data-testid="profile-avatar-file"
                       onChange={onFile} />
                <button onClick={pickFile} data-testid="profile-avatar-pick"
                        className="px-4 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
                  Pick photo
                </button>
                {avatar && (
                  <button onClick={removeAvatar} disabled={busy}
                          data-testid="profile-avatar-remove"
                          className="ml-2 px-4 py-2 text-[11px] font-semibold uppercase tracking-widest border border-red-500 text-red-600 hover:bg-red-50 disabled:opacity-50">
                    Remove
                  </button>
                )}
                <div className="text-xs text-brand-navy/50">PNG · JPG · WEBP · square recommended · max 350 KB.</div>
              </div>
            </div>
            <div className="pt-4 border-t border-brand-navy/10 flex justify-end">
              <button onClick={saveAvatar} disabled={busy || !avatar}
                      data-testid="profile-avatar-save"
                      className="px-6 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
                {busy ? "Saving…" : "Save photo"}
              </button>
            </div>
          </div>
        )}

        {tab === "password" && (
          <form onSubmit={changePwd} className="p-6 space-y-4" data-testid="profile-pwd-form">
            <PwdField label="Current password" value={current} onChange={setCurrent}
                      testId="profile-pwd-current" />
            <PwdField label="New password (≥10 chars)" value={next} onChange={setNext}
                      testId="profile-pwd-new" />
            <PwdField label="Confirm new password" value={confirm} onChange={setConfirm}
                      testId="profile-pwd-confirm" />
            <div className="pt-4 border-t border-brand-navy/10 flex justify-end gap-2">
              <button type="button" onClick={onClose}
                      className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
                Cancel
              </button>
              <button type="submit" disabled={busy}
                      data-testid="profile-pwd-submit"
                      className="px-6 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep disabled:opacity-50">
                {busy ? "Saving…" : "Change password"}
              </button>
            </div>
          </form>
        )}
      </div>
    </div>
  );
}

function PwdField({ label, value, onChange, testId }) {
  return (
    <label className="block text-sm">
      <span className="pmc-label">{label}</span>
      <input type="password" required value={value}
             onChange={(e) => onChange(e.target.value)}
             data-testid={testId}
             className="mt-1 w-full px-4 py-3 border border-brand-navy/20 focus:outline-none focus:border-brand-navy-soft text-brand-navy bg-white" />
    </label>
  );
}

/** Client-side resize: keeps upload payload small so Mongo docs stay lean. */
async function resizeSquare(file, size) {
  return new Promise((resolve) => {
    const reader = new FileReader();
    reader.onload = () => {
      const img = new Image();
      img.onload = () => {
        const canvas = document.createElement("canvas");
        canvas.width = size; canvas.height = size;
        const ctx = canvas.getContext("2d");
        // Center-crop to square then draw
        const s = Math.min(img.width, img.height);
        const sx = (img.width - s) / 2;
        const sy = (img.height - s) / 2;
        ctx.drawImage(img, sx, sy, s, s, 0, 0, size, size);
        resolve(canvas.toDataURL("image/jpeg", 0.85));
      };
      img.onerror = () => resolve(null);
      img.src = reader.result;
    };
    reader.onerror = () => resolve(null);
    reader.readAsDataURL(file);
  });
}
