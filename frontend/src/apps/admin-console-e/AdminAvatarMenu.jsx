import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { adminApi, showApiError } from "@/lib/api";

const ROLE_DISPLAY = {
  admin: "Administrator",
  reviewer: "Reviewer",
  escrow_agent: "Escrow Agent",
  certifier: "Site Certifier",
  legal_counsel: "Legal Counsel",
  accounting: "Accounting Team",
  committee_member: "Bid Committee",
  auditor: "Auditor",
  support: "Support",
  management: "Management",
  partner: "Partner",
};

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
  // v51t — anchor the dropdown via a portal to document.body so no
  // ancestor overflow/clip can hide it. We measure the button's rect on
  // open + on resize/scroll so the menu stays glued to the avatar.
  const btnRef = useRef(null);
  const menuRef = useRef(null);
  const fileRef = useRef(null);
  const [anchor, setAnchor] = useState(null);

  useEffect(() => {
    adminApi.me().then(setMe).catch(() => {});
  }, []);

  const place = () => {
    const b = btnRef.current;
    if (!b) return;
    const r = b.getBoundingClientRect();
    const narrow = window.innerWidth <= 767;
    // On narrow screens pin to the right edge (fully inside viewport);
    // on desktop align the menu's right edge to the button's right edge.
    const width = narrow ? Math.min(300, window.innerWidth - 16) : 280;
    const top = narrow ? Math.max(8, r.bottom + 6) : r.bottom + 8;
    const right = narrow ? 8 : Math.max(8, window.innerWidth - r.right);
    setAnchor({ top, right, width });
  };

  useEffect(() => {
    if (!open) return;
    place();
    const onDoc = (e) => {
      if (menuRef.current && menuRef.current.contains(e.target)) return;
      if (btnRef.current && btnRef.current.contains(e.target)) return;
      setOpen(false);
    };
    const onEsc = (e) => { if (e.key === "Escape") { setOpen(false); setShowPw(false); } };
    const onViewportChange = () => place();
    document.addEventListener("mousedown", onDoc);
    document.addEventListener("keydown", onEsc);
    window.addEventListener("resize", onViewportChange);
    window.addEventListener("scroll", onViewportChange, true);
    return () => {
      document.removeEventListener("mousedown", onDoc);
      document.removeEventListener("keydown", onEsc);
      window.removeEventListener("resize", onViewportChange);
      window.removeEventListener("scroll", onViewportChange, true);
    };
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
    navigate("/login", { replace: true });
  };

  return (
    <div style={{ position: "relative" }}>
      <button
        ref={btnRef}
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
      {open && anchor && createPortal(
        <div ref={menuRef} role="menu" data-testid="admin-avatar-menu" className="pmc-avatar-menu" style={{
          position: "fixed", top: anchor.top, right: anchor.right, width: anchor.width,
          maxHeight: `calc(100vh - ${anchor.top + 16}px)`, overflowY: "auto", zIndex: 2000,
          background: "var(--surface, #fff)", border: "1px solid var(--line, #0001)",
          borderRadius: "var(--radius-md, 6px)", boxShadow: "0 20px 50px rgba(0,0,0,.25)",
          padding: 8, display: "grid", gap: 2,
        }}>
          <div style={{ display: "flex", gap: 10, alignItems: "center", padding: "10px 10px 12px", borderBottom: "1px solid var(--line)", marginBottom: 6 }}>
            <span className="pmc-avatar" style={{ overflow: "hidden", flex: "none" }}>
              {avatar ? <img src={avatar} alt="" style={{ width: "100%", height: "100%", objectFit: "cover" }} /> : initial}
            </span>
            <div style={{ minWidth: 0 }}>
              <div style={{ fontWeight: 600, fontSize: 14, maxWidth: 150, display: "block", overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }} data-testid="avatar-email">{email}</div>
              <div className="pmc-muted" style={{ fontSize: 12 }}>
                {ROLE_DISPLAY[me?.role] || ROLE_DISPLAY[me?.active_role] || (me?.role ? me.role : "Staff")}
              </div>
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
        </div>,
        document.body,
      )}
    </div>
  );
}
