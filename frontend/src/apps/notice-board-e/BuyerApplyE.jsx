import { useState } from "react";
import { toast } from "sonner";
import PublicChrome from "@/apps/shared/PublicChrome";
import { useSeo } from "@/lib/useSeo";
import { growthApi } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";

const TYPES = [["bank", "Bank / financial institution"], ["government", "Government department"], ["psu", "Public sector undertaking (PSU)"],
  ["private", "Private company"], ["ngo", "NGO / development agency"], ["other", "Other"]];

export default function BuyerApplyE() {
  useSeo({ title: "Register your organisation to issue tenders | Global Tender Grid", description: "Banks, government departments, PSUs and companies can apply to run e-tenders on PMC Managers." });
  const [f, setF] = useState({ org_name: "", org_type: "private", country: "", contact_name: "", email: "", phone: "", website: "", tenders_per_year: "", message: "" });
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);
  const up = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const send = async (e) => {
    e.preventDefault();
    if (!f.org_name.trim() || f.country.trim().length !== 2 || !f.contact_name.trim() || !f.email.trim()) return toast.error("Fill in organisation, 2-letter country code, contact name and email.");
    setBusy(true);
    try {
      await growthApi.applyBuyer({ ...f, country: f.country.toUpperCase(), tenders_per_year: f.tenders_per_year === "" ? null : Number(f.tenders_per_year),
        phone: f.phone || null, website: f.website || null, message: f.message || null });
      setDone(true);
    } catch (err) { showApiError(err); } finally { setBusy(false); }
  };
  const inp = "pmc-input mt-1 w-full";
  return (
    <PublicChrome testid="buyer-apply-page">
      <div className="pmc-wrap py-10 max-w-3xl">
        <div className="pmc-eyebrow">For buyers</div>
        <h1 className="text-4xl sm:text-5xl font-semibold mt-1">Register your organisation</h1>
        <p className="mt-2 text-sm">Banks, government departments, PSUs and private companies can run their own procurement dashboard on the Global Tender Grid. Apply below — we review every application and set up your account within two working days.</p>
        {done ? <div className="mt-6 bg-white border border-emerald-700/30 p-5 text-emerald-900" data-testid="buyer-apply-done">Thank you. Your application is in — we have emailed a confirmation and will be in touch shortly.</div> : (
          <form onSubmit={send} className="mt-6 grid md:grid-cols-2 gap-3 text-sm bg-white border border-black/10 p-5" data-testid="buyer-apply-form">
            <label>Organisation name<input className={inp} value={f.org_name} onChange={up("org_name")} data-testid="buyer-org-name" /></label>
            <label>Organisation type<select className={inp} value={f.org_type} onChange={up("org_type")} data-testid="buyer-org-type">{TYPES.map(([v, l]) => <option key={v} value={v}>{l}</option>)}</select></label>
            <label>Country (2-letter code)<input className={inp} maxLength={2} value={f.country} onChange={up("country")} placeholder="IN" data-testid="buyer-country" /></label>
            <label>Tenders per year (approx.)<input type="number" className={inp} value={f.tenders_per_year} onChange={up("tenders_per_year")} data-testid="buyer-tenders" /></label>
            <label>Contact name<input className={inp} value={f.contact_name} onChange={up("contact_name")} data-testid="buyer-contact" /></label>
            <label>Work email<input type="email" className={inp} value={f.email} onChange={up("email")} data-testid="buyer-email" /></label>
            <label>Phone<input className={inp} value={f.phone} onChange={up("phone")} data-testid="buyer-phone" /></label>
            <label>Website<input className={inp} value={f.website} onChange={up("website")} data-testid="buyer-website" /></label>
            <label className="md:col-span-2">What do you want to procure?<textarea rows={3} className={inp} value={f.message} onChange={up("message")} data-testid="buyer-message" /></label>
            <div className="md:col-span-2"><button className="pmc-btn pmc-btn--primary" disabled={busy} data-testid="buyer-apply-submit">{busy ? "Sending…" : "Submit application"}</button></div>
          </form>)}
      </div>
    </PublicChrome>);
}
