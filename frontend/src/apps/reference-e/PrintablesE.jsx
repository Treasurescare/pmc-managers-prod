import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function PrintablesE({ legacy: Legacy }) {
  const { isE } = useUiTheme();
  useEffect(() => {
    if (!isE) return;
    const tick = () => {
      document.querySelectorAll("[data-in]").forEach((el) => {
        const secs = parseInt(el.getAttribute("data-in") || "0", 10);
        if (!secs) return;
        const d = Math.floor(secs/86400), h = Math.floor((secs%86400)/3600), m = Math.floor((secs%3600)/60);
        el.textContent = d>0 ? `${d}d ${h}h` : h>0 ? `${h}h ${m}m` : `${m}m`;
      });
    };
    tick();
  }, [isE]);
  if (!isE && Legacy) return <Legacy />;
  if (!isE) return null;
  return (
    <div data-testid="printables-e" data-pmc-e-page="printables-e">
<div className="dg-wrap"><div className="dg-intro"><div className="pmc-eyebrow">Printable documents</div><h1 className="pmc-display" style={{ fontSize: "40px", lineHeight: "44px", margin: "6px 0 8px" }}>PDFs and prints</h1><p className="pmc-muted" style={{ margin: "0", maxWidth: "780px" }}>A4, black ink first with brass for the seal only. Every page carries its reference and a verify link; award and minutes carry the ledger event.</p></div><div className="pr-grid"><div><div className="a4"><div className="a4-h"><div><div className="a4-brand">PMC Managers Limited</div><div className="a4-sub">Global Tender Grid</div></div><div className="a4-ref">PMC-NOT-2026-0055</div></div><div className="a4-t">Notice Inviting Tender</div><h1>Turnkey IVF Laboratory Setup — Embryology Lab, Cryopreservation &amp; Cleanroom HVAC</h1>
<table className="a4-kv"><tr><td>Reference</td><td>PMC-NOT-2026-0055</td></tr><tr><td>Type</td><td>Open tender · 3 covers</td></tr><tr><td>Indicative budget</td><td>USD 2,100,000</td></tr><tr><td>EMD</td><td>3% of bid value</td></tr><tr><td>Submission closes</td><td>30 Sep 2026, 21:48 Almaty</td></tr><tr><td>Delivery</td><td>Kazakhstan</td></tr></table>
<h2>1. Scope</h2><p>Turnkey design and build of an ISO Class 5/7 embryology laboratory including cleanroom HVAC, cryopreservation storage and full workstation fit-out.</p><h2>2. Eligibility</h2><p>Registered suppliers with approved KYC; two completed cleanroom projects of USD 1M+ in five years; Kazakhstan licences for electrical, mechanical, plumbing &amp; firefighting.</p><div className="a4-f"><span>Page 1 of 3</span><span>Verify at pmcmanagers.com/verify · PMC-NOT-2026-0055</span></div></div><div className="cap">Notice inviting tender</div></div><div><div className="a4"><div className="a4-h"><div><div className="a4-brand">PMC Managers Limited</div><div className="a4-sub">Global Tender Grid</div></div><div className="a4-ref">PMC-AWD-2026-00025</div></div><div className="a4-t">Award Notice</div><h1>Modular Operation Theatres (OTs) — Wave 2</h1>
<table className="a4-kv"><tr><td>Award</td><td>PMC-AWD-2026-00025</td></tr><tr><td>Notice</td><td>PMC-NOT-2026-0016</td></tr><tr><td>Awarded to</td><td>Supplier A (sample)</td></tr><tr><td>Award value</td><td>USD 900,000</td></tr><tr><td>Bids received</td><td>6 · 4 technically qualified</td></tr><tr><td>Basis</td><td>Lowest evaluated price among qualified bids</td></tr><tr><td>Awarded</td><td>12 Sep 2026</td></tr></table>
<div className="a4-seal"><svg viewBox="0 0 100 100" width="84" height="84"><circle cx="50" cy="50" r="46" fill="none" stroke="var(--brass)" stroke-width="2" /><circle cx="50" cy="50" r="36" fill="none" stroke="var(--brass)" /><text x="50" y="47" text-anchor="middle" font-size="9" font-weight="700" fill="var(--brass-text)" font-family="var(--font-sans)">LEDGER</text><text x="50" y="59" text-anchor="middle" font-size="9" fill="var(--brass-text)" font-family="var(--font-mono)">#1745</text></svg><div><b>Sealed on the audit ledger</b><br />award.issue #1745 · f7a0…9d12</div></div><div className="a4-f"><span>Page 1 of 3</span><span>Verify at pmcmanagers.com/verify · PMC-AWD-2026-00025</span></div></div><div className="cap">Award notice</div></div><div><div className="a4"><div className="a4-h"><div><div className="a4-brand">PMC Managers Limited</div><div className="a4-sub">Global Tender Grid</div></div><div className="a4-ref">PMC-NOT-2026-0055 · CS</div></div><div className="a4-t">Comparative Statement</div><h1>Turnkey IVF Laboratory Setup</h1><p className="a4-m">PMC-NOT-2026-0055 · commercial opened 2 Oct 2026 · estimate USD 2,100,000</p>
<table className="a4-tb"><tr><th>Rank</th><th>Bidder</th><th>Technical</th><th>Price (USD)</th><th>vs estimate</th></tr><tr><td>L1</td><td>Emerald Corporates</td><td>89</td><td>2,046,000</td><td>−2.6%</td></tr><tr><td>L2</td><td>Bidder B</td><td>82</td><td>2,188,500</td><td>+4.2%</td></tr><tr><td>—</td><td>Bidder C</td><td>47 · failed</td><td>Not opened</td><td>—</td></tr></table>
<h2>Recommendation</h2><p>Award to the L1 bidder, Emerald Corporates, at USD 2,046,000, USD 54,000 below the estimate.</p>
<table className="a4-sig"><tr><td>Procurement head</td><td>Medical engineer</td><td>Independent adviser</td></tr><tr><td className="l"></td><td className="l"></td><td className="l"></td></tr></table><div className="a4-f"><span>Page 1 of 3</span><span>Verify at pmcmanagers.com/verify · PMC-NOT-2026-0055 · CS</span></div></div><div className="cap">Comparative statement</div></div><div><div className="a4"><div className="a4-h"><div><div className="a4-brand">PMC Managers Limited</div><div className="a4-sub">Global Tender Grid</div></div><div className="a4-ref">PMC-NOT-2026-0055 · MIN</div></div><div className="a4-t">Minutes of Evaluation Committee</div><h1>Technical evaluation · PMC-NOT-2026-0055</h1><p className="a4-m">1 Oct 2026, 10:00–12:30 · online · quorum 3 of 2</p>
<h2>Present</h2><p>Procurement head (chair), Medical engineer, Independent adviser (external). All declared no conflict of interest.</p>
<h2>Proceedings</h2><ol><li>Three technical envelopes opened at 10:02; opening recorded as envelope.open #1918.</li><li>Members scored independently against six weighted criteria.</li><li>Scores for Bidder C on ISO 14644 validation differed by more than 30%; consensus reached at 8 of 20 with the reason noted.</li><li>Bidder C did not meet the minimum of 60 and is not qualified.</li></ol>
<h2>Decision</h2><p>Technical scores locked at 12:24 (eval.lock #1938). Commercial envelopes of qualified bidders to open on 2 Oct 2026.</p><div className="a4-f"><span>Page 1 of 3</span><span>Verify at pmcmanagers.com/verify · PMC-NOT-2026-0055 · MIN</span></div></div><div className="cap">Committee minutes</div></div></div></div>
    </div>
  );
}
