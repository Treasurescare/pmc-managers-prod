import { useState } from "react";
import { toast } from "sonner";
import { siteApi, showApiError } from "@/lib/api";

const Row = ({ k, v, ok }) => (
  <div className="flex justify-between gap-3 text-sm py-1 border-b border-brand-navy/10"><span className="text-brand-navy/60">{k}</span>
    <span className={ok === false ? "text-red-700 font-semibold" : ok ? "text-emerald-700 font-semibold" : ""}>{v}</span></div>
);

export default function EmailHealthCard() {
  const [h, setH] = useState(null);
  const [to, setTo] = useState("");
  const [busy, setBusy] = useState(false);
  const check = () => { setBusy(true); siteApi.emailHealth().then(setH).catch(showApiError).finally(() => setBusy(false)); };
  const send = () => {
    setBusy(true);
    siteApi.emailTest(to).then((r) => (r.ok ? toast.success(`Test email sent to ${to} — check the inbox (and spam)`) : toast.error(`Not sent. ${r.error}`, { duration: 20000 })))
      .catch(showApiError).finally(() => setBusy(false));
  };
  return (
    <div className="bg-white border border-brand-navy/15 p-4 space-y-3" data-testid="email-health-card">
      <div className="font-semibold">Email health check</div>
      <p className="text-xs text-brand-navy/60">Checks this server's email settings with Resend and sends a real test email.</p>
      <button type="button" className="pmc-btn pmc-btn--secondary" disabled={busy} onClick={check} data-testid="email-health-check">Check email setup</button>
      {h && (
        <div data-testid="email-health-result">
          <Row k="Resend key on server" v={h.resend_key_set ? "Set" : "Missing"} ok={h.resend_key_set} />
          <Row k="Key accepted by Resend" v={h.domains.ok ? "Yes" : h.domains.error} ok={h.domains.ok} />
          <Row k="Sender" v={`${h.from_name || ""} <${h.from_address || "not set"}>`} />
          <Row k={`Domain ${h.sender_domain || ""}`} v={h.domains.send_only ? "not readable with a send-only key" : h.sender_domain_status || "not added in Resend"} ok={h.domains.send_only ? undefined : h.sender_domain_status === "verified"} />
          {(h.tips || []).map((t) => <div key={t} className="text-sm text-amber-800 bg-amber-50 border border-amber-200 p-2 mt-2" data-testid="email-health-tip">{t}</div>)}
          {!h.tips?.length && <div className="text-sm text-emerald-700 mt-2" data-testid="email-health-ok">Everything looks right. Send a test to be sure.</div>}
        </div>
      )}
      <div className="flex gap-2 flex-wrap">
        <input type="email" className="flex-1 min-w-[220px] px-3 py-2 border border-brand-navy/20 text-sm" placeholder="Send a test to…" value={to} onChange={(e) => setTo(e.target.value)} data-testid="email-test-to" />
        <button type="button" className="pmc-btn pmc-btn--primary" disabled={busy || !to.includes("@")} onClick={send} data-testid="email-test-send">Send test email</button>
      </div>
    </div>
  );
}
