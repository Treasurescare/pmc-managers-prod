import { useState } from "react";

const KEY = "pmc_launch_banner_closed";

export default function LaunchBanner() {
  const [closed, setClosed] = useState(() => localStorage.getItem(KEY) === "1");
  if (closed) return null;
  const close = () => { localStorage.setItem(KEY, "1"); setClosed(true); };
  return (
    <div style={{ background: "var(--brass, #d9bd72)", color: "#162921" }} data-testid="launch-banner">
      <div className="pmc-wrap" style={{ display: "flex", alignItems: "center", gap: "14px", flexWrap: "wrap", padding: "10px 0", fontSize: "14px" }}>
        <b style={{ letterSpacing: ".08em", textTransform: "uppercase", fontSize: "12px" }}>Now open for registrations</b>
        <span style={{ flex: "1 1 320px" }}>Be among the first buyers and suppliers on the Global Tender Grid. Registration is open worldwide.</span>
        <a href="/register" className="pmc-btn pmc-btn--primary pmc-btn--sm" data-testid="launch-banner-supplier">Register as supplier</a>
        <a href="/contact" className="pmc-btn pmc-btn--secondary pmc-btn--sm" data-testid="launch-banner-buyer">Issue your first tender</a>
        <button type="button" onClick={close} aria-label="Close announcement" data-testid="launch-banner-close"
          style={{ background: "none", border: 0, fontSize: "20px", lineHeight: 1, cursor: "pointer", color: "#162921" }}>×</button>
      </div>
    </div>);
}
