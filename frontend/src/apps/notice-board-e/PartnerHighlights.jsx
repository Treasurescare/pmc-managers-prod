import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { agentApi } from "@/lib/api";

export default function PartnerHighlights() {
  const [d, setD] = useState(null);
  useEffect(() => { agentApi.highlights().then(setD).catch(() => {}); }, []);
  if (!d?.items?.length) return null;
  const monthName = new Date(`${d.month}-01T00:00:00Z`).toLocaleString(undefined, { month: "long", year: "numeric", timeZone: "UTC" });
  return (
    <section className="pmc-wrap" style={{ padding: "72px 0 0" }} data-testid="home-partner-highlights">
      <div className="pmc-eyebrow">PMC partner network</div>
      <h2 className="pmc-display" style={{ fontSize: "40px", lineHeight: "46px", margin: "10px 0 8px" }}>Partners of the month <em style={{ color: "var(--brass, #A8843A)" }}>· {monthName}{d.live ? " so far" : ""}</em></h2>
      <p className="pmc-muted" style={{ margin: "0 0 24px", maxWidth: 640 }}>Partners introduce and onboard verified suppliers to PMC Managers. Here are this month's stand-outs.</p>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))", gap: 16 }}>
        {d.items.map((x) => (
          <div key={`${x.badge}-${x.partner}`} className="pmc-card" style={{ padding: 20, border: "1px solid rgba(15,59,46,.15)", background: "#fff" }} data-testid={`home-badge-${x.badge}`}>
            <div style={{ fontSize: 11, letterSpacing: "1.5px", textTransform: "uppercase", color: "#8A6A1F", fontWeight: 700 }}>★ {x.label}</div>
            {x.photo_url && <img src={`${process.env.REACT_APP_BACKEND_URL}${x.photo_url}`} alt={x.partner} style={{ width: 72, height: 72, objectFit: "cover", marginTop: 12, border: "1px solid rgba(15,59,46,.15)" }} data-testid={`home-badge-photo-${x.code}`} />}
            <div style={{ fontSize: 22, fontWeight: 600, margin: "8px 0 4px" }}>{x.partner}</div>
            <div className="pmc-muted" style={{ fontSize: 13 }}>{x.approved} supplier{x.approved === 1 ? "" : "s"} approved · {x.invites} invite{x.invites === 1 ? "" : "s"}</div>
            {x.bio && <p style={{ fontSize: 14, lineHeight: "21px", margin: "10px 0 0" }} data-testid={`home-badge-bio-${x.code}`}>{x.bio}</p>}
          </div>))}
      </div>
      <div style={{ marginTop: 20 }}><Link to="/partner/register" className="pmc-btn pmc-btn--secondary" data-testid="home-become-partner">Become a PMC partner</Link></div>
    </section>
  );
}
