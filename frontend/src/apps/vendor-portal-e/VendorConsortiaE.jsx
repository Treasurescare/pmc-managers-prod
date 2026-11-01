import { useEffect, useState } from "react";
import { consortiumApi, vendorApi, showApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";
import ConsortiumCard from "@/apps/vendor-portal/ConsortiumCard";
import MyConsortiumPayouts from "./MyConsortiumPayouts";

export default function VendorConsortiaE() {
  const [items, setItems] = useState(null);
  const [me, setMe] = useState(null);
  const load = () => consortiumApi.mine().then((r) => setItems(r.items || [])).catch(showApiError);
  useEffect(() => { vendorApi.me().then((v) => setMe(v.id)).catch(() => {}); load(); }, []);
  return (
    <VendorPortalChrome active="/vendor/consortia">
      <div data-testid="consortia-page">
      <div className="sp-head"><div><div className="pmc-eyebrow">Consortium bidding</div><h1 data-testid="consortia-heading">My consortia</h1></div></div>
      <p className="text-sm text-slate-600 mb-4">Teams you lead or have been invited to. A lead starts a consortium from the bid page of a tender that accepts consortium bids.</p>
      <div className="space-y-3" data-testid="consortia-list">
        {(items || []).map((c) => <ConsortiumCard key={c.id} c={c} me={me} onChange={load} />)}
        {items && !items.length && <div className="text-sm text-slate-600" data-testid="consortia-empty">You are not in any consortium yet.</div>}
      </div>
      <MyConsortiumPayouts />
      </div>
    </VendorPortalChrome>
  );
}
