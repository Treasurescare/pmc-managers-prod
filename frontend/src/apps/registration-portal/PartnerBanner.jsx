import { useState } from "react";
import { toast } from "sonner";
import { agentApi, showApiError } from "@/lib/api";

export default function PartnerBanner({ reg, token, onRevoked, onMode }) {
  const [busy, setBusy] = useState(false);
  const p = reg.partner;
  if (!p) return null;
  if (reg.editor === "partner") {
    return (
      <div className="mt-4 bg-amber-50 border border-amber-300 p-3 text-sm" data-testid="partner-edit-banner">
        You're filling this form as partner <b>{p.code}</b>. Every change is logged with your code. Declarations and signature are left for the supplier — when you're done, use <b>Send to supplier for review</b> in your partner portal.
      </div>
    );
  }
  const revoke = async () => {
    if (!window.confirm("Remove this partner's access to your registration?")) return;
    setBusy(true);
    try { await agentApi.revokePartner(reg.id, token); toast.success("Partner access removed"); onRevoked(); } catch (e) { showApiError(e); } finally { setBusy(false); }
  };
  const fields = (p.fields || []).map((f) => f.replace(/^document:/, "doc: ").replace(/_/g, " "));
  const mode = async (m) => {
    let name = "";
    if (m === "partner") {
      name = window.prompt(`Type your full name to let partner ${p.code} fill your form (you accept the partner consent statements from the invitation):`) || "";
      if (name.trim().length < 3) return;
    }
    try { const r = await agentApi.switchMode(reg.id, token, m, name); toast.success(m === "self" ? "You'll complete it yourself — the partner stays linked" : "The partner can now fill your form"); onMode(r.partner_access); } catch (e) { showApiError(e); }
  };
  const open = ["draft", "needs_clarification"].includes(reg.status);
  return (
    <div className="mt-4 bg-white border border-brand-gold p-3 text-sm space-y-2" data-testid="partner-supplier-banner">
      <div>Prepared with help from partner <b>{p.name}</b> ({p.code}) · access: <b data-testid="partner-access-state">{{ granted: "partner may fill your form", self_fill: "you are filling it yourself", revoked: "removed", awaiting_consent: "waiting for your consent" }[p.access] || p.access}</b></div>
      {fields.length > 0 && <div className="text-xs text-brand-navy/70" data-testid="partner-fields-list">Filled or changed by the partner — please check: {fields.join(", ")}</div>}
      <div className="text-xs text-brand-navy/70">Only you can tick the declarations, sign and submit. Partner code {p.code} stays on your supplier record, bids, contracts and fee payments.</div>
      <div className="flex gap-2 flex-wrap">
        {open && p.access === "granted" && <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => mode("self")} data-testid="partner-mode-self">I'll finish it myself</button>}
        {open && p.access === "self_fill" && <button type="button" className="pmc-btn pmc-btn--secondary" onClick={() => mode("partner")} data-testid="partner-mode-partner">Let my partner fill it</button>}
        {p.access === "granted" && <button type="button" className="pmc-btn pmc-btn--secondary" disabled={busy} onClick={revoke} data-testid="partner-revoke-btn">Remove partner access</button>}
      </div>
    </div>
  );
}
