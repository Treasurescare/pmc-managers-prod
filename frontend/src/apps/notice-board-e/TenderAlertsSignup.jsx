import { useEffect, useState } from "react";
import { marketingApi, publicApi, showApiError } from "@/lib/api";
import UnspscPicker from "@/components/UnspscPicker";

export default function TenderAlertsSignup() {
  const [f, setF] = useState({ email: "", audience: "vendor", country: "", category: "", consent: false, website: "" });
  const [countries, setCountries] = useState([]);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  useEffect(() => { publicApi.countries().then((c) => setCountries(Array.isArray(c) ? c : (c.items || []))).catch(() => {}); }, []);
  const submit = async (e) => {
    e.preventDefault();
    setBusy(true);
    try {
      await marketingApi.subscribe({ email: f.email, audience: f.audience, country: f.country,
        categories: f.category ? [f.category] : [], consent: f.consent, website: f.website });
      setDone(true);
    } catch (err) { showApiError(err); } finally { setBusy(false); }
  };
  const code = (c) => (Array.isArray(c) ? c[0] : (c.code || c.iso || c.value));
  const name = (c) => (Array.isArray(c) ? c[1] : (c.name || c.label || code(c)));
  return (
    <section className="pmc-wrap" style={{ padding: "72px 0 0" }} data-testid="tender-alerts-signup">
      <div className="pmc-card" style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(280px,1fr))", gap: "40px", padding: "40px", alignItems: "center" }}>
        <div>
          <div className="pmc-eyebrow">Free tender alerts</div>
          <h2 className="pmc-display" style={{ fontSize: "40px", lineHeight: "44px", margin: "10px 0 12px" }}>Get new tenders in your inbox</h2>
          <p className="pmc-muted" style={{ fontSize: "16px", lineHeight: "26px", margin: 0 }}>Tell us what you do and we'll email you new tenders that match. No account needed. Unsubscribe in one click.</p>
        </div>
        {done ? (
          <div data-testid="signup-done" style={{ fontSize: "17px", lineHeight: "28px" }}>
            <b>Check your inbox.</b> We've sent a confirmation link to {f.email}. Your alerts start once you click it.
          </div>
        ) : (
          <form onSubmit={submit} style={{ display: "grid", gap: "12px" }}>
            <input className="pmc-input" type="email" required placeholder="Work email" value={f.email} onChange={(e) => setF({ ...f, email: e.target.value })} data-testid="signup-email" />
            <input type="text" tabIndex={-1} autoComplete="off" value={f.website} onChange={(e) => setF({ ...f, website: e.target.value })} style={{ position: "absolute", left: "-9999px" }} aria-hidden="true" />
            <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit,minmax(160px,1fr))", gap: "12px" }}>
              <select className="pmc-input" value={f.audience} onChange={(e) => setF({ ...f, audience: e.target.value })} data-testid="signup-audience">
                <option value="vendor">I'm a supplier</option><option value="buyer">I issue tenders</option></select>
              <select className="pmc-input" value={f.country} onChange={(e) => setF({ ...f, country: e.target.value })} data-testid="signup-country">
                <option value="">Any country</option>
                {countries.map((c) => <option key={code(c)} value={code(c)}>{name(c)}</option>)}</select>
            </div>
            <div data-testid="signup-category">
              <UnspscPicker testidPrefix="signup-category-unspsc" value={f.category ? " " : ""} title={f.category} hideValue inputClassName="pmc-input flex-1"
                placeholder="What do you supply? e.g. solar, wind, cement (blank = all)" onChange={(r) => setF({ ...f, category: r.title })} />
            </div>
            <label style={{ display: "flex", gap: "10px", fontSize: "13px", lineHeight: "20px", alignItems: "flex-start" }}>
              <input type="checkbox" checked={f.consent} onChange={(e) => setF({ ...f, consent: e.target.checked })} data-testid="signup-consent" />
              <span>I agree to receive tender alerts and occasional updates from PMC Managers by email. I can unsubscribe at any time.</span>
            </label>
            <button className="pmc-btn pmc-btn--primary" type="submit" disabled={busy || !f.consent || !f.email} data-testid="signup-submit">{busy ? "Sending…" : "Get tender alerts"}</button>
          </form>
        )}
      </div>
    </section>
  );
}
