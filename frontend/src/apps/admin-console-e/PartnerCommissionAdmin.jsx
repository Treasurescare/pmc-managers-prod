import { useEffect, useState } from "react";
import { toast } from "sonner";
import { agentApi, showApiError } from "@/lib/api";
import { WalletEntries, WalletTotals } from "@/apps/agent-portal/PartnerWallet";
import { BoardTable } from "@/apps/agent-portal/PartnerLeaderboard";

const inp = "mt-1 block px-3 py-2 border border-brand-navy/20 bg-white text-sm w-full";
const EMPTY = { currency: "USD", onboarding_amount: 0, deal_type: "percent", deal_value: 0 };

const RuleFields = ({ r, setR, prefix }) => (
  <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
    <label className="text-sm">Currency<input className={inp} maxLength={3} value={r.currency} onChange={(e) => setR({ ...r, currency: e.target.value.toUpperCase() })} data-testid={`${prefix}-currency`} /></label>
    <label className="text-sm">Onboarding fee (fixed)<input type="number" min="0" step="0.01" className={inp} value={r.onboarding_amount} onChange={(e) => setR({ ...r, onboarding_amount: e.target.value })} data-testid={`${prefix}-onboarding`} /></label>
    <label className="text-sm">Deal fee type<select className={inp} value={r.deal_type} onChange={(e) => setR({ ...r, deal_type: e.target.value })} data-testid={`${prefix}-deal-type`}><option value="percent">% of business earned</option><option value="fixed">Fixed amount</option></select></label>
    <label className="text-sm">{r.deal_type === "percent" ? "Deal fee %" : "Deal fee amount"}<input type="number" min="0" step="0.01" className={inp} value={r.deal_value} onChange={(e) => setR({ ...r, deal_value: e.target.value })} data-testid={`${prefix}-deal-value`} /></label>
  </div>
);
const num = (r) => ({ ...r, onboarding_amount: Number(r.onboarding_amount || 0), deal_value: Number(r.deal_value || 0) });

export const AdminLeaderboardCard = () => {
  const [b, setB] = useState(null);
  const [saving, setSaving] = useState(false);
  const load = () => agentApi.adminLeaderboard().then(setB).catch(showApiError);
  useEffect(() => { load(); }, []);
  if (!b) return null;
  const toggle = (v) => { setSaving(true); setB({ ...b, show_names: v }); agentApi.setLeaderboard(v).then(() => toast.success(v ? "Partners now see each other's names" : "Partners now see codes only")).catch(showApiError).finally(() => { setSaving(false); load(); }); };
  return (
    <details className="bg-white border border-brand-navy/15 p-4" data-testid="admin-leaderboard">
      <summary className="font-semibold cursor-pointer">Partner leaderboard · {b.month}</summary>
      <label className="flex items-center gap-2 text-sm my-3"><input type="checkbox" checked={b.show_names} disabled={saving} onChange={(e) => toggle(e.target.checked)} data-testid="leaderboard-show-names" />Show partner names to other partners (otherwise partner codes only)</label>
      <BoardTable rows={b.rows} showId />
    </details>
  );
};

export const CommissionSettingsCard = () => {
  const [r, setR] = useState(null);
  useEffect(() => { agentApi.commissionSettings().then((s) => setR({ ...EMPTY, ...s })).catch(showApiError); }, []);
  if (!r) return null;
  const save = () => agentApi.saveCommissionSettings(num(r)).then(() => toast.success("Default commission saved")).catch(showApiError);
  return (
    <div className="bg-white border border-brand-navy/15 p-4 space-y-3" data-testid="commission-settings">
      <div className="font-semibold">Default partner commission</div>
      <p className="text-xs text-brand-navy/60">Onboarding fee is added to a partner's wallet automatically when a supplier they onboarded is approved. Deal fees are added by you when a deal completes. You pay partners from your own account and mark entries paid.</p>
      <RuleFields r={r} setR={setR} prefix="cs" />
      <button className="pmc-btn pmc-btn--primary" onClick={save} data-testid="cs-save">Save default</button>
    </div>
  );
};

const DealForm = ({ id, suppliers, onDone }) => {
  const [f, setF] = useState({ vendor_ref: "", deal_ref: "", business_amount: "", note: "" });
  const approved = suppliers.filter((s) => s.vendor_ref);
  const go = (e) => {
    e.preventDefault();
    agentApi.addDeal(id, { ...f, business_amount: Number(f.business_amount || 0) }).then((x) => { toast.success(`Deal commission ${x.currency} ${x.amount} added`); setF({ vendor_ref: "", deal_ref: "", business_amount: "", note: "" }); onDone(); }).catch(showApiError);
  };
  return (
    <form onSubmit={go} className="grid md:grid-cols-4 gap-2 items-end" data-testid="deal-form">
      <label className="text-sm">Supplier<select required className={inp} value={f.vendor_ref} onChange={(e) => setF({ ...f, vendor_ref: e.target.value })} data-testid="deal-vendor"><option value="">Choose…</option>{approved.map((s) => <option key={s.id} value={s.vendor_ref}>{s.company_name} ({s.vendor_ref})</option>)}</select></label>
      <label className="text-sm">Deal / tender ref<input required className={inp} value={f.deal_ref} onChange={(e) => setF({ ...f, deal_ref: e.target.value })} data-testid="deal-ref" /></label>
      <label className="text-sm">PMC business earned<input type="number" min="0" step="0.01" className={inp} value={f.business_amount} onChange={(e) => setF({ ...f, business_amount: e.target.value })} data-testid="deal-amount" /></label>
      <button className="pmc-btn pmc-btn--secondary" data-testid="deal-submit">Add deal commission</button>
    </form>
  );
};

const Settle = ({ e, reload }) => {
  const act = (action) => {
    const ref = window.prompt(action === "paid" ? "Payment reference (bank transfer ref, cheque no.)" : "Reason for voiding");
    if (!ref || ref.trim().length < 2) return;
    agentApi.settle(e.id, action, ref.trim()).then(() => { toast.success(action === "paid" ? "Marked paid — partner emailed" : "Commission voided"); reload(); }).catch(showApiError);
  };
  return <><button type="button" className="px-2 py-1 text-xs border border-brand-navy" onClick={() => act("paid")} data-testid={`wallet-mark-paid-${e.id}`}>Mark paid</button>
    <button type="button" className="px-2 py-1 text-xs border" onClick={() => act("void")} data-testid={`wallet-void-${e.id}`}>Void</button></>;
};

const Move = ({ s, partners, fromId, onDone }) => {
  const [to, setTo] = useState("");
  const [note, setNote] = useState("");
  const [open, setOpen] = useState(false);
  if (!open) return <button type="button" className="px-2 py-0.5 text-[11px] border" onClick={() => setOpen(true)} data-testid={`move-open-${s.id}`}>Move to another partner</button>;
  const go = () => agentApi.reassign(s.id, to, note).then((r) => { toast.success(r.reconsent_sent ? "Moved — supplier asked to confirm the new partner" : "Supplier moved"); setOpen(false); onDone(); }).catch(showApiError);
  return (
    <div className="flex gap-2 flex-wrap items-center mt-1" data-testid={`move-form-${s.id}`}>
      <select className="px-2 py-1 border text-xs" value={to} onChange={(e) => setTo(e.target.value)} data-testid={`move-to-${s.id}`}>
        <option value="">New partner…</option>{partners.filter((p) => p.status === "approved" && p.id !== fromId).map((p) => <option key={p.id} value={p.id}>{p.legal_name || p.name} ({p.partner_code})</option>)}</select>
      <input className="px-2 py-1 border text-xs flex-1 min-w-[200px]" placeholder="Reason (kept in history)" value={note} onChange={(e) => setNote(e.target.value)} data-testid={`move-note-${s.id}`} />
      <button type="button" className="px-2 py-1 text-xs border border-brand-navy" disabled={!to || note.trim().length < 5} onClick={go} data-testid={`move-submit-${s.id}`}>Move</button>
    </div>
  );
};

const SupplierLine = ({ s, partners, fromId, onDone }) => (
  <div className="py-1" data-testid={`admin-partner-supplier-${s.id}`}>
    <div>{s.company_name} · {s.email} · {s.partner_access} · {s.status}{s.vendor_ref ? ` · ${s.vendor_ref}` : ""} · {s.edits} edits</div>
    {(s.history || []).map((h, i) => <div key={i} className="text-[11px] text-brand-navy/60" data-testid={`move-history-${s.id}-${i}`}>{h.at.slice(0, 10)} moved {h.from?.code} → {h.to?.code} by {h.by}: {h.note}</div>)}
    <Move s={s} partners={partners} fromId={fromId} onDone={onDone} />
  </div>
);

export const PartnerWalletAdmin = ({ id, partners = [] }) => {
  const [w, setW] = useState(null);
  const [ov, setOv] = useState(null);
  const load = () => agentApi.adminWallet(id).then((x) => { setW(x); setOv(x.override ? { ...EMPTY, ...x.override } : null); }).catch(showApiError);
  useEffect(() => { load(); }, [id]); // eslint-disable-line react-hooks/exhaustive-deps
  if (!w) return null;
  const saveOv = (rule) => agentApi.setPartnerRule(id, rule ? num(rule) : null).then(() => { toast.success(rule ? "Partner commission saved" : "Using default commission"); load(); }).catch(showApiError);
  return (
    <div className="space-y-3 border-t pt-3" data-testid={`admin-partner-wallet-${id}`}>
      <div className="pmc-label">Suppliers onboarded ({w.suppliers.length})</div>
      <div className="text-xs divide-y" data-testid="admin-partner-suppliers">{w.suppliers.map((s) => <SupplierLine key={s.id} s={s} partners={partners} fromId={id} onDone={load} />)}</div>
      <div className="pmc-label">Commission rule ({w.rule.source === "partner" ? "special for this partner" : "default"})</div>
      {ov ? <><RuleFields r={ov} setR={setOv} prefix="ov" /><div className="flex gap-2"><button className="pmc-btn pmc-btn--primary" onClick={() => saveOv(ov)} data-testid="ov-save">Save for this partner</button><button className="pmc-btn pmc-btn--secondary" onClick={() => saveOv(null)} data-testid="ov-clear">Use default</button></div></>
        : <button className="pmc-btn pmc-btn--secondary" onClick={() => setOv({ ...EMPTY, ...w.rule })} data-testid="ov-start">Set a special rate for this partner</button>}
      <div className="pmc-label">Wallet</div>
      <WalletTotals totals={w.totals} />
      <DealForm id={id} suppliers={w.suppliers} onDone={load} />
      <WalletEntries items={w.items} actions={(e) => <Settle e={e} reload={load} />} />
    </div>
  );
};
