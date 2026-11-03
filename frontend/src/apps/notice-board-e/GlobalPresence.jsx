export const OFFICES_OPEN = ["United Kingdom", "Malaysia"];
export const OFFICES_OPENING = ["India", "United States", "Kazakhstan"];

export default function GlobalPresence() {
  const Pill = ({ name, open }) => (
    <div className="pmc-panel" style={{ padding: "18px 20px", display: "flex", justifyContent: "space-between", alignItems: "center", gap: "12px" }}
         data-testid={`office-${name.toLowerCase().replace(/\s+/g, "-")}`}>
      <b>{name}</b>
      <span className="pmc-muted" style={{ fontSize: "12px", letterSpacing: ".08em", textTransform: "uppercase", color: open ? "var(--brass)" : undefined }}>
        {open ? "Office open" : "Opening soon"}
      </span>
    </div>);
  return (
    <section className="pmc-wrap" style={{ padding: "72px 0" }} data-testid="global-presence">
      <div className="pmc-split-2" style={{ display: "grid", gridTemplateColumns: ".8fr 1.2fr", gap: "56px", alignItems: "start" }}>
        <div>
          <div className="pmc-eyebrow">Global presence</div>
          <h2 className="pmc-display" style={{ fontSize: "44px", lineHeight: "48px", margin: "10px 0 16px" }}>A global grid, with people on the ground</h2>
          <p className="pmc-muted" style={{ fontSize: "16px", lineHeight: "26px", margin: 0 }}>The Global Tender Grid serves buyers and suppliers in every country. Our teams work from offices in the United Kingdom and Malaysia, and we are opening offices in India, the United States and Kazakhstan.</p>
        </div>
        <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "12px" }}>
          {OFFICES_OPEN.map((n) => <Pill key={n} name={n} open />)}
          {OFFICES_OPENING.map((n) => <Pill key={n} name={n} />)}
        </div>
      </div>
    </section>);
}
