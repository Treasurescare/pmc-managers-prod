import { useEffect, useState } from "react";
import { toast } from "sonner";
import PublicChrome from "@/apps/shared/PublicChrome";
import { useSeo } from "@/lib/useSeo";
import { growthApi } from "@/lib/growthApi";
import { showApiError } from "@/lib/api";

const RequestForm = ({ s, onClose }) => {
  const [f, setF] = useState({ name: "", email: "", company: "", phone: "", message: "", notice_ref: "" });
  const [done, setDone] = useState(false);
  const up = (k) => (e) => setF({ ...f, [k]: e.target.value });
  const send = async (pay) => {
    if (!f.name.trim() || !f.email.trim() || f.message.trim().length < 5) return toast.error("Add your name, email and a short message.");
    try {
      const r = await growthApi.requestService({ ...f, service_id: s.id, pay_now: pay, notice_ref: f.notice_ref || null, company: f.company || null, phone: f.phone || null });
      if (r.checkout_url) window.location.href = r.checkout_url; else setDone(true);
    } catch (e) { showApiError(e); }
  };
  if (done) return <div className="mt-3 text-sm text-emerald-800" data-testid={`service-request-done-${s.id}`}>Thank you — our team will contact you within one working day.</div>;
  return (
    <div className="mt-3 grid md:grid-cols-2 gap-2 text-sm" data-testid={`service-request-form-${s.id}`}>
      <input className="pmc-input" placeholder="Your name" value={f.name} onChange={up("name")} data-testid="service-req-name" />
      <input className="pmc-input" placeholder="Email" value={f.email} onChange={up("email")} data-testid="service-req-email" />
      <input className="pmc-input" placeholder="Company" value={f.company} onChange={up("company")} data-testid="service-req-company" />
      <input className="pmc-input" placeholder="Tender reference (optional)" value={f.notice_ref} onChange={up("notice_ref")} data-testid="service-req-ref" />
      <textarea className="pmc-input md:col-span-2" rows={3} placeholder="What do you need help with?" value={f.message} onChange={up("message")} data-testid="service-req-message" />
      <div className="md:col-span-2 flex flex-wrap gap-2">
        <button className="pmc-btn pmc-btn--secondary" onClick={() => send(false)} data-testid="service-req-send">Send request</button>
        {s.price ? <button className="pmc-btn pmc-btn--primary" onClick={() => send(true)} data-testid="service-req-pay">Book &amp; pay {s.currency} {Number(s.price).toLocaleString()}</button> : null}
        <button className="pmc-btn pmc-btn--ghost" onClick={onClose} data-testid="service-req-cancel">Cancel</button>
      </div>
    </div>);
};

export default function ConsultingE() {
  useSeo({ title: "Tender preparation & consultancy services | PMC Managers", description: "Professional bid writing, tender preparation and procurement advisory from PMC Managers." });
  const [items, setItems] = useState([]);
  const [open, setOpen] = useState(null);
  useEffect(() => { growthApi.services().then((r) => setItems(r.items)).catch(() => {}); }, []);
  return (
    <PublicChrome testid="consulting-page">
      <div className="pmc-wrap py-10">
        <div className="pmc-eyebrow">PMC Managers</div>
        <h1 className="text-4xl sm:text-5xl font-semibold mt-1">Tender preparation &amp; consultancy</h1>
        <p className="mt-2 max-w-2xl text-sm">Expert help for suppliers and buyers — from preparing a winning bid to running a compliant procurement.</p>
        <div className="grid gap-3 mt-6" data-testid="service-list">
          {!items.length && <div className="text-sm opacity-70" data-testid="service-empty">Services will be listed here shortly. Contact us at tenders@pmcmanagers.com.</div>}
          {items.map((s) => (
            <div key={s.id} className="bg-white border border-black/10 p-5" data-testid={`service-${s.id}`}>
              <div className="flex flex-wrap items-start gap-3">
                <div className="flex-1 min-w-[240px]"><div className="font-semibold text-lg">{s.name}</div><p className="text-sm mt-1 whitespace-pre-line">{s.summary}</p></div>
                <div className="text-right"><div className="font-semibold" data-testid={`service-price-${s.id}`}>{s.price ? `${s.currency} ${Number(s.price).toLocaleString()}` : (s.price_note || "Price on request")}</div>
                  <button className="pmc-btn pmc-btn--primary mt-2" onClick={() => setOpen(open === s.id ? null : s.id)} data-testid={`service-request-${s.id}`}>Request this service</button></div>
              </div>
              {open === s.id && <RequestForm s={s} onClose={() => setOpen(null)} />}
            </div>))}
        </div>
      </div>
    </PublicChrome>);
}
