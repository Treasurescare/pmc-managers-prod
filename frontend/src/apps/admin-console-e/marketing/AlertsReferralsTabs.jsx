import { useEffect, useState } from "react";
import { toast } from "sonner";
import { marketingApi, showApiError } from "@/lib/api";

export const AlertsTab = () => {
  const [d, setD] = useState(null);
  const load = () => marketingApi.alerts().then(setD).catch(showApiError);
  useEffect(() => { load(); }, []);
  const save = async (patch) => {
    const next = { enabled: d.enabled, include_uploaded: d.include_uploaded, ...patch };
    try { await marketingApi.saveAlerts(next); setD({ ...d, ...next }); toast.success("Saved"); } catch (e) { showApiError(e); }
  };
  if (!d) return null;
  return (
    <div className="space-y-4" data-testid="mkt-alerts">
      <div className="border border-brand-navy/20 bg-white p-4 space-y-3">
        <label className="flex gap-3 items-center font-semibold">
          <input type="checkbox" checked={d.enabled} onChange={(e) => save({ enabled: e.target.checked })} data-testid="mkt-alerts-enabled" />
          Email vendors when a new tender in their category is published
        </label>
        <label className="flex gap-3 items-center text-sm">
          <input type="checkbox" checked={d.include_uploaded} onChange={(e) => save({ include_uploaded: e.target.checked })} data-testid="mkt-alerts-uploaded" />
          Also alert uploaded vendor contacts with that category (helps them sign up)
        </label>
        <div className="text-xs text-brand-navy/60">Sent once per tender, when it goes live. People who unsubscribed are skipped.</div>
      </div>
      <div className="border border-brand-navy/15 bg-white">
        <div className="pmc-label p-3">Recent alerts</div>
        {d.items.map((a) => (
          <div key={a.id} className="border-t border-brand-navy/10 p-3 text-sm flex gap-3" data-testid={`mkt-alert-${a.notice_ref}`}>
            <span className="font-semibold">{a.notice_ref}</span><span className="flex-1">{a.title} · {a.category}</span>
            <span>{a.recipients} emailed</span><span className="text-brand-navy/50">{a.at?.slice(0, 16).replace("T", " ")}</span>
          </div>))}
        {!d.items.length && <div className="p-4 text-sm text-brand-navy/60">No alerts sent yet.</div>}
      </div>
    </div>
  );
};

export const ReferralsTab = () => {
  const [d, setD] = useState({ leaders: [], recent: [] });
  useEffect(() => { marketingApi.referrals().then(setD).catch(showApiError); }, []);
  return (
    <div className="grid gap-6 lg:grid-cols-2" data-testid="mkt-referrals">
      <div className="border border-brand-navy/15 bg-white">
        <div className="pmc-label p-3">Top referrers</div>
        {d.leaders.map((l) => (
          <div key={l.code} className="border-t border-brand-navy/10 p-3 text-sm flex gap-3" data-testid={`mkt-ref-leader-${l.code}`}>
            <span className="flex-1 font-semibold">{l.referrer}</span><span className="text-brand-navy/50">{l.code}</span><span>{l.count} joined</span>
          </div>))}
        {!d.leaders.length && <div className="p-4 text-sm text-brand-navy/60">No referrals yet. Vendors find their link under Refer &amp; earn in their portal.</div>}
      </div>
      <div className="border border-brand-navy/15 bg-white">
        <div className="pmc-label p-3">Latest sign-ups from referral links</div>
        {d.recent.map((r) => (
          <div key={r.id} className="border-t border-brand-navy/10 p-3 text-sm flex gap-3">
            <span className="flex-1">{r.company || r.email}</span><span className="text-brand-navy/50">{r.code}</span><span>{r.at?.slice(0, 10)}</span>
          </div>))}
      </div>
    </div>
  );
};
