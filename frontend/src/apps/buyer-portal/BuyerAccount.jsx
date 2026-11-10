import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { useBuyer } from "./BuyerChrome";
import { BuyerProfileFields, profileReady, profileBody } from "./BuyerProfileFields";
import { buyerApi, day } from "@/lib/buyerApi";
import { showApiError } from "@/lib/api";
import PasswordInput from "@/components/PasswordInput";

function PasswordBox() {
  const [f, setF] = useState({ current_password: "", new_password: "", confirm: "" });
  const ok = f.current_password && f.new_password.length >= 8 && f.new_password === f.confirm;
  const save = () => buyerApi.password({ current_password: f.current_password, new_password: f.new_password })
    .then(() => { toast.success("Password changed"); setF({ current_password: "", new_password: "", confirm: "" }); }).catch(showApiError);
  return (
    <div id="password" className="pmc-panel p-4 mt-6 grid gap-3 max-w-md" data-testid="buyer-password-box">
      <h2 className="font-semibold">Change password</h2>
      <PasswordInput value={f.current_password} onChange={(e) => setF({ ...f, current_password: e.target.value })} placeholder="Current password" data-testid="buyer-pw-current" />
      <PasswordInput value={f.new_password} onChange={(e) => setF({ ...f, new_password: e.target.value })} placeholder="New password (8+ characters)" data-testid="buyer-pw-new" />
      <PasswordInput value={f.confirm} onChange={(e) => setF({ ...f, confirm: e.target.value })} placeholder="Repeat new password" data-testid="buyer-pw-confirm" />
      {f.confirm && f.confirm !== f.new_password && <p className="text-xs text-red-700">The new passwords don't match.</p>}
      <button className="pmc-btn pmc-btn--primary" disabled={!ok} onClick={save} data-testid="buyer-pw-save">Change password</button>
      <a className="text-xs underline" href="/forgot-password?portal=buyer" data-testid="buyer-pw-forgot">Forgot your current password?</a>
    </div>);
}

export function BuyerProfile() {
  const { me, setMe } = useBuyer();
  const [f, setF] = useState({ ...me.profile, name: me.profile?.name || me.name });
  useEffect(() => { if (window.location.hash === "#password") document.getElementById("password")?.scrollIntoView(); }, []);
  const save = () => buyerApi.updateMe(profileBody(f)).then((r) => { setMe({ ...me, ...r }); toast.success("Profile saved"); }).catch(showApiError);
  return (
    <div data-testid="buyer-profile">
      <h1 className="text-2xl font-semibold mb-1">Profile & security</h1>
      <p className="text-sm opacity-70 mb-4">Sign-in email: <b>{me.email}</b>. Fields marked * are required.</p>
      <div className="pmc-panel p-4"><BuyerProfileFields f={f} set={setF} prefix="buyer-prof" />
        <button className="pmc-btn pmc-btn--primary mt-4" disabled={!profileReady(f)} onClick={save} data-testid="buyer-prof-save">Save profile</button></div>
      <PasswordBox />
    </div>);
}

function InviteForm({ onDone }) {
  const [f, setF] = useState({ name: "", email: "", phone: "" });
  const ok = f.name.trim().length > 1 && /\S+@\S+\.\S+/.test(f.email) && f.phone.replace(/\D/g, "").length >= 6;
  const go = () => buyerApi.invite(f).then(() => { toast.success("Invite sent to PMC for approval"); setF({ name: "", email: "", phone: "" }); onDone(); }).catch(showApiError);
  return (
    <div className="pmc-panel p-4 grid sm:grid-cols-4 gap-2 items-end" data-testid="buyer-invite-form">
      <input className="pmc-input" placeholder="Colleague's name *" value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="buyer-invite-name" />
      <input className="pmc-input" type="email" placeholder="Work email *" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="buyer-invite-email" />
      <input className="pmc-input" inputMode="tel" placeholder="Mobile *" value={f.phone} onChange={(e) => setF({ ...f, phone: e.target.value.replace(/[^0-9 -]/g, "") })} data-testid="buyer-invite-phone" />
      <button className="pmc-btn pmc-btn--primary" disabled={!ok} onClick={go} data-testid="buyer-invite-send">Invite</button>
    </div>);
}

export function BuyerTeam() {
  const { me } = useBuyer();
  const [d, setD] = useState(null);
  const load = useCallback(() => buyerApi.team().then(setD).catch(showApiError), []);
  useEffect(() => { load(); }, [load]);
  const rm = (id, label) => { if (window.confirm(`Remove ${label}? They will lose access immediately.`)) buyerApi.remove(id).then(() => { toast.success("Removed"); load(); }).catch(showApiError); };
  const admin = me.verified && me.is_org_admin;
  if (!d) return null;
  return (
    <div data-testid="buyer-team">
      <h1 className="text-2xl font-semibold mb-1">My team</h1>
      <p className="text-sm opacity-70 mb-4">For safety, every colleague you invite is checked and approved by PMC before they can sign in. Removing someone takes effect at once.</p>
      {admin ? <InviteForm onDone={load} /> : <p className="text-sm pmc-panel p-3" data-testid="buyer-team-readonly">{me.verified ? "Only your organisation's main buyer can invite or remove colleagues." : "You can invite colleagues once PMC has verified your organisation."}</p>}
      <h2 className="font-semibold mt-6 mb-2">Members</h2>
      <div className="grid gap-2">{d.members.map((m) => (
        <div key={m.id} className="pmc-panel p-3 text-sm flex gap-3 items-center" data-testid={`buyer-member-${m.id}`}>
          <span className="flex-1"><b>{m.name}</b> · {m.email}{m.is_org_admin ? " · main buyer" : ""}{m.me ? " (you)" : ""}{!m.is_active ? " · removed" : ""}</span>
          {admin && !m.me && m.is_active && <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => rm(m.id, m.name)} data-testid={`buyer-member-remove-${m.id}`}>Remove</button>}
        </div>))}</div>
      <h2 className="font-semibold mt-6 mb-2">Invites</h2>
      {!d.requests.length && <p className="text-sm opacity-60" data-testid="buyer-invites-empty">No invites yet.</p>}
      <div className="grid gap-2">{d.requests.map((r) => (
        <div key={r.id} className="pmc-panel p-3 text-sm flex gap-3 items-center" data-testid={`buyer-invite-${r.id}`}>
          <span className="flex-1">{r.name} · {r.email} · {day(r.created_at)}</span>
          <span className="text-xs uppercase" data-testid={`buyer-invite-status-${r.id}`}>{r.status === "pending" ? "waiting for PMC" : r.status}</span>
          {admin && r.status === "pending" && <button className="pmc-btn pmc-btn--secondary pmc-btn--sm" onClick={() => rm(r.id, r.email)} data-testid={`buyer-invite-cancel-${r.id}`}>Cancel</button>}
        </div>))}</div>
    </div>);
}
