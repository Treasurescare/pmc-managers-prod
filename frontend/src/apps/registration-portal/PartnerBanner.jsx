import { useState } from "react";
import { toast } from "sonner";
import { agentApi, showApiError } from "@/lib/api";

export default function PartnerBanner({ reg, token, onRevoked }) {
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
  return (
    <div className="mt-4 bg-white border border-brand-gold p-3 text-sm space-y-2" data-testid="partner-supplier-banner">
      <div>Prepared with help from partner <b>{p.name}</b> ({p.code}) · access: <b data-testid="partner-access-state">{p.access}</b></div>
      {fields.length > 0 && <div className="text-xs text-brand-navy/70" data-testid="partner-fields-list">Filled or changed by the partner — please check: {fields.join(", ")}</div>}
      <div className="text-xs text-brand-navy/70">Only you can tick the declarations, sign and submit.</div>
      {p.access === "granted" && <button type="button" className="pmc-btn pmc-btn--secondary" disabled={busy} onClick={revoke} data-testid="partner-revoke-btn">Remove partner access</button>}
    </div>
  );
}
