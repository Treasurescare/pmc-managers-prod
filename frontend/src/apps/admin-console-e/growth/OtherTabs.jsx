import { useState } from "react";
import { toast } from "sonner";
import { growthApi } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";
import { btn, inp, useList } from "./BuyerAppsTab";

export const DirectoryTab = () => {
  const [items, load] = useList(growthApi.adminDirectory);
  const feature = (ref, days) => growthApi.adminFeature(ref, days).then(() => { toast.success(days ? `Featured for ${days} days` : "Feature removed"); load(); }).catch(showApiError);
  return (
    <div className="bg-white border border-brand-navy/10 divide-y divide-brand-navy/10" data-testid="directory-tab">
      {items.map((v) => (
        <div key={v.vendor_ref} className="p-3 text-sm flex flex-wrap gap-2 items-center" data-testid={`dir-row-${v.vendor_ref}`}>
          <span className="flex-1"><b>{v.company_name}</b> · {v.country} · {v.listed ? "listed" : "not listed"}{v.featured ? ` · featured until ${String(v.featured_until).slice(0, 10)}` : ""}</span>
          <button className={btn} onClick={() => feature(v.vendor_ref, 30)} data-testid={`dir-feature-${v.vendor_ref}`}>Feature 30 days</button>
          {v.featured && <button className={btn} onClick={() => feature(v.vendor_ref, 0)} data-testid={`dir-unfeature-${v.vendor_ref}`}>Remove feature</button>}
        </div>))}
      {!items.length && <div className="p-3 text-sm opacity-60">No approved suppliers yet.</div>}
    </div>);
};

const KeyBox = ({ k, onClose }) => (
  <div className="bg-amber-50 border border-amber-300 p-3 mb-3 text-sm" data-testid="api-key-box">
    <b>Copy this API key now — it is shown only once.</b>
    <div className="font-mono break-all mt-1" data-testid="api-key-value">{k}</div>
    <div className="flex gap-2 mt-2"><button className={btn} onClick={() => navigator.clipboard?.writeText(k).then(() => toast.success("Copied"))} data-testid="api-key-copy">Copy</button>
      <button className={btn} onClick={onClose} data-testid="api-key-close">Done</button></div>
  </div>);

export const DataApiTab = () => {
  const [items, load] = useList(growthApi.apiClients);
  const [f, setF] = useState({ name: "", email: "", plan: "Standard", daily_limit: 1000 });
  const [key, setKey] = useState(null);
  const create = () => growthApi.createApiClient({ ...f, daily_limit: Number(f.daily_limit) }).then((r) => { setKey(r.api_key); load(); }).catch(showApiError);
  const toggle = (c) => growthApi.updateApiClient(c.id, { name: c.name, email: c.email, plan: c.plan, daily_limit: c.daily_limit, is_active: !c.is_active }).then(load).catch(showApiError);
  const rotate = (c) => growthApi.rotateApiClient(c.id).then((r) => setKey(r.api_key)).catch(showApiError);
  return (
    <div data-testid="data-api-tab">
      <p className="text-sm mb-2">Clients call <code>GET /api/v1/data/tenders</code> with header <code>X-API-Key</code>. Filters: q, country, source (all|pmc|global), updated_since, limit, offset. Plan fees: Masters → Fee rules → "Tender data API plan".</p>
      {key && <KeyBox k={key} onClose={() => setKey(null)} />}
      <div className="bg-white border border-brand-navy/20 p-3 mb-3 grid md:grid-cols-5 gap-2 text-xs items-end" data-testid="api-client-form">
        <label>Client name<input className={inp} value={f.name} onChange={(e) => setF({ ...f, name: e.target.value })} data-testid="api-client-name" /></label>
        <label>Email<input className={inp} value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="api-client-email" /></label>
        <label>Plan<input className={inp} value={f.plan} onChange={(e) => setF({ ...f, plan: e.target.value })} data-testid="api-client-plan" /></label>
        <label>Requests per day<input type="number" className={inp} value={f.daily_limit} onChange={(e) => setF({ ...f, daily_limit: e.target.value })} data-testid="api-client-limit" /></label>
        <button className={btn} onClick={create} data-testid="api-client-create">Create key</button>
      </div>
      <div className="bg-white border border-brand-navy/10 divide-y divide-brand-navy/10">
        {items.map((c) => (
          <div key={c.id} className="p-3 text-sm flex flex-wrap gap-2 items-center" data-testid={`api-client-${c.id}`}>
            <span className="flex-1"><b>{c.name}</b> · {c.email} · {c.plan} · {c.daily_limit}/day · key …{c.key_hint} · {c.is_active ? "active" : "disabled"}</span>
            <button className={btn} onClick={() => rotate(c)} data-testid={`api-client-rotate-${c.id}`}>New key</button>
            <button className={btn} onClick={() => toggle(c)} data-testid={`api-client-toggle-${c.id}`}>{c.is_active ? "Disable" : "Enable"}</button>
          </div>))}
        {!items.length && <div className="p-3 text-sm opacity-60">No API clients yet.</div>}
      </div>
    </div>);
};

const SourceRow = ({ s, onDone }) => {
  const [f, setF] = useState({ url: s.url || "", api_key_env: s.api_key_env || "", items_path: s.items_path || "", mapping: JSON.stringify(s.mapping || {}, null, 0) });
  const [busy, setBusy] = useState(false);
  const save = (enabled) => {
    let mapping;
    try { mapping = JSON.parse(f.mapping || "{}"); } catch { return toast.error("Field mapping must be valid JSON"); }
    return growthApi.updateSource(s.code, { enabled, ...(s.kind === "provider" ? { url: f.url, api_key_env: f.api_key_env, items_path: f.items_path, mapping } : {}) })
      .then(() => { toast.success("Saved"); onDone(); }).catch(showApiError);
  };
  const run = () => { setBusy(true); growthApi.runSource(s.code).then((r) => { r.ok ? toast.success(`Fetched ${r.fetched}: ${r.new} new, ${r.updated} updated`) : toast.error(r.error); onDone(); }).catch(showApiError).finally(() => setBusy(false)); };
  return (
    <div className="p-3 text-sm" data-testid={`source-${s.code}`}>
      <div className="flex flex-wrap gap-2 items-center"><span className="flex-1"><b>{s.name}</b> · {s.licence} · {s.count} tenders · {s.enabled ? "on" : "off"}
        {s.last_run_at ? ` · last run ${String(s.last_run_at).slice(0, 16).replace("T", " ")} ${s.last_result?.ok ? "ok" : `failed: ${s.last_result?.error || ""}`}` : ""}</span>
        <button className={btn} onClick={() => save(!s.enabled)} data-testid={`source-toggle-${s.code}`}>{s.enabled ? "Turn off" : "Turn on"}</button>
        <button className={btn} disabled={busy} onClick={run} data-testid={`source-run-${s.code}`}>{busy ? "Fetching…" : "Fetch now"}</button></div>
      {s.kind === "provider" && <div className="grid md:grid-cols-3 gap-2 mt-2 text-xs">
        <label>Provider API URL<input className={inp} value={f.url} onChange={(e) => setF({ ...f, url: e.target.value })} data-testid="provider-url" /></label>
        <label>Key name in server secrets {s.key_set ? "(set)" : "(not set)"}<input className={inp} value={f.api_key_env} onChange={(e) => setF({ ...f, api_key_env: e.target.value.toUpperCase() })} data-testid="provider-key-env" /></label>
        <label>Items path in response<input className={inp} value={f.items_path} onChange={(e) => setF({ ...f, items_path: e.target.value })} data-testid="provider-items-path" /></label>
        <label className="md:col-span-3">Field mapping (JSON)<input className={inp} value={f.mapping} onChange={(e) => setF({ ...f, mapping: e.target.value })} data-testid="provider-mapping" /></label>
        <div><button className={btn} onClick={() => save(s.enabled)} data-testid="provider-save">Save provider settings</button></div>
      </div>}
    </div>);
};

export const SourcesTab = () => {
  const [items, load] = useList(growthApi.sources);
  return (
    <div data-testid="sources-tab">
      <p className="text-sm mb-2">Collected tenders appear on the public page /tenders/global, in saved alerts and in the data API. Duplicates across sources are hidden automatically; deadline changes are marked Amended.</p>
      <div className="bg-white border border-brand-navy/10 divide-y divide-brand-navy/10">{items.map((s) => <SourceRow key={s.code} s={s} onDone={load} />)}</div>
    </div>);
};
