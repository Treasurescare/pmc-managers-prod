import { useEffect, useState } from "react";
import { toast } from "sonner";
import { whatsappApi, showApiError } from "@/lib/api";
import { WhatsAppInbox } from "./WhatsAppInbox";

const TOGGLES = [["tender_alerts", "New-tender alerts to opted-in suppliers"], ["payment_msgs", "Payment reminders and receipts"],
  ["ai_autoreply", "Ask PMC assistant answers incoming messages"]];

export const WhatsAppTab = () => {
  const [st, setSt] = useState(null);
  const [num, setNum] = useState("");
  const load = () => whatsappApi.status().then(setSt).catch(showApiError);
  useEffect(() => { load(); }, []);
  const toggle = async (k) => {
    try { const s = await whatsappApi.saveSettings({ ...st.settings, [k]: !st.settings[k] }); setSt({ ...st, settings: s }); }
    catch (e) { showApiError(e); }
  };
  const test = async () => {
    try { const r = await whatsappApi.test(num); r.sent ? toast.success("Test message sent") : toast.error("WhatsApp rejected the test — check the conversation for details"); }
    catch (e) { showApiError(e); }
  };
  if (!st) return null;
  return (
    <div className="space-y-5" data-testid="mkt-whatsapp">
      <div className="border border-brand-navy/20 bg-white p-4 space-y-3">
        <div className="flex items-center gap-3">
          <span className={"px-2 py-0.5 text-xs uppercase " + (st.configured ? "bg-emerald-700 text-white" : "bg-amber-500 text-white")} data-testid="wa-status">
            {st.configured ? "Connected" : "Not connected yet"}</span>
          <span className="text-sm">{st.opted_in} supplier(s) opted in to WhatsApp</span>
        </div>
        <div className="text-xs text-brand-navy/70">Webhook URL for Meta: <code data-testid="wa-webhook-url">{st.webhook_url}</code></div>
        <div className="text-xs text-brand-navy/70">Approved templates needed: {st.templates.join(", ")} (language: {st.settings.template_lang})</div>
        <div className="space-y-2 pt-2">
          {TOGGLES.map(([k, l]) => (
            <label key={k} className="flex items-center gap-2 text-sm">
              <input type="checkbox" checked={!!st.settings[k]} onChange={() => toggle(k)} data-testid={`wa-toggle-${k}`} />{l}
            </label>))}
        </div>
        <div className="flex gap-2 pt-2 max-w-md">
          <input className="px-3 py-2 border border-brand-navy/20 text-sm flex-1" placeholder="Your number, e.g. 447700900123" value={num}
                 onChange={(e) => setNum(e.target.value)} data-testid="wa-test-number" />
          <button className="pmc-btn pmc-btn--secondary" disabled={!st.configured || !num} onClick={test} data-testid="wa-test-send">Send test</button>
        </div>
      </div>
      <WhatsAppInbox />
    </div>
  );
};
