import { useEffect, useState } from "react";
import { toast } from "sonner";
import AdminEShell from "./AdminEShell";
import { agentApi, uploadsApi, showApiError } from "@/lib/api";
import { AdminLeaderboardCard, CommissionSettingsCard, PartnerWalletAdmin } from "./PartnerCommissionAdmin";
import AdminPartnerEditor from "./AdminPartnerEditor";

const inp = "px-3 py-2 border border-brand-navy/20 bg-white text-sm";

const resendMsg = (x) => (x.email_sent ? toast.success(x.kind === "reminder" ? "Reminder emailed — they can sign in and finish their profile" : "Invitation link emailed")
  : toast.error(`Email did not send. ${x.email_error || ""}`, { duration: 15000 }));

const Detail = ({ id, onChanged, partners }) => {
  const [a, setA] = useState(null);
  const [editing, setEditing] = useState(false);
  const [note, setNote] = useState("");
  const [waive, setWaive] = useState(false);
  const load = () => agentApi.adminGet(id).then(setA).catch(showApiError);
  useEffect(() => { load(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!a) return null;
  const act = async (action) => {
    try {
      const r = await agentApi.decide(id, action, note, waive);
      const msg = { approve: "Partner approved", reject: "Partner rejected", clarify: "Changes requested", suspend: "Partner suspended",
        request_payment: r.email_sent ? "Payment request emailed" : "Payment request created — email did not send" }[action];
      (action === "request_payment" && !r.email_sent ? toast.warning : toast.success)(msg);
      setNote(""); load(); onChanged();
    } catch (e) { showApiError(e); }
  };
  const F = ({ k, l }) => <div><div className="text-[10px] uppercase tracking-widest text-brand-navy/60">{l}</div><div className="text-sm">{a[k] || "—"}</div></div>;
  return (
    <div className="bg-white border border-brand-navy/15 p-4 space-y-4" data-testid={`admin-agent-detail-${id}`}>
      {["draft", "needs_clarification", "invited"].includes(a.status) && <div className="text-sm bg-amber-50 border border-amber-200 p-2" data-testid="admin-agent-status-note">
        {a.status === "invited" ? "Invitation sent — the partner hasn't confirmed their email and set a password yet." : "The partner has signed in but hasn't finished and submitted their profile yet. Send a reminder, or fill in the details you have."}</div>}
      {a.status !== "rejected" && <div className="flex gap-2 flex-wrap">
        <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => setEditing(!editing)} data-testid="admin-agent-edit-toggle">{editing ? "Close editing" : "Edit details"}</button>
        {["draft", "needs_clarification", "invited"].includes(a.status) && <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => agentApi.resend(id).then(resendMsg).catch(showApiError)} data-testid="admin-agent-detail-resend">{a.status === "invited" ? "Resend invitation link" : "Send reminder to finish profile"}</button>}
      </div>}
      {editing && <AdminPartnerEditor a={a} onSaved={() => { load(); onChanged(); }} onClose={() => setEditing(false)} />}
      <div className="grid md:grid-cols-3 gap-3">
        <F k="entity_type" l="Type" /><F k="legal_name" l="Name" /><F k="email" l="Email" /><F k="primary_contact_phone" l="Phone" />
        <F k="country" l="Country" /><F k="city" l="City" /><F k="address_line1" l="Address" /><F k="postal_code" l="Postcode" /><F k="reg_number" l="Registration no." />
      </div>
      <div><div className="pmc-label">Banking</div>{(a.banking || []).map((b, i) => <div key={i} className="text-sm">{[b.institution_name, b.account_name, b.account_number || b.iban, b.swift, b.currency].filter(Boolean).join(" · ")}</div>)}</div>
      <div><div className="pmc-label">Documents</div><div className="flex gap-2 flex-wrap">
        {Object.entries(a.documents || {}).map(([slot, d]) => <button key={slot} type="button" className="px-2 py-1 text-xs border" onClick={() => uploadsApi.openFile(d.key).catch(showApiError)} data-testid={`admin-agent-doc-${slot}`}>{slot.replace(/_/g, " ")}</button>)}
      </div></div>
      <div className="text-sm" data-testid="admin-agent-agreement">{a.agreement ? <>Agreement {a.agreement.version} signed by <b>{a.agreement.signer_name}</b> on {a.agreement.signed_at.slice(0, 16).replace("T", " ")} UTC (IP {a.agreement.ip || "—"})</> : "Agreement not signed"}</div>
      {a.partner_code && <div className="text-sm" data-testid="admin-agent-code">Partner code <b>{a.partner_code}</b>{a.fee_waived ? " · fee waived" : ""}</div>}
      {a.public_profile?.show && <div className="text-sm flex gap-2 items-center flex-wrap" data-testid="admin-agent-public-profile">Homepage card: "{a.public_profile.bio || "no bio"}"{a.public_profile.hidden ? " · hidden by PMC" : ""}
        <button type="button" className="px-2 py-0.5 text-xs border" onClick={() => agentApi.hidePublicProfile(id, !a.public_profile.hidden).then(() => { toast.success(a.public_profile.hidden ? "Card shown again" : "Card hidden from homepage"); load(); }).catch(showApiError)} data-testid="admin-agent-hide-profile">{a.public_profile.hidden ? "Show on homepage" : "Hide from homepage"}</button></div>}
      {a.payment && <div className="text-sm" data-testid="admin-agent-payment">Registration fee {a.payment.currency} {Number(a.payment.amount).toLocaleString(undefined, { minimumFractionDigits: 2 })} · <b>{a.payment.status}</b>{a.payment.paid_at ? ` on ${a.payment.paid_at.slice(0, 10)}` : ""}</div>}
      {["submitted", "approved", "needs_clarification", "payment_pending"].includes(a.status) && (
        <div className="space-y-2">
          <textarea className={inp + " w-full"} rows={2} placeholder="Note to the partner (required to reject or ask for changes)" value={note} onChange={(e) => setNote(e.target.value)} data-testid="admin-agent-note" />
          <div className="flex gap-2 flex-wrap">
            {a.status === "submitted" && <>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={waive} onChange={(e) => setWaive(e.target.checked)} data-testid="admin-agent-waive" />Waive registration fee</label>
              {waive ? <button className="pmc-btn pmc-btn--primary" onClick={() => act("approve")} data-testid="admin-agent-approve">Approve (fee waived)</button>
                : <button className="pmc-btn pmc-btn--primary" onClick={() => act("request_payment")} data-testid="admin-agent-request-payment">Send payment request</button>}
              <button className="pmc-btn pmc-btn--secondary" onClick={() => act("clarify")} data-testid="admin-agent-clarify">Ask for changes</button></>}
            {a.status === "payment_pending" && <>
              <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={waive} onChange={(e) => setWaive(e.target.checked)} data-testid="admin-agent-waive-pending" />Waive registration fee</label>
              {waive ? <button className="pmc-btn pmc-btn--primary" onClick={() => act("approve")} data-testid="admin-agent-approve-pending">Approve (fee waived)</button>
                : <button className="pmc-btn pmc-btn--secondary" onClick={() => act("request_payment")} data-testid="admin-agent-resend-payment">Resend payment link</button>}</>}
            {a.status !== "approved" && <button className="pmc-btn pmc-btn--secondary" onClick={() => act("reject")} data-testid="admin-agent-reject">Reject</button>}
            {a.status === "approved" && <button className="pmc-btn pmc-btn--secondary" onClick={() => act("suspend")} data-testid="admin-agent-suspend">Suspend</button>}
          </div>
        </div>)}
      {a.status === "approved" && <PartnerWalletAdmin id={id} partners={partners} />}
    </div>
  );
};

export default function AdminAgentsE() {
  const [rows, setRows] = useState([]);
  const [open, setOpen] = useState(null);
  const [f, setF] = useState({ email: "", name: "" });
  const load = () => agentApi.adminList().then((r) => setRows(r.items || [])).catch(showApiError);
  useEffect(() => { load(); }, []);
  const invite = async (e) => {
    e.preventDefault();
    try {
      const r = await agentApi.invite(f.email, f.name);
      if (r.existing) resendMsg(r);
      else if (r.email_sent) toast.success("Invitation emailed");
      else toast.error(`Partner created but the email did not send. ${r.email_error || ""}`, { duration: 15000 });
      setF({ email: "", name: "" }); load();
    }
    catch (err) { showApiError(err); }
  };
  return (
    <AdminEShell active="Partners" crumb={<>Market / <b>Partners</b></>}>
      <div className="p-6 space-y-5" data-testid="admin-agents-page">
        <CommissionSettingsCard />
        <AdminLeaderboardCard />
        <form onSubmit={invite} className="flex gap-2 flex-wrap items-end bg-white border border-brand-navy/15 p-4" data-testid="admin-agent-invite-form">
          <label className="text-sm">Partner name<input className={inp + " block mt-1"} required value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="admin-agent-invite-name" /></label>
          <label className="text-sm">Email<input type="email" className={inp + " block mt-1"} required value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="admin-agent-invite-email" /></label>
          <button className="pmc-btn pmc-btn--primary" data-testid="admin-agent-invite-submit">Send invitation</button>
        </form>
        <div className="bg-white border border-brand-navy/15 divide-y" data-testid="admin-agents-list">
          {rows.map((r) => (
            <div key={r.id}>
              <div className="flex justify-between items-center p-3 gap-2 flex-wrap">
                <button type="button" className="text-left" onClick={() => setOpen(open === r.id ? null : r.id)} data-testid={`admin-agent-row-${r.id}`}>
                  <div className="font-semibold text-sm">{r.legal_name || r.name}</div><div className="text-xs text-brand-navy/60">{r.email}</div></button>
                <div className="flex gap-2 items-center">
                  <span className="text-[10px] uppercase tracking-widest px-2 py-0.5 border" data-testid={`admin-agent-status-${r.id}`}>{r.status.replace("_", " ")}</span>
                  {["invited", "draft", "needs_clarification"].includes(r.status) && <button className="pmc-btn pmc-btn--secondary" onClick={() => agentApi.resend(r.id).then(resendMsg).catch(showApiError)} data-testid={`admin-agent-resend-${r.id}`}>{r.status === "invited" ? "Resend link" : "Send reminder"}</button>}
                </div>
              </div>
              {open === r.id && <div className="p-3 pt-0"><Detail id={r.id} onChanged={load} partners={rows} /></div>}
            </div>))}
          {!rows.length && <div className="p-6 text-sm text-center text-brand-navy/60" data-testid="admin-agents-empty">No partners yet — send the first invitation above.</div>}
        </div>
      </div>
    </AdminEShell>
  );
}
