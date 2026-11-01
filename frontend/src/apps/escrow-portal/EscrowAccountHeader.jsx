/**
 * EscrowHeaderActions — v56. Top-bar actions for the escrow institution
 * portal, rendered inside PortalShellE's .pmc-atop bar so it sits next to the
 * shared hamburger and matches the admin console shell exactly. Carries the
 * notifications bell with unread badge and an avatar dropdown (Change profile ·
 * Change password · Sign out). Sign-out routes to /login.
 *
 * Previously this exported a full dark <header> with its own brand lockup;
 * that produced a second header + fixed sidebar that did not collapse on
 * mobile. The shell now owns the chrome; this only contributes the right-hand
 * actions.
 */
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, showApiError } from "@/lib/api";
import { toast } from "sonner";
import PortalAvatarMenu from "@/apps/shared/PortalAvatarMenu";
import PasswordInput from "@/components/PasswordInput";

export default function EscrowHeaderActions({ account, onProfileUpdated }) {
  const nav = useNavigate();
  const [notifsOpen, setNotifsOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unread, setUnread] = useState(account?.unread_notifications || 0);
  const [modal, setModal] = useState(null); // 'profile' | 'password' | null
  const bellRef = useRef(null);

  const refreshNotifications = async () => {
    try {
      const r = await api.get("/api/v1/escrow-accounts/me/notifications");
      setNotifications(r.data);
      setUnread(r.data.filter((n) => !n.read).length);
    } catch (e) { /* silent — polled */ }
  };

  useEffect(() => {
    refreshNotifications();
    const t = setInterval(refreshNotifications, 30000);
    const close = (e) => {
      if (bellRef.current && !bellRef.current.contains(e.target)) setNotifsOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => { clearInterval(t); document.removeEventListener("mousedown", close); };
  }, []);

  const markAllRead = async () => {
    try {
      await api.post("/api/v1/escrow-accounts/me/notifications/mark-all-read");
      refreshNotifications();
    } catch (e) { showApiError(e); }
  };

  const signOut = async () => {
    try { await api.post("/api/v1/escrow-accounts/auth/logout"); } catch (e) { /* ignore */ }
    toast.success("Signed out");
    nav("/login");
  };

  const initials = (account?.legal_name || account?.email || "?")
    .split(/\s+/).slice(0, 2).map((s) => s[0]).join("").toUpperCase();

  return (
    <>
      <div className="pmc-atop__r">
        {/* Notifications bell */}
        <div style={{ position: "relative" }} ref={bellRef}>
          <button type="button" onClick={() => setNotifsOpen((o) => !o)}
                  data-testid="escrow-notif-bell" aria-label="Notifications"
                  style={{ width: 40, height: 40, display: "grid", placeItems: "center",
                           borderRadius: "var(--radius-sm)", border: "1px solid var(--line)",
                           background: "var(--surface)", color: "var(--ink)", cursor: "pointer",
                           position: "relative" }}>
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor"
                 strokeWidth="2" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
              <path d="M6 8a6 6 0 0 1 12 0c0 7 3 9 3 9H3s3-2 3-9" />
              <path d="M10 21a2 2 0 0 0 4 0" />
            </svg>
            {unread > 0 && (
              <span data-testid="escrow-notif-badge"
                    style={{ position: "absolute", top: -4, right: -4, background: "var(--brass-on-chrome)",
                             color: "var(--on-brass)", fontSize: 10, fontWeight: 700, borderRadius: 999,
                             padding: "1px 5px", lineHeight: "14px" }}>
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </button>
          {notifsOpen && (
            <div data-testid="escrow-notif-dropdown"
                 style={{ position: "absolute", right: 0, top: "calc(100% + 8px)", width: 320, maxWidth: "90vw",
                          background: "var(--surface)", color: "var(--ink)", border: "1px solid var(--line)",
                          borderRadius: "var(--radius-md)", boxShadow: "0 20px 50px rgba(0,0,0,.25)",
                          zIndex: 60, overflow: "hidden" }}>
              <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between",
                            padding: "10px 14px", borderBottom: "1px solid var(--line)" }}>
                <div style={{ fontSize: 11, textTransform: "uppercase", letterSpacing: "0.12em", color: "var(--ink-muted)" }}>
                  Notifications
                </div>
                {unread > 0 && (
                  <button type="button" onClick={markAllRead} data-testid="escrow-notif-mark-all"
                          style={{ fontSize: 11, color: "var(--ink-muted)", background: "none", border: "none",
                                   cursor: "pointer", textDecoration: "underline" }}>
                    Mark all read
                  </button>
                )}
              </div>
              <div style={{ maxHeight: 320, overflow: "auto" }}>
                {notifications.length === 0 && (
                  <div style={{ padding: "18px 14px", fontSize: 12, color: "var(--ink-subtle)" }}>
                    No notifications yet. We'll ping you here when PMC reviews your registration.
                  </div>
                )}
                {notifications.map((n) => (
                  <div key={n.id} data-testid={`escrow-notif-item-${n.id}`}
                       style={{ padding: "12px 14px", borderBottom: "1px solid var(--line)",
                                background: n.read ? "transparent" : "var(--primary-soft)" }}>
                    <div style={{ fontWeight: 600, fontSize: 14 }}>{n.title}</div>
                    <div style={{ fontSize: 12, color: "var(--ink-muted)", marginTop: 2 }}>{n.body}</div>
                    <div style={{ fontSize: 10, color: "var(--ink-subtle)", marginTop: 4 }}>
                      {new Date(n.created_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Avatar menu */}
        <PortalAvatarMenu
          initial={initials}
          title={account?.email}
          sub={account?.institution?.status || "draft"}
          items={[
            { label: "Change profile", onClick: () => setModal("profile"), testid: "escrow-menu-profile" },
            { label: "Change password", onClick: () => setModal("password"), testid: "escrow-menu-password" },
            { label: "Sign out", onClick: signOut, danger: true, testid: "escrow-menu-signout" },
          ]}
          testId="escrow-avatar-button"
        />
      </div>

      {modal === "profile" && (
        <ProfileModal account={account} onClose={() => setModal(null)} onSaved={onProfileUpdated} />
      )}
      {modal === "password" && (
        <PasswordModal onClose={() => setModal(null)} />
      )}
    </>
  );
}


function ProfileModal({ account, onClose, onSaved }) {
  const [legal, setLegal] = useState(account?.legal_name || "");
  const [phone, setPhone] = useState(account?.primary_contact_phone || "");
  const [busy, setBusy] = useState(false);

  const save = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await api.patch("/api/v1/escrow-accounts/me/profile", {
        legal_name: legal.trim(),
        primary_contact_phone: phone.trim(),
      });
      toast.success("Profile updated");
      onSaved?.(r.data);
      onClose();
    } catch (err) { showApiError(err); }
    finally { setBusy(false); }
  };

  return (
    <Modal title="Change profile" onClose={onClose} testId="escrow-profile-modal">
      <form onSubmit={save} className="space-y-4">
        <ModalField label="Legal entity name">
          <input className="w-full px-3 py-2 border border-brand-navy/20"
                 data-testid="escrow-profile-name"
                 value={legal} onChange={(e) => setLegal(e.target.value)} />
        </ModalField>
        <ModalField label="Primary contact phone">
          <input className="w-full px-3 py-2 border border-brand-navy/20"
                 data-testid="escrow-profile-phone"
                 value={phone} onChange={(e) => setPhone(e.target.value)} />
        </ModalField>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose}
                  className="px-4 py-2 text-xs uppercase tracking-widest border border-brand-navy/20 text-brand-navy">
            Cancel
          </button>
          <button type="submit" disabled={busy}
                  data-testid="escrow-profile-save"
                  className="px-4 py-2 text-xs uppercase tracking-widest bg-brand-navy text-white disabled:opacity-50">
            {busy ? "Saving…" : "Save"}
          </button>
        </div>
      </form>
    </Modal>
  );
}


function PasswordModal({ onClose }) {
  const [cur, setCur] = useState("");
  const [np, setNp] = useState("");
  const [c2, setC2] = useState("");
  const [busy, setBusy] = useState(false);

  const save = async (e) => {
    e.preventDefault();
    if (np.length < 8) return toast.error("New password must be at least 8 characters");
    if (np !== c2) return toast.error("Passwords don't match");
    setBusy(true);
    try {
      await api.post("/api/v1/escrow-accounts/auth/change-password",
                      { current_password: cur, new_password: np });
      toast.success("Password updated");
      onClose();
    } catch (err) { showApiError(err); }
    finally { setBusy(false); }
  };

  return (
    <Modal title="Change password" onClose={onClose} testId="escrow-password-modal">
      <form onSubmit={save} className="space-y-4">
        <ModalField label="Current password">
          <PasswordInput type="password" className="w-full px-3 py-2 border border-brand-navy/20"
                 data-testid="escrow-pwd-current"
                 value={cur} onChange={(e) => setCur(e.target.value)} />
        </ModalField>
        <ModalField label="New password">
          <PasswordInput type="password" className="w-full px-3 py-2 border border-brand-navy/20"
                 data-testid="escrow-pwd-new"
                 value={np} onChange={(e) => setNp(e.target.value)} />
        </ModalField>
        <ModalField label="Confirm new password">
          <PasswordInput type="password" className="w-full px-3 py-2 border border-brand-navy/20"
                 data-testid="escrow-pwd-confirm"
                 value={c2} onChange={(e) => setC2(e.target.value)} />
        </ModalField>
        <div className="flex justify-end gap-2 pt-2">
          <button type="button" onClick={onClose}
                  className="px-4 py-2 text-xs uppercase tracking-widest border border-brand-navy/20 text-brand-navy">
            Cancel
          </button>
          <button type="submit" disabled={busy}
                  data-testid="escrow-pwd-save"
                  className="px-4 py-2 text-xs uppercase tracking-widest bg-brand-navy text-white disabled:opacity-50">
            {busy ? "Saving…" : "Update password"}
          </button>
        </div>
      </form>
    </Modal>
  );
}


function Modal({ title, onClose, children, testId }) {
  return (
    <div className="fixed inset-0 z-50 bg-black/50 flex items-center justify-center p-4"
         data-testid={testId} onClick={onClose}>
      <div className="bg-white text-brand-navy w-full max-w-md"
           onClick={(e) => e.stopPropagation()}>
        <div className="px-4 py-3 border-b border-brand-navy/10 flex items-center justify-between">
          <div className="font-semibold">{title}</div>
          <button type="button" onClick={onClose}
                  className="text-brand-navy/60 hover:text-brand-navy">×</button>
        </div>
        <div className="px-5 py-4">{children}</div>
      </div>
    </div>
  );
}

function ModalField({ label, children }) {
  return (
    <label className="block">
      <span className="block text-[11px] uppercase tracking-widest text-brand-navy/70 mb-1">
        {label}
      </span>
      {children}
    </label>
  );
}
