import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { agentApi, showApiError } from "@/lib/api";

const Box = ({ title, children, testid }) => (
  <div className="min-h-screen bg-brand-pale flex items-center justify-center p-6" data-testid={testid}>
    <div className="bg-white border border-brand-navy/15 p-8 w-full max-w-2xl space-y-4">
      <div className="text-[11px] uppercase tracking-widest text-brand-navy/60">PMC Managers · Supplier registration</div>
      <h1 className="font-serif text-2xl text-brand-navy">{title}</h1>
      {children}
    </div>
  </div>
);

export default function SupplierInvite() {
  const { token } = useParams();
  const nav = useNavigate();
  const [info, setInfo] = useState(null);
  const [err, setErr] = useState("");
  const [ticks, setTicks] = useState({});
  const [name, setName] = useState("");
  const [done, setDone] = useState("");
  const [busy, setBusy] = useState(false);
  useEffect(() => { agentApi.inviteInfo(token).then(setInfo).catch((e) => setErr(e?.response?.data?.detail || "Invalid link")); }, [token]);
  const decide = async (decision) => {
    setBusy(true);
    try {
      const r = await agentApi.inviteDecide(token, { decision, signer_name: name, consents: ticks });
      if (decision === "accept" || decision === "self") { toast.success(decision === "self" ? "Email confirmed — you'll complete the form yourself" : "Consent recorded — your email is confirmed"); nav(r.resume_path); } else setDone("declined");
    } catch (e) { showApiError(e); } finally { setBusy(false); }
  };
  if (err) return <Box title="Invitation not valid" testid="supplier-invite-invalid"><p className="text-sm">{String(err)}</p><Link to="/" className="text-xs underline">Home</Link></Box>;
  if (!info) return <Box title="Checking your invitation…" testid="supplier-invite-loading" />;
  if (done) return <Box title="Invitation declined" testid="supplier-invite-declined"><p className="text-sm">The partner has been told. You can still register yourself any time.</p><Link to="/register" className="text-xs underline">Register on PMC</Link></Box>;
  const all = info.consents.every((c) => ticks[c.key]);
  return (
    <Box title={`Register ${info.company_name} on PMC`} testid="supplier-invite">
      <p className="text-sm text-brand-navy/80" data-testid="supplier-invite-partner"><b>{info.partner_name}</b> (PMC partner code <b>{info.partner_code}</b>) has offered to fill in your PMC supplier registration for <b>{info.email}</b>.</p>
      <div className="space-y-2" data-testid="supplier-invite-consents">
        {info.consents.map((c) => (
          <label key={c.key} className="flex gap-2 text-sm items-start"><input type="checkbox" className="mt-1" checked={!!ticks[c.key]} onChange={(e) => setTicks({ ...ticks, [c.key]: e.target.checked })} data-testid={`supplier-consent-${c.key}`} />{c.text}</label>))}
      </div>
      <label className="block text-sm">Your full name (signature)<input className="mt-1 w-full px-3 py-2 border border-brand-navy/20" value={name} onChange={(e) => setName(e.target.value)} data-testid="supplier-consent-name" /></label>
      <div className="flex gap-2 flex-wrap">
        <button className="pmc-btn pmc-btn--primary" disabled={busy || !all || name.trim().length < 3} onClick={() => decide("accept")} data-testid="supplier-consent-accept">Let the partner fill it & open my registration</button>
        <button className="pmc-btn pmc-btn--secondary" disabled={busy || !ticks.data_privacy || name.trim().length < 3} onClick={() => decide("self")} data-testid="supplier-consent-self">I'll fill it myself</button>
        <button className="pmc-btn pmc-btn--secondary" disabled={busy} onClick={() => decide("decline")} data-testid="supplier-consent-decline">I don't know this partner — decline</button>
      </div>
      <p className="text-xs text-brand-navy/60">Filling it yourself needs only your name and the data-privacy tick; {info.partner_code} stays linked as your partner either way, and you can switch later. Consent version {info.version}. Your name, time and IP address are recorded.</p>
    </Box>
  );
}
