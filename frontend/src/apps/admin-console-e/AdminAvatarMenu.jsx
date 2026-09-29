import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { adminApi, showApiError } from "@/lib/api";

// Admin avatar with working dropdown: profile info, change photo,
// change password, sign out. Used by AdminEShell and the two pages
// (Dashboard, Bidding Ops) that render their own top bar.
export default function AdminAvatarMenu() {
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const [me, setMe] = useState(null);
  const [showPw, setShowPw] = useState(false);
  const [cur, setCur] = useState("");
  const [next, setNext] = useState("");
  const [busy, setBusy] = useState(false);
  const wrapRef = useRef(null);
  const fileRef = useRef(null);

  useEffect(() => {
    adminApi.me().then(setMe).catch(() => {});
  }, []);

  useEffect(() => {
    if (!open) return;
    const onDoc = (e) => { if (wrapRef.current && !wrapRef.current.contains(e.target)) setOpen(false); };
    const onEsc = (e) => { if (e.key === "Escape") { setOpen(false); setShowPw(false); } };
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    return () => { document.removeEventListener("mousedown", onDoc); document.removeEventListener("keydown", onEsc); };
  }, [open]);

  const email = me?.email || "Admin";
  const initial = (email[0] || "A").toUpperCase();
  const avatar = me?.avatar_data_url;

  const onPhoto = (e) => {
    const f = e.target.files?.[0];
    if (!f) return;
    if (f.size > 400 * 1024) { toast.error("Photo must be under 400 KB"); return; }
    const reader = new FileReader();
    reader.onload = async () => {
      try {
        await adminApi.uploadAvatar(reader.result);
        setMe((m) => ({ ...m, avatar_data_url: reader.result }));
        toast.success("Profile photo updated");
      } catch (err) { showApiError(err); }
    };
    reader.readAsDataURL(f);
    e.target.value = "";
  };

  const onRemovePhoto = async () => {
    try {
      await adminApi.removeAvatar();
      setMe((m) => ({ ...m, avatar_data_url: null }));
      toast.success("Photo removed");
    } catch (err) { showApiError(err); }
  };

  const onChangePw = async (e) => {
    e.preventDefault();
    if (next.length < 8) { toast.error("New password must be at least 8 characters"); return; }
    setBusy(true);
    try {
      await adminApi.changePassword(cur, next);
      toast.success("Password changed");
      setShowPw(false); setCur(""); setNext("");
    } catch (err) { showApiError(err); }
    finally { setBusy(false); }
  };

  const onSignOut = async () => {
    try { await adminApi.logout(); } catch {}
    navigate("/admin/login", { replace: true });
  };

  return (
    <div ref={wrapRef} style={{ position: "relative" }}>
      <button
        type="button"
        className="pmc-avatar"
        title={email}
        aria-haspopup="menu"
        aria-expanded={open}
        data-testid="admin-avatar-btn"
        onClick={() => setOpen((o) => !o)}
        style={{ cursor: "pointer", border: "none", padding: 0, overflow: "hidden" }}
      >
        {avatar ? <img src={avatar} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : initial}
      </button>
      {open && (
        <div role="menu" data-testid="admin-avatar-menu" style={{
          position: "absolute", right: 0, top: "calc(100% + 8px)", width: 260, zIndex: 60,
          background: "var(--surface)", border: "1px solid var(--line)", borderRadius: "var(--radius-md)",
          boxShadow: "var(--shadow-2)", padding: "8px", display: "grid", gap: 2,
        }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", padding: "10px 10px 12px", borderBottom: "1px solid var(--line)", marginBottom: 6 }}>
            <span className="pmc-avatar" style={{ overflow: "hidden", flex: "none" }}>
              {avatar ? <img src={avatar} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : initial}
            </span>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 14, maxWidth: 150, display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} data-testid="avatar-email">{email}</div>
              <div className="pmc-muted" style={{ fontSize: 12 }}>Administrator</div>
            </div>
          </div>
          <input ref={fileRef} type="file" accept="image/*" hidden onChange={onPhoto} data-testid="avatar-file-input" />
          <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ justifyContent: "flex-start" }} data-testid="avatar-change-photo" onClick={() => fileRef.current?.click()}>Change photo</button>
          {avatar && <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ justifyContent: "flex-start" }} data-testid="avatar-remove-photo" onClick={onRemovePhoto}>Remove photo</button>}
          <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ justifyContent: "flex-start" }} data-testid="avatar-change-password" onClick={() => { setShowPw((s) => !s); }}>Change password</button>
          {showPw && (
            <form onSubmit={onChangePw} data-testid="avatar-pw-form" style={{ display: "grid", gap: 6, padding: "8px 4px" }}>
              <input type="password" required placeholder="Current password" value={cur} onChange={(e) => setCur(e.target.value)} data-testid="avatar-pw-current"
                style={{ padding: "8px 10px", border: "1px solid var(--line-strong)", borderRadius: "var(--radius-sm)", fontSize: 13 }} />
              <input type="password" required minLength={8} placeholder="New password (min 8)" value={next} onChange={(e) => setNext(e.target.value)} data-testid="avatar-pw-new"
                style={{ padding: "8px 10px", border: "1px solid var(--line-strong)", borderRadius: "var(--radius-sm)", fontSize: 13 }} />
              <button type="submit" className="pmc-btn pmc-btn--primary pmc-btn--sm" disabled={busy} data-testid="avatar-pw-save">{busy ? "Saving…" : "Save password"}</button>
            </form>
          )}
          <div style={{ borderTop: "1px solid var(--line)", marginTop: 6, paddingTop: 6 }}>
            <button type="button" className="pmc-btn pmc-btn--ghost pmc-btn--sm" style={{ justifyContent: "flex-start", color: "var(--danger)" }} data-testid="avatar-sign-out" onClick={onSignOut}>Sign out</button>
          </div>
        </div>
      )}
    </div>
  );
}
