import { useEffect, useState } from "react";
import { toast } from "sonner";
import { agentApi, showApiError } from "@/lib/api";

const inp = "mt-1 block w-full px-3 py-2 border border-brand-navy/20 bg-white text-sm";
const ACCESS = { awaiting_consent: "Waiting for supplier consent", granted: "Consent given", self_fill: "Supplier filling it themselves — you stay linked", declined: "Supplier declined", revoked: "Access removed by supplier" };
const STAGE = { invited: "Invited", consented: "Ready to fill", filling: "Filling in", self_fill: "Supplier completing", ready_for_review: "With supplier for review", submitted: "Submitted to PMC", declined: "Declined", revoked: "Revoked", claim_released: "Released" };

const InviteForm = ({ onDone }) => {
  const [f, setF] = useState({ company_name: "", email: "", mobile: "" });
  const [busy, setBusy] = useState(false);
  const go = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      const r = await agentApi.inviteSupplier(f);
      (r.email_sent ? toast.success : toast.warning)(r.email_sent ? "Invitation emailed to the supplier" : "Supplier added, but the email did not send — use Resend");
      setF({ company_name: "", email: "", mobile: "" }); onDone();
    } catch (err) { showApiError(err); } finally { setBusy(false); }
  };
  const fld = (k, l, type = "text") => <label className="text-sm flex-1 min-w-[180px]">{l}<input type={type} required className={inp} value={f[k]} onChange={(e) => setF({ ...f, [k]: e.target.value })} data-testid={`ps-invite-${k}`} /></label>;
  return (
    <form onSubmit={go} className="bg-white border border-brand-navy/15 p-4 space-y-3" data-testid="ps-invite-form">
      <div className="font-semibold">Invite a supplier</div>
      <p className="text-xs text-brand-navy/60">The supplier gets an email showing your name and partner code. You can fill their form only after they confirm their email and give consent.</p>
      <div className="flex gap-3 flex-wrap">{fld("company_name", "Company name")}{fld("email", "Supplier email", "email")}{fld("mobile", "Mobile (with country code)", "tel")}</div>
      <button className="pmc-btn pmc-btn--primary" disabled={busy} data-testid="ps-invite-submit">{busy ? "Sending…" : "Send invitation"}</button>
    </form>
  );
};

const Row = ({ r, reload }) => {
  const run = (fn, ok) => fn().then(() => { toast.success(ok); reload(); }).catch(showApiError);
  const resend = () => agentApi.resendSupplier(r.id).then((x) => (x.email_sent ? toast.success("Invitation resent") : toast.warning("Invitation email did not send"))).catch(showApiError);
  const open = () => agentApi.supplierEditLink(r.id).then((x) => { window.open(x.path, "_blank"); reload(); }).catch(showApiError);
  const editable = r.partner_access === "granted" && ["draft", "needs_clarification"].includes(r.status);
  return (
    <div className="p-3 flex justify-between gap-3 flex-wrap items-center" data-testid={`ps-row-${r.id}`}>
      <div><div className="font-semibold text-sm">{r.company_name}</div>
        <div className="text-xs text-brand-navy/60">{r.email} · {r.mobile}{r.vendor_ref ? ` · ${r.vendor_ref}` : ""}</div>
        <div className="text-xs mt-1"><span data-testid={`ps-access-${r.id}`}>{ACCESS[r.partner_access] || r.partner_access}</span> · <b data-testid={`ps-stage-${r.id}`}>{r.status === "approved" ? "Approved by PMC" : r.status === "rejected" ? "Rejected by PMC" : STAGE[r.partner_stage] || r.partner_stage}</b>{r.edits ? ` · ${r.edits} edit${r.edits === 1 ? "" : "s"} logged` : ""}</div></div>
      <div className="flex gap-2 flex-wrap">
        {r.partner_access === "awaiting_consent" && <button className="pmc-btn pmc-btn--secondary" onClick={resend} data-testid={`ps-resend-${r.id}`}>Resend</button>}
        {editable && <button className="pmc-btn pmc-btn--secondary" onClick={open} data-testid={`ps-fill-${r.id}`}>Fill form</button>}
        {editable && <button className="pmc-btn pmc-btn--primary" onClick={() => run(() => agentApi.sendForReview(r.id), "Sent to the supplier for review")} data-testid={`ps-review-${r.id}`}>Send to supplier for review</button>}
      </div>
    </div>
  );
};

export default function PartnerSuppliers() {
  const [rows, setRows] = useState(null);
  const [code, setCode] = useState("");
  const load = () => agentApi.suppliers().then((r) => setRows(r.items || [])).catch(showApiError);
  useEffect(() => { load(); agentApi.me().then((a) => setCode(a.partner_code || "")).catch(() => {}); }, []);
  const link = code ? `${window.location.origin}/register?partner=${code}` : "";
  const copy = () => navigator.clipboard.writeText(link).then(() => toast.success("Link copied")).catch(() => toast.info(link));
  return (
    <div className="space-y-4" data-testid="partner-suppliers">
      {link && <div className="bg-white border border-brand-gold p-4 space-y-2" data-testid="ps-referral">
        <div className="font-semibold">Your personal sign-up link</div>
        <p className="text-xs text-brand-navy/60">Share it on WhatsApp, email or social media. Suppliers who register through it fill the form themselves and are linked to your code {code} automatically.</p>
        <div className="flex gap-2 flex-wrap"><input readOnly className="flex-1 min-w-[240px] px-3 py-2 border border-brand-navy/20 text-sm font-mono" value={link} data-testid="ps-referral-link" />
          <button type="button" className="pmc-btn pmc-btn--secondary" onClick={copy} data-testid="ps-referral-copy">Copy link</button>
          <a className="pmc-btn pmc-btn--secondary" href={`https://wa.me/?text=${encodeURIComponent(`Register as a supplier on PMC Managers: ${link}`)}`} target="_blank" rel="noreferrer" data-testid="ps-referral-whatsapp">Share on WhatsApp</a></div>
      </div>}
      <InviteForm onDone={load} />
      <div className="bg-white border border-brand-navy/15 divide-y" data-testid="ps-list">
        {(rows || []).map((r) => <Row key={r.id} r={r} reload={load} />)}
        {rows && !rows.length && <div className="p-6 text-sm text-center text-brand-navy/60" data-testid="ps-empty">No suppliers yet — invite your first one above.</div>}
      </div>
    </div>
  );
}
