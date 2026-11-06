import { useCallback, useEffect, useState } from "react";
import { toast } from "sonner";
import { growthApi } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";

export const btn = "px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy/5";
export const inp = "mt-1 w-full px-2 py-1.5 border border-brand-navy/20 bg-white text-sm";
export const useList = (fn) => {
  const [items, setItems] = useState([]);
  const load = useCallback(() => fn().then((r) => setItems(r.items || [])).catch(showApiError), [fn]);
  useEffect(() => { load(); }, [load]);
  return [items, load];
};

const Decide = ({ a, onDone }) => {
  const [f, setF] = useState({ code: "", tier: "", notes: "" });
  const go = (action) => growthApi.decideBuyer(a.id, { action, code: f.code || null, tier: f.tier || null, notes: f.notes || null })
    .then((r) => { toast.success(action === "approve" ? `Approved · organisation code ${r.tenant_code}` : "Rejected"); onDone(); }).catch(showApiError);
  return (
    <div className="grid md:grid-cols-4 gap-2 mt-2 items-end">
      <label className="text-xs">Organisation code<input className={inp} value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} placeholder="auto" data-testid={`buyer-app-code-${a.id}`} /></label>
      <label className="text-xs">Tier<input className={inp} value={f.tier} onChange={(e) => setF({ ...f, tier: e.target.value })} placeholder="Starter" data-testid={`buyer-app-tier-${a.id}`} /></label>
      <label className="text-xs">Notes<input className={inp} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} data-testid={`buyer-app-notes-${a.id}`} /></label>
      <div className="flex gap-2"><button className={btn} onClick={() => go("approve")} data-testid={`buyer-app-approve-${a.id}`}>Approve</button>
        <button className={btn} onClick={() => go("reject")} data-testid={`buyer-app-reject-${a.id}`}>Reject</button></div>
    </div>);
};

export const BuyerAppsTab = () => {
  const [items, load] = useList(growthApi.buyerApps);
  return (
    <div className="bg-white border border-brand-navy/10 divide-y divide-brand-navy/10" data-testid="buyer-apps-tab">
      {!items.length && <div className="p-4 text-sm opacity-60" data-testid="buyer-apps-empty">No applications yet. The public form is at /buyers/apply.</div>}
      {items.map((a) => (
        <div key={a.id} className="p-4 text-sm" data-testid={`buyer-app-${a.id}`}>
          <div className="flex flex-wrap gap-2"><b className="flex-1">{a.org_name}</b><span className="uppercase text-xs font-semibold">{a.status}{a.tenant_code ? ` · ${a.tenant_code}` : ""}</span></div>
          <div className="text-xs opacity-70">{a.org_type} · {a.country} · {a.contact_name} &lt;{a.email}&gt; {a.phone || ""} · {a.tenders_per_year ?? "?"} tenders/yr · {String(a.created_at).slice(0, 10)}</div>
          {a.message && <div className="text-xs mt-1">{a.message}</div>}
          {a.status === "pending" && <Decide a={a} onDone={load} />}
        </div>))}
    </div>);
};
