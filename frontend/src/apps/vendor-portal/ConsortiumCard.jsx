import { useState } from "react";
import { toast } from "sonner";
import { consortiumApi, uploadsApi, showApiError } from "@/lib/api";

const inp = "border rounded-md px-2 py-1.5 text-sm";
const STATUS = { invited: "Invited", accepted: "Accepted", declined: "Declined" };

const AddMember = ({ c, onChange }) => {
  const [f, setF] = useState({ email_or_ref: "", capability: "", share_pct: "" });
  const add = async () => {
    try { onChange(await consortiumApi.addMember(c.id, { ...f, share_pct: Number(f.share_pct || 0) })); setF({ email_or_ref: "", capability: "", share_pct: "" }); toast.success("Invitation sent"); }
    catch (e) { showApiError(e); }
  };
  return (
    <div className="flex gap-2 flex-wrap items-end" data-testid="cons-add-member">
      <input className={inp} placeholder="Supplier email or PMC supplier ID" value={f.email_or_ref} onChange={(e) => setF({ ...f, email_or_ref: e.target.value })} data-testid="cons-member-email" />
      <input className={inp} placeholder="What they bring (e.g. funding, technology)" value={f.capability} onChange={(e) => setF({ ...f, capability: e.target.value })} data-testid="cons-member-capability" />
      <input className={inp + " w-24"} type="number" placeholder="Share %" value={f.share_pct} onChange={(e) => setF({ ...f, share_pct: e.target.value })} data-testid="cons-member-share" />
      <button type="button" className="px-3 py-1.5 bg-slate-900 text-white rounded-md text-sm" onClick={add} data-testid="cons-member-add">Invite</button>
    </div>);
};

const Terms = ({ c, onChange }) => {
  const [t, setT] = useState({ lead_share_pct: c.lead_share_pct ?? 100, escrow_mode: c.escrow_mode || "", deposit_mode: c.deposit_mode || "",
    shares: Object.fromEntries((c.members || []).map((m) => [m.vendor_id, m.share_pct])) });
  const save = async () => {
    if (!t.escrow_mode || !t.deposit_mode) return toast.error("Choose the escrow and deposit options first");
    try { onChange(await consortiumApi.terms(c.id, { ...t, lead_share_pct: Number(t.lead_share_pct) })); toast.success("Terms saved — members need to sign again"); }
    catch (e) { showApiError(e); }
  };
  return (
    <div className="space-y-2 text-sm" data-testid="cons-terms">
      <div className="flex gap-3 flex-wrap items-end">
        <label>Your share %<input className={inp + " block w-24"} type="number" value={t.lead_share_pct} onChange={(e) => setT({ ...t, lead_share_pct: e.target.value })} data-testid="cons-lead-share" /></label>
        {(c.members || []).filter((m) => m.status !== "declined").map((m) => (
          <label key={m.vendor_id}>{m.company_name} %<input className={inp + " block w-24"} type="number" value={t.shares[m.vendor_id] ?? ""} onChange={(e) => setT({ ...t, shares: { ...t.shares, [m.vendor_id]: Number(e.target.value) } })} data-testid={`cons-share-${m.vendor_id}`} /></label>))}
      </div>
      <div className="flex gap-3 flex-wrap">
        <label>Escrow<select className={inp + " block"} value={t.escrow_mode} onChange={(e) => setT({ ...t, escrow_mode: e.target.value })} data-testid="cons-escrow-mode">
          <option value="" disabled>Choose…</option><option value="shared">One shared escrow, split by shares</option><option value="separate">Separate escrow for each member</option></select></label>
        <label>Bid deposit (EMD)<select className={inp + " block"} value={t.deposit_mode} onChange={(e) => setT({ ...t, deposit_mode: e.target.value })} data-testid="cons-deposit-mode">
          <option value="" disabled>Choose…</option><option value="lead_pays">Lead pays the whole deposit</option><option value="each_pays_share">Each member pays their share</option></select></label>
      </div>
      <button type="button" className="px-3 py-1.5 border rounded-md" onClick={save} data-testid="cons-terms-save">Save terms</button>
    </div>);
};

const Agreement = ({ c, me, onChange }) => {
  const [name, setName] = useState("");
  const [ok, setOk] = useState(false);
  const signed = (c.agreement?.signatures || []);
  const upload = async (file) => {
    try {
      const p = await uploadsApi.presign(file.name, file.type || "application/pdf", "vendor-docs", file.size);
      const r = await uploadsApi.direct(p.key, file);
      onChange(await consortiumApi.uploadAgreement(c.id, { key: r?.key || p.key, filename: file.name })); toast.success("Signed agreement uploaded");
    } catch (e) { showApiError(e); }
  };
  const sign = async () => {
    try { onChange(await consortiumApi.sign(c.id, { signer_name: name, consent: ok })); toast.success("Agreement signed"); } catch (e) { showApiError(e); }
  };
  const iSigned = signed.some((s) => s.vendor_id === me);
  return (
    <div className="space-y-2 text-sm" data-testid="cons-agreement">
      <div className="font-semibold">Consortium agreement</div>
      <div className="text-xs text-slate-600">Either upload your own agreement signed by every member, or each member signs the standard PMC agreement below.</div>
      {c.agreement?.uploaded && <div className="text-emerald-800 text-xs" data-testid="cons-agreement-uploaded">✓ Uploaded: {c.agreement.uploaded.filename}</div>}
      {c.is_lead && c.status !== "bid_submitted" && <label className="inline-block px-2 py-1 border rounded cursor-pointer text-xs" data-testid="cons-agreement-upload">Upload signed agreement<input type="file" hidden onChange={(e) => e.target.files?.[0] && upload(e.target.files[0])} data-testid="cons-agreement-input" /></label>}
      <details className="text-xs"><summary className="cursor-pointer">Read the standard agreement ({c.agreement_version})</summary>
        <ol className="list-decimal ml-5 mt-1 space-y-1">{(c.agreement_text || []).map((s) => <li key={s.title}><b>{s.title}.</b> {s.text}</li>)}</ol></details>
      <div className="text-xs">Signed by: {signed.length ? signed.map((s) => `${s.company} (${s.signer_name})`).join(", ") : "nobody yet"}</div>
      {!iSigned && c.status !== "bid_submitted" && <div className="flex gap-2 items-center flex-wrap">
        <input className={inp} placeholder="Your full name" value={name} onChange={(e) => setName(e.target.value)} data-testid="cons-sign-name" />
        <label className="text-xs flex gap-1 items-center"><input type="checkbox" checked={ok} onChange={(e) => setOk(e.target.checked)} data-testid="cons-sign-consent" />I sign for my company</label>
        <button type="button" className="px-3 py-1.5 border rounded-md" onClick={sign} data-testid="cons-sign">Sign standard agreement</button></div>}
    </div>);
};

export default function ConsortiumCard({ c, me, onChange }) {
  const live = c.status !== "bid_submitted" && c.status !== "withdrawn";
  const mine = (c.members || []).find((m) => m.vendor_id === me);
  const respond = (accept) => consortiumApi.respond(c.id, accept).then(onChange).then(() => toast.success(accept ? "You joined the consortium" : "Invitation declined")).catch(showApiError);
  const remove = (vid) => consortiumApi.removeMember(c.id, vid).then(onChange).catch(showApiError);
  return (
    <div className="border rounded-md p-3 bg-white space-y-3" data-testid={`cons-card-${c.id}`}>
      <div className="flex justify-between flex-wrap gap-2">
        <div><div className="font-semibold text-slate-900">{c.name}</div><div className="text-xs text-slate-600">Tender {c.notice_ref}{c.notice_title ? ` · ${c.notice_title}` : ""} · up to {c.max_members} members</div></div>
        <span className="text-[10px] uppercase tracking-widest px-2 py-0.5 border self-start" data-testid={`cons-status-${c.id}`}>{c.status === "bid_submitted" ? "Bid submitted" : c.ready ? "Ready to bid" : c.status}</span>
      </div>
      <table className="w-full text-sm"><tbody>
        <tr><td>{c.lead_company} <span className="text-xs text-slate-500">(lead)</span></td><td>{c.lead_share_pct}%</td><td className="text-xs">Lead</td><td /></tr>
        {(c.members || []).map((m) => (
          <tr key={m.vendor_id} className="border-t" data-testid={`cons-member-${m.vendor_id}`}><td>{m.company_name}<div className="text-xs text-slate-500">{m.capability}</div></td><td>{m.share_pct}%</td>
            <td className="text-xs">{STATUS[m.status]}</td>
            <td className="text-right">{c.is_lead && live && <button type="button" className="text-xs underline" onClick={() => remove(m.vendor_id)} data-testid={`cons-remove-${m.vendor_id}`}>Remove</button>}</td></tr>))}
      </tbody></table>
      {mine?.status === "invited" && live && <div className="flex gap-2" data-testid="cons-respond">
        <button type="button" className="px-3 py-1.5 bg-slate-900 text-white rounded-md text-sm" onClick={() => respond(true)} data-testid="cons-accept">Accept and join</button>
        <button type="button" className="px-3 py-1.5 border rounded-md text-sm" onClick={() => respond(false)} data-testid="cons-decline">Decline</button></div>}
      {c.is_lead && live && <><AddMember c={c} onChange={onChange} /><Terms key={JSON.stringify(c.members?.map((m) => m.vendor_id))} c={c} onChange={onChange} /></>}
      {(c.is_lead || mine?.status === "accepted") && <Agreement c={c} me={me} onChange={onChange} />}
      {live && c.issues?.length > 0 && <ul className="text-xs text-amber-800 list-disc ml-5" data-testid={`cons-issues-${c.id}`}>{c.issues.map((i) => <li key={i}>{i}</li>)}</ul>}
      {c.is_lead && live && <button type="button" className="text-xs underline text-red-700" onClick={() => consortiumApi.withdraw(c.id).then(() => onChange(null)).catch(showApiError)} data-testid="cons-withdraw">Withdraw this consortium</button>}
    </div>);
}
