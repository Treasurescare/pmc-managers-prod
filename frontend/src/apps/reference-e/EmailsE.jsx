import { useEffect } from "react";
import { useUiTheme } from "@/context/UiThemeContext";

export default function EmailsE({ legacy: Legacy }) {
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
    <div data-testid="emails-e" data-pmc-e-page="emails-e">
<div className="dg-wrap"><div className="dg-intro"><div className="pmc-eyebrow">Emails</div><h1 className="pmc-display" style={{ fontSize: "40px", lineHeight: "44px", margin: "6px 0 8px" }}>Notification emails</h1><p className="pmc-muted" style={{ margin: "0", maxWidth: "780px" }}>600px single column. Subject says what happened and to what; preheader says what to do. One button. Every email carries its ledger reference.</p></div><div className="em-grid"><div className="em"><div className="em-meta"><b>New tender matches your KYC: Turnkey IVF Laboratory Setup</b><span>USD 2,100,000 · Kazakhstan · closes 30 Sep</span></div>
<div className="em-card"><div className="em-top"><span className="em-brand">PMC Managers</span><span className="em-sub">Global Tender Board</span></div>
<div className="em-b"><div className="em-eb">New matched tender</div><h2>Turnkey IVF Laboratory Setup</h2><table className="em-kv"><tr><td>Reference</td><td>PMC-NOT-2026-0055</td></tr><tr><td>Budget</td><td>USD 2,100,000</td></tr><tr><td>EMD</td><td>3% of bid</td></tr><tr><td>Closes</td><td>30 Sep 2026, 21:48 Almaty</td></tr></table><p>Your licences match 4 of 4 requirements.</p><a href="#" className="em-cta">View tender</a></div>
<div className="em-f"><span className="em-ref">notice.publish #1872</span><br />You get this because of your alert settings. <a href="#">Change alerts</a> · <a href="#">Help</a><br />PMC Managers Limited</div></div></div><div className="em"><div className="em-meta"><b>Corrigendum 1 issued for PMC-NOT-2026-0055</b><span>Clause 4.2 ISO classes changed</span></div>
<div className="em-card"><div className="em-top"><span className="em-brand">PMC Managers</span><span className="em-sub">Global Tender Board</span></div>
<div className="em-b"><div className="em-eb">Corrigendum</div><h2>A tender you follow has changed</h2><p>Clause 4.2 now sets ISO Class 5 at workstations and chambers; the surrounding lab is ISO Class 7.</p><p className="em-note">Your sealed bid is unaffected. If you need to update it, unseal and re-seal before the deadline.</p><a href="#" className="em-cta">See what changed</a></div>
<div className="em-f"><span className="em-ref">corrigendum.issue #1880</span><br />You get this because of your alert settings. <a href="#">Change alerts</a> · <a href="#">Help</a><br />PMC Managers Limited</div></div></div><div className="em"><div className="em-meta"><b>24 hours left: Turnkey IVF Laboratory Setup</b><span>Your bid is not sealed yet — EMD pending</span></div>
<div className="em-card"><div className="em-top"><span className="em-brand">PMC Managers</span><span className="em-sub">Global Tender Board</span></div>
<div className="em-b"><div className="em-eb">Deadline reminder</div><h2>24 hours to submit</h2><table className="em-kv"><tr><td>Your bid</td><td>PMC-BID-2026-00017</td></tr><tr><td>Still to do</td><td>Pay EMD · USD 61,380</td></tr><tr><td>Closes</td><td>30 Sep 2026, 21:48 Almaty</td></tr></table><a href="#" className="em-cta">Finish your bid</a></div>
<div className="em-f"><span className="em-ref">reminder · 24h</span><br />You get this because of your alert settings. <a href="#">Change alerts</a> · <a href="#">Help</a><br />PMC Managers Limited</div></div></div><div className="em"><div className="em-meta"><b>EMD confirmed for PMC-BID-2026-00020</b><span>INR 1,240,000 received by escrow</span></div>
<div className="em-card"><div className="em-top"><span className="em-brand">PMC Managers</span><span className="em-sub">Global Tender Board</span></div>
<div className="em-b"><div className="em-eb">EMD confirmed</div><h2>Escrow has your deposit</h2><table className="em-kv"><tr><td>Amount</td><td>INR 1,240,000</td></tr><tr><td>Bid</td><td>PMC-BID-2026-00020</td></tr><tr><td>Next step</td><td>Review, sign &amp; seal</td></tr></table><a href="#" className="em-cta">Continue your bid</a></div>
<div className="em-f"><span className="em-ref">escrow.confirm #1911</span><br />You get this because of your alert settings. <a href="#">Change alerts</a> · <a href="#">Help</a><br />PMC Managers Limited</div></div></div><div className="em"><div className="em-meta"><b>You've been awarded: OPD Building Renovation — Block C</b><span>Letter of award ready to sign</span></div>
<div className="em-card"><div className="em-top"><span className="em-brand">PMC Managers</span><span className="em-sub">Global Tender Board</span></div>
<div className="em-b"><div className="em-eb">Award</div><h2>Congratulations — you've been awarded</h2><table className="em-kv"><tr><td>Award</td><td>PMC-AWD-2026-00027</td></tr><tr><td>Value</td><td>KZT 812,000,000</td></tr><tr><td>Sign by</td><td>30 Sep 2026</td></tr></table><a href="#" className="em-cta">Review &amp; sign</a></div>
<div className="em-f"><span className="em-ref">award.issue #1945</span><br />You get this because of your alert settings. <a href="#">Change alerts</a> · <a href="#">Help</a><br />PMC Managers Limited</div></div></div><div className="em"><div className="em-meta"><b>Result: Modular Operation Theatres — Wave 1</b><span>Not awarded · your debrief is ready</span></div>
<div className="em-card"><div className="em-top"><span className="em-brand">PMC Managers</span><span className="em-sub">Global Tender Board</span></div>
<div className="em-b"><div className="em-eb">Result</div><h2>Thank you for bidding</h2><p>This tender was awarded to another bidder. Your bid ranked <b>2 of 4</b> with a technical score of <b>78</b>; your price was 7% above L1.</p><p className="em-note">Your EMD of USD 30,600 will be refunded to your account on file.</p><a href="#" className="em-cta">Read your debrief</a></div>
<div className="em-f"><span className="em-ref">award.issue #1702</span><br />You get this because of your alert settings. <a href="#">Change alerts</a> · <a href="#">Help</a><br />PMC Managers Limited</div></div></div></div></div>
    </div>
  );
}
