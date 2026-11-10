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
    .then((r) => {
      if (action !== "approve") toast.success("Rejected");
      else if (r.signin_status === "sent") toast.success(`Approved · ${r.tenant_code} · sign-in emailed to ${r.signin_email}`);
      else toast.warning(`Approved · ${r.tenant_code}. ${r.signin_email} already has another PMC sign-in — send the buyer sign-in to a different email.`, { duration: 10000 });
      onDone();
    }).catch(showApiError);
  return (
    <div className="grid md:grid-cols-4 gap-2 mt-2 items-end">
      <label className="text-xs">Organisation code<input className={inp} value={f.code} onChange={(e) => setF({ ...f, code: e.target.value })} placeholder="auto" data-testid={`buyer-app-code-${a.id}`} /></label>
      <label className="text-xs">Tier<input className={inp} value={f.tier} onChange={(e) => setF({ ...f, tier: e.target.value })} placeholder="Starter" data-testid={`buyer-app-tier-${a.id}`} /></label>
      <label className="text-xs">Notes<input className={inp} value={f.notes} onChange={(e) => setF({ ...f, notes: e.target.value })} data-testid={`buyer-app-notes-${a.id}`} /></label>
      <div className="flex gap-2"><button className={btn} onClick={() => go("approve")} data-testid={`buyer-app-approve-${a.id}`}>Approve</button>
        <button className={btn} onClick={() => go("reject")} data-testid={`buyer-app-reject-${a.id}`}>Reject</button></div>
    </div>);
};

const SignIn = ({ a, onDone }) => {
  const [email, setEmail] = useState("");
  const [busy, setBusy] = useState(false);
  const go = () => { setBusy(true); growthApi.buyerSignin(a.id, { email: email || null })
    .then((r) => { toast.success(`Sign-in link emailed to ${r.signin_email}`); setEmail(""); onDone(); }).catch(showApiError).finally(() => setBusy(false)); };
  const label = a.signin_status === "sent" ? `Sign-in sent to ${a.signin_email} · ${String(a.signin_sent_at).slice(0, 10)}`
    : a.signin_status === "email_in_use" ? `${a.signin_email} already has another PMC sign-in — use a different email` : "No buyer sign-in sent yet";
  return (
    <div className="flex flex-wrap gap-2 mt-2 items-end" data-testid={`buyer-app-signin-${a.id}`}>
      <span className="text-xs flex-1 min-w-[200px]" data-testid={`buyer-app-signin-status-${a.id}`}>{label}</span>
      <label className="text-xs">Other email (optional)<input className={inp} type="email" value={email} onChange={(e) => setEmail(e.target.value)} placeholder={a.email} data-testid={`buyer-app-signin-email-${a.id}`} /></label>
      <button className={btn} disabled={busy} onClick={go} data-testid={`buyer-app-signin-send-${a.id}`}>{a.signin_status === "sent" && !email ? "Resend sign-in" : "Send sign-in"}</button>
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
          {a.status === "approved" && a.tenant_code && <SignIn a={a} onDone={load} />}
        </div>))}
    </div>);
};
