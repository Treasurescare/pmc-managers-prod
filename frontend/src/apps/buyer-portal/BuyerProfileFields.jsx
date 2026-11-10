import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { useCountries } from "@/components/CountryPicker";

function useList(url) {
  const [rows, setRows] = useState(null);
  useEffect(() => {
    let live = true;
    setRows(null);
    if (url) api.get(url).then((r) => { if (live) setRows(r.data || []); }).catch(() => { if (live) setRows([]); });
    return () => { live = false; };
  }, [url]);
  return rows;
}

const uniq = (rows) => [...new Map((rows || []).map((c) => [`${c.state_code}|${c.name}`, c])).values()];

const L = ({ t, req, children }) => (
  <label className="text-xs grid gap-1"><span>{t}{req && <b className="text-red-700"> *</b>}</span>{children}</label>);

// Name, mobile, country → state → city (masters), address/ZIP optional. `f` is a flat profile object.
export function BuyerProfileFields({ f, set, prefix = "buyer", withOrg = true }) {
  const countries = useCountries();
  const country = countries.find((c) => c.code === f.country_code);
  const statesRaw = useList(f.country_code ? `/api/v1/masters/states?country_code=${f.country_code}` : null);
  const states = statesRaw || [];
  const needState = states.length > 0 && !f.state_code;
  const cities = uniq(useList(f.country_code && statesRaw && !needState ? `/api/v1/masters/cities?country_code=${f.country_code}${f.state_code ? `&state_code=${encodeURIComponent(f.state_code)}` : ""}&limit=500` : null));
  const patch = (o) => set({ ...f, ...o });
  return (
    <div className="grid sm:grid-cols-2 gap-3">
      <L t="Full name" req><input className="pmc-input" value={f.name || ""} onChange={(e) => patch({ name: e.target.value })} data-testid={`${prefix}-name`} /></L>
      {withOrg && <L t="Organisation (optional)"><input className="pmc-input" value={f.org_name || ""} onChange={(e) => patch({ org_name: e.target.value })} data-testid={`${prefix}-org`} /></L>}
      <L t="Country" req>
        <select className="pmc-input" value={f.country_code || ""} onChange={(e) => patch({ country_code: e.target.value, state_code: "", city: "" })} data-testid={`${prefix}-country`}>
          <option value="">Choose a country…</option>
          {countries.map((c) => <option key={c.code} value={c.code}>{c.name}</option>)}
        </select></L>
      <L t="Mobile number" req>
        <div className="flex gap-2"><span className="pmc-input w-20 text-center" data-testid={`${prefix}-phone-code`}>{country?.phone_code || "+"}</span>
          <input className="pmc-input flex-1" inputMode="tel" value={f.phone || ""} onChange={(e) => patch({ phone: e.target.value.replace(/[^0-9 -]/g, "") })} data-testid={`${prefix}-phone`} /></div></L>
      <L t="State / province">
        <select className="pmc-input" value={f.state_code || ""} disabled={!states.length} onChange={(e) => patch({ state_code: e.target.value, city: "" })} data-testid={`${prefix}-state`}>
          <option value="">{states.length ? "State / province…" : "No states listed"}</option>
          {states.map((s) => <option key={s.state_code} value={s.state_code}>{s.name}</option>)}
        </select></L>
      <L t="City" req>
        <select className="pmc-input" value={f.city || ""} disabled={!cities.length} onChange={(e) => patch({ city: e.target.value })} data-testid={`${prefix}-city`}>
          <option value="">{needState ? "Choose a state first" : cities.length ? "City…" : "Choose a country first"}</option>
          {f.city && !cities.some((c) => c.name === f.city) && <option value={f.city}>{f.city}</option>}
          {cities.map((c) => <option key={`${c.state_code}|${c.name}`} value={c.name}>{c.name}</option>)}
        </select></L>
      <L t="Address (optional)"><input className="pmc-input" value={f.address || ""} onChange={(e) => patch({ address: e.target.value })} data-testid={`${prefix}-address`} /></L>
      <L t="ZIP / postal code (optional)"><input className="pmc-input" value={f.zip || ""} placeholder={country?.postal_code_format || ""} onChange={(e) => patch({ zip: e.target.value })} data-testid={`${prefix}-zip`} /></L>
    </div>);
}

export const profileReady = (f) => !!(f.name?.trim() && f.phone?.replace(/\D/g, "").length >= 6 && f.country_code && f.city);
export const profileBody = (f) => ({ name: f.name, phone: f.phone, country_code: f.country_code, city: f.city, state_code: f.state_code || null,
  address: f.address || null, zip: f.zip || null, org_name: f.org_name || null });
