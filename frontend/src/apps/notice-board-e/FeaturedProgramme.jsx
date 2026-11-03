import { useEffect, useState } from "react";
import { siteApi } from "@/lib/api";

const ICONS = ["i-box", "i-file", "i-home", "i-layers", "i-users", "i-coin", "i-shield", "i-chart"];

export function useFeaturedProgramme() {
  const [p, setP] = useState(null);
  useEffect(() => { siteApi.programme().then(setP).catch(() => setP({ enabled: false })); }, []);
  return p;
}

export default function FeaturedProgramme({ p }) {
  if (!p?.enabled || !p.title) return null;
  const link = p.tenders_link || "/tenders/live";
  return (
    <section className="pmc-wrap" style={{ padding: "88px 0" }} data-testid="featured-programme">
      <div className="pmc-split-2" style={{ display: "grid", gridTemplateColumns: ".9fr 1.1fr", gap: "56px", alignItems: "start" }}>
        <div>
          <div className="pmc-eyebrow">{p.eyebrow || "Programme spotlight"}</div>
          <h2 className="pmc-display" style={{ fontSize: "48px", lineHeight: "52px", margin: "10px 0 16px" }} data-testid="featured-programme-title">{p.title}</h2>
          {p.summary && <p className="pmc-muted" style={{ fontSize: "17px", lineHeight: "28px", margin: "0 0 24px" }}>{p.summary}</p>}
          <div style={{ display: "flex", gap: "12px", flexWrap: "wrap" }}>
            <a href={link} className="pmc-btn pmc-btn--primary pmc-btn--lg" data-testid="featured-programme-tenders">See programme tenders</a>
            {p.brief_url && <a href={p.brief_url} className="pmc-btn pmc-btn--secondary pmc-btn--lg" target="_blank" rel="noreferrer" data-testid="featured-programme-brief">Download the brief</a>}
          </div>
        </div>
        <div className="pmc-cats">{(p.highlights || []).map((x, i) => (
          <a key={x.title} href={link} className="pmc-cat" data-testid={`featured-programme-item-${i}`}>
            <svg className="pmc-ico" aria-hidden="true"><use href={`#${ICONS[i % ICONS.length]}`} /></svg>
            <div><h3>{x.title}</h3>{x.text && <p>{x.text}</p>}</div>
            <svg className="pmc-ico pmc-cat__go" aria-hidden="true"><use href="#i-arrow" /></svg>
          </a>))}</div>
      </div>
    </section>
  );
}
