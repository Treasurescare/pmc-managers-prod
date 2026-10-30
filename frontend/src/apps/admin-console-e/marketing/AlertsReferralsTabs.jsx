import { useEffect, useState } from "react";
import { toast } from "sonner";
import { marketingApi, showApiError } from "@/lib/api";

export const AlertsTab = () => {
  const [d, setD] = useState(null);
  const load = () => marketingApi.alerts().then(setD).catch(showApiError);
  useEffect(() => { load(); }, []);
  const save = async (patch) => {
    const next = { enabled: d.enabled, include_uploaded: d.include_uploaded, mode: d.mode, ...patch };
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
        <div className="flex gap-6 text-sm" data-testid="mkt-alerts-mode">
          {[["instant", "One email per new tender"], ["weekly", "One weekly digest (Mondays 08:00 London)"]].map(([m, l]) => (
            <label key={m} className="flex gap-2 items-center"><input type="radio" checked={d.mode === m} onChange={() => save({ mode: m })} data-testid={`mkt-alerts-mode-${m}`} />{l}</label>))}
        </div>
        <div className="flex items-center gap-3 text-sm">
          <button className="pmc-btn border border-brand-navy/40 bg-white px-3 py-2 text-sm" data-testid="mkt-digest-now"
            onClick={async () => { try { await marketingApi.digestNow(); toast.success("Digest is being sent — refresh in a minute"); } catch (e) { showApiError(e); } }}>Send this week's digest now</button>
          <span className="text-xs text-brand-navy/50">(sends even if alerts are off)</span>
          <span className="text-brand-navy/60" data-testid="mkt-website-subs">{d.website_subscribers} confirmed sign-ups from the website</span>
        </div>
        <div className="text-xs text-brand-navy/60">People who unsubscribed are always skipped.</div>
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
      <div className="border border-brand-navy/15 bg-white">
        <div className="pmc-label p-3">Weekly digests</div>
        {(d.digests || []).map((g) => (
          <div key={g.id} className="border-t border-brand-navy/10 p-3 text-sm flex gap-3" data-testid={`mkt-digest-${g.id}`}>
            <span className="font-semibold">{g.week.slice(0, 8)}{g.week.includes("manual") && <span className="ml-2 text-[10px] px-1.5 py-0.5 bg-amber-600 text-white uppercase">manual</span>}</span><span className="flex-1">{g.tenders} new tenders{g.note ? ` · ${g.note}` : ""}</span>
            <span>{g.recipients} emailed</span><span className="text-brand-navy/50">{g.at?.slice(0, 16).replace("T", " ")}</span>
          </div>))}
        {!(d.digests || []).length && <div className="p-4 text-sm text-brand-navy/60">No digests sent yet.</div>}
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
