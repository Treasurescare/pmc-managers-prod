/**
 * EscrowAccountHeader — v52d. Shared header used by the account dashboard
 * and the registration wizard. Carries the brand lockup on the left,
 * a notification bell with unread badge, and an avatar menu
 * (Change password · Change profile · Sign out). Sign-out routes to
 * /login — the unified PMC Managers sign-in page.
 */
import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api, showApiError } from "@/lib/api";
import { toast } from "sonner";

export default function EscrowAccountHeader({ account, onProfileUpdated }) {
  const nav = useNavigate();
  const [notifsOpen, setNotifsOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const [notifications, setNotifications] = useState([]);
  const [unread, setUnread] = useState(account?.unread_notifications || 0);
  const [modal, setModal] = useState(null); // 'profile' | 'password' | null

  const bellRef = useRef(null);
  const avatarRef = useRef(null);

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
      if (avatarRef.current && !avatarRef.current.contains(e.target)) setMenuOpen(false);
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
    try {
      await api.post("/api/v1/escrow-accounts/auth/logout");
    } catch (e) { /* ignore */ }
    toast.success("Signed out");
    nav("/login");
  };

  const initials = (account?.legal_name || account?.email || "?")
    .split(/\s+/).slice(0, 2).map((s) => s[0]).join("").toUpperCase();

  return (
    <header className="bg-brand-navy text-white px-6 py-3 flex items-center justify-between"
            data-testid="escrow-account-header">
      <div className="flex items-center gap-3">
        <div className="text-[11px] uppercase tracking-widest text-brand-gold">
          PMC Managers
        </div>
        <div className="text-white/40">·</div>
        <div className="font-serif text-lg">{account?.legal_name || "Escrow institution"}</div>
      </div>

      <div className="flex items-center gap-5">
        {/* Notifications bell (left of avatar) */}
        <div className="relative" ref={bellRef}>
          <button type="button" onClick={() => setNotifsOpen((o) => !o)}
                  data-testid="escrow-notif-bell"
                  className="relative px-2 py-1 hover:text-brand-gold">
            <span className="text-xl">🔔</span>
            {unread > 0 && (
              <span className="absolute -top-1 -right-1 bg-brand-gold text-brand-navy text-[10px] px-1.5 py-0.5 rounded-full font-bold"
                    data-testid="escrow-notif-badge">
                {unread > 9 ? "9+" : unread}
              </span>
            )}
          </button>
          {notifsOpen && (
            <div className="absolute right-0 mt-2 w-80 bg-white text-brand-navy border border-brand-navy/10 shadow-xl z-50"
                 data-testid="escrow-notif-dropdown">
              <div className="flex items-center justify-between px-4 py-2 border-b border-brand-navy/10">
                <div className="text-[11px] uppercase tracking-widest">Notifications</div>
                {unread > 0 && (
                  <button type="button" onClick={markAllRead}
                          data-testid="escrow-notif-mark-all"
                          className="text-[11px] text-brand-navy/60 hover:text-brand-navy underline">
                    Mark all read
                  </button>
                )}
              </div>
              <div className="max-h-80 overflow-auto">
                {notifications.length === 0 && (
                  <div className="px-4 py-6 text-xs text-brand-navy/50">
                    No notifications yet. We'll ping you here when PMC reviews
                    your registration.
                  </div>
                )}
                {notifications.map((n) => (
                  <div key={n.id}
                       data-testid={`escrow-notif-item-${n.id}`}
                       className={"px-4 py-3 border-b border-brand-navy/5 text-sm " +
                                   (n.read ? "" : "bg-brand-pale")}>
                    <div className="font-semibold">{n.title}</div>
                    <div className="text-xs text-brand-navy/70 mt-0.5">{n.body}</div>
                    <div className="text-[10px] text-brand-navy/40 mt-1">
                      {new Date(n.created_at).toLocaleString()}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>

        {/* Avatar menu */}
        <div className="relative" ref={avatarRef}>
          <button type="button" onClick={() => setMenuOpen((o) => !o)}
                  data-testid="escrow-avatar-button"
                  className="flex items-center gap-2 hover:text-brand-gold">
            <div className="w-9 h-9 rounded-full bg-brand-gold text-brand-navy font-bold flex items-center justify-center text-sm">
              {initials}
            </div>
          </button>
          {menuOpen && (
            <div className="absolute right-0 mt-2 w-56 bg-white text-brand-navy border border-brand-navy/10 shadow-xl z-50"
                 data-testid="escrow-avatar-menu">
              <div className="px-4 py-3 border-b border-brand-navy/10">
                <div className="text-xs font-semibold truncate">{account?.email}</div>
                <div className="text-[10px] text-brand-navy/50 uppercase tracking-widest mt-0.5">
                  {account?.institution?.status || "draft"}
                </div>
              </div>
              <button type="button" onClick={() => { setModal("profile"); setMenuOpen(false); }}
                      data-testid="escrow-menu-profile"
                      className="block w-full text-left px-4 py-2 text-sm hover:bg-brand-pale">
                Change profile
              </button>
              <button type="button" onClick={() => { setModal("password"); setMenuOpen(false); }}
                      data-testid="escrow-menu-password"
                      className="block w-full text-left px-4 py-2 text-sm hover:bg-brand-pale">
                Change password
              </button>
              <button type="button" onClick={signOut}
                      data-testid="escrow-menu-signout"
                      className="block w-full text-left px-4 py-2 text-sm hover:bg-brand-pale border-t border-brand-navy/10 text-red-700">
                Sign out
              </button>
            </div>
          )}
        </div>
      </div>

      {modal === "profile" && (
        <ProfileModal account={account} onClose={() => setModal(null)}
                      onSaved={onProfileUpdated} />
      )}
      {modal === "password" && (
        <PasswordModal onClose={() => setModal(null)} />
      )}
    </header>
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
          <input type="password" className="w-full px-3 py-2 border border-brand-navy/20"
                 data-testid="escrow-pwd-current"
                 value={cur} onChange={(e) => setCur(e.target.value)} />
        </ModalField>
        <ModalField label="New password">
          <input type="password" className="w-full px-3 py-2 border border-brand-navy/20"
                 data-testid="escrow-pwd-new"
                 value={np} onChange={(e) => setNp(e.target.value)} />
        </ModalField>
        <ModalField label="Confirm new password">
          <input type="password" className="w-full px-3 py-2 border border-brand-navy/20"
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
