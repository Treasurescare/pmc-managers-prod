import { useEffect, useState } from "react";
import { toast } from "sonner";
import { marketingApi, showApiError } from "@/lib/api";
import VendorPortalChrome from "./VendorPortalChrome";

export default function VendorReferral() {
  const [d, setD] = useState(null);
  useEffect(() => { marketingApi.myReferral().then(setD).catch(showApiError); }, []);
  const copy = () => { navigator.clipboard?.writeText(d.link).then(() => toast.success("Link copied")).catch(() => {}); };
  const share = encodeURIComponent(`Join me on PMC Managers to find and bid on tenders: ${d?.link || ""}`);
  return (
    <div data-testid="vendor-referral">
      <VendorPortalChrome active="/vendor/refer">
        <div className="sp-head"><div><div className="pmc-eyebrow">Grow your network</div><h1>Refer &amp; earn</h1></div></div>
        {d && (
          <section className="pmc-panel" style={{ padding: "20px", marginBottom: "16px", maxWidth: "760px" }}>
            <p style={{ marginBottom: "12px" }}>Invite other suppliers and contractors to PMC Managers. Everyone who registers through your link is counted below.</p>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <input className="pmc-input" readOnly value={d.link} style={{ flex: 1, minWidth: "260px" }} data-testid="ref-link" />
              <button className="pmc-btn pmc-btn--primary" onClick={copy} data-testid="ref-copy">Copy link</button>
              <a className="pmc-btn" href={`https://wa.me/?text=${share}`} target="_blank" rel="noreferrer" data-testid="ref-whatsapp">WhatsApp</a>
              <a className="pmc-btn" href={`https://www.linkedin.com/sharing/share-offsite/?url=${encodeURIComponent(d.link)}`} target="_blank" rel="noreferrer" data-testid="ref-linkedin">LinkedIn</a>
              <a className="pmc-btn" href={`mailto:?subject=${encodeURIComponent("Tenders on PMC Managers")}&body=${share}`} data-testid="ref-email">Email</a>
            </div>
            <div style={{ marginTop: "18px", fontSize: "28px", fontWeight: 600 }} data-testid="ref-joined">{d.joined}</div>
            <div style={{ fontSize: "12px", opacity: 0.7 }}>companies joined through your link · code {d.code}</div>
            {d.items.length > 0 && (
              <ul style={{ marginTop: "12px" }}>
                {d.items.map((r, i) => <li key={i} style={{ fontSize: "14px", padding: "4px 0" }}>{r.company} · {r.at.slice(0, 10)}</li>)}
              </ul>)}
          </section>)}
      </VendorPortalChrome>
    </div>
  );
}
