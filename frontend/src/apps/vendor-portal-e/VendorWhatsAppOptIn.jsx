import { useEffect, useState } from "react";
import { toast } from "sonner";
import { whatsappApi, showApiError } from "@/lib/api";

export const VendorWhatsAppOptIn = () => {
  const [f, setF] = useState(null);
  const [busy, setBusy] = useState(false);
  useEffect(() => { whatsappApi.mine().then(setF).catch(() => setF(null)); }, []);
  if (!f) return null;
  const save = async (opt_in) => {
    setBusy(true);
    try {
      const r = await whatsappApi.saveMine({ number: f.number, opt_in });
      setF({ ...f, ...r });
      toast.success(r.opt_in ? "WhatsApp alerts switched on" : "WhatsApp alerts switched off");
    } catch (e) { showApiError(e); } finally { setBusy(false); }
  };
  return (
    <section className="pmc-panel" style={{ padding: "14px 16px", marginBottom: "14px" }} data-testid="vendor-wa-optin">
      <div className="pmc-eyebrow" style={{ marginBottom: "6px" }}>WhatsApp alerts</div>
      <p className="pmc-muted" style={{ fontSize: "13px", margin: "0 0 10px" }}>
        Get new tenders in your categories, payment reminders and receipts on WhatsApp. Reply STOP anytime to switch off.
      </p>
      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap", alignItems: "center" }}>
        <input className="pmc-input" style={{ maxWidth: "240px" }} placeholder="e.g. 447700900123" value={f.number || ""} disabled={f.opt_in}
               onChange={(e) => setF({ ...f, number: e.target.value })} data-testid="vendor-wa-number" />
        {f.opt_in
          ? <button className="pmc-btn pmc-btn--secondary" disabled={busy} onClick={() => save(false)} data-testid="vendor-wa-off">Switch off</button>
          : <button className="pmc-btn pmc-btn--primary" disabled={busy || !f.number} onClick={() => save(true)} data-testid="vendor-wa-on">I agree — send me WhatsApp alerts</button>}
        <span className="pmc-muted" style={{ fontSize: "12px" }} data-testid="vendor-wa-state">{f.opt_in ? "On" : "Off"}</span>
      </div>
    </section>
  );
};
