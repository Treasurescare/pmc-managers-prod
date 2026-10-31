import { useEffect, useState } from "react";
import { toast } from "sonner";
import { agentApi, showApiError } from "@/lib/api";

const money = (c, v) => `${c} ${Number(v || 0).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;

export const WalletTotals = ({ totals }) => (
  <div className="flex gap-3 flex-wrap" data-testid="wallet-totals">
    {Object.entries(totals || {}).map(([c, t]) => (
      <div key={c} className="bg-white border border-brand-navy/15 px-4 py-3 min-w-[180px]">
        <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">{c}</div>
        <div className="text-sm">Due <b data-testid={`wallet-due-${c}`}>{money(c, t.due)}</b></div>
        <div className="text-sm">Paid <b data-testid={`wallet-paid-${c}`}>{money(c, t.paid)}</b></div>
      </div>))}
    {!Object.keys(totals || {}).length && <div className="text-sm text-brand-navy/60" data-testid="wallet-empty-totals">No commission earned yet.</div>}
  </div>
);

export const WalletEntries = ({ items, actions }) => (
  <div className="bg-white border border-brand-navy/15 divide-y" data-testid="wallet-entries">
    {(items || []).map((e) => (
      <div key={e.id} className="p-3 flex justify-between gap-3 flex-wrap text-sm" data-testid={`wallet-entry-${e.id}`}>
        <div><b>{e.kind === "onboarding" ? "Onboarding" : `Deal · ${e.deal_ref}`}</b> — {e.company_name} {e.vendor_ref ? `(${e.vendor_ref})` : ""}
          <div className="text-xs text-brand-navy/60">{e.basis} · {e.created_at?.slice(0, 10)}{e.reference ? ` · ref ${e.reference}` : ""}{e.paid_on ? ` · paid ${e.paid_on}` : ""}</div></div>
        <div className="flex gap-2 items-center"><span className="font-semibold">{money(e.currency, e.amount)}</span>
          <span className="text-[10px] uppercase tracking-widest px-2 py-0.5 border" data-testid={`wallet-status-${e.id}`}>{e.status}</span>
          {actions && e.status === "due" && actions(e)}</div>
      </div>))}
    {!(items || []).length && <div className="p-6 text-sm text-center text-brand-navy/60">No commission entries yet.</div>}
  </div>
);

export default function PartnerWallet() {
  const [w, setW] = useState(null);
  const load = () => agentApi.wallet().then(setW).catch(showApiError);
  useEffect(() => { load(); }, []);
  if (!w) return <div className="text-brand-navy/50 text-sm">Loading…</div>;
  const r = w.rule || {};
  const ask = () => agentApi.requestPayout().then(() => { toast.success("Payout request sent to PMC"); load(); }).catch(showApiError);
  const hasDue = Object.values(w.totals || {}).some((t) => t.due > 0);
  return (
    <div className="space-y-4" data-testid="partner-wallet">
      <div className="text-sm text-brand-navy/70" data-testid="wallet-rule">Your commission: {money(r.currency, r.onboarding_amount)} per approved supplier
        {Number(r.deal_value) > 0 && <> · deals: {r.deal_type === "percent" ? `${r.deal_value}% of PMC business earned` : money(r.currency, r.deal_value)}</>}. PMC pays you directly from its own account.</div>
      <WalletTotals totals={w.totals} />
      <div className="flex gap-3 items-center flex-wrap">
        <button className="pmc-btn pmc-btn--primary" disabled={!hasDue} onClick={ask} data-testid="wallet-request-payout">Request payout</button>
        {w.payout_requested_at && <span className="text-xs text-brand-navy/60" data-testid="wallet-payout-requested">Last requested {w.payout_requested_at.slice(0, 10)}</span>}
      </div>
      <WalletEntries items={w.items} />
    </div>
  );
}
