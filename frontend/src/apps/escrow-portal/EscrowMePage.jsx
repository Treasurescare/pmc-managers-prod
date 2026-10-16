/**
 * EscrowMePage — v53n. Signed-in landing page for the escrow institution
 * portal. Handles BOTH user types:
 *
 *   1. Institution account — created via /escrow/register and verified.
 *      Cookie: `escrow_account_token`. API: /escrow-accounts/auth/me.
 *      Renders the 5-section wizard (while draft) or the account
 *      dashboard body (once approved).
 *
 *   2. Signatory — individual person named on an institution's signatory
 *      list who set a password via the approval magic link
 *      (`/escrow/login?claim=1`). Cookie: `escrow_sig_token`.
 *      API: /escrow-signatories/auth/me. Renders the signatory
 *      dashboard.
 *
 * Bug this fixes: before v53n the page tried /escrow-accounts/auth/me
 * only. Signatories (which the claim flow produces) got 401 → the
 * .catch() bounced back to /escrow/login — infinite redirect loop that
 * the user described as "crashes and moves to login page" after setting
 * a password through the admin's approval email.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import EscrowAccountHeader from "./EscrowAccountHeader";
import EscrowAccountWizard from "./EscrowAccountWizard";
import EscrowAccountDashboardBody from "./EscrowAccountDashboardBody";
import EscrowSignatoryDashboard from "./EscrowSignatoryDashboard";

export default function EscrowMePage() {
  const nav = useNavigate();
  const [acc, setAcc] = useState(null);
  const [sig, setSig] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    setLoading(true);
    // Try account first (institution admin). If that 401s, try signatory
    // (named individual with a claimed password). Only when BOTH fail
    // do we bounce back to login.
    api.get("/api/v1/escrow-accounts/auth/me")
      .then((r) => { setAcc(r.data); setSig(null); setLoading(false); })
      .catch(() => {
        api.get("/api/v1/escrow-signatories/auth/me")
          .then((r) => { setSig(r.data); setAcc(null); setLoading(false); })
          .catch(() => nav("/escrow/login"));
      });
  };

  useEffect(() => { refresh(); }, []); // eslint-disable-line

  if (loading) return <div className="p-10 text-brand-navy/50" data-testid="escrow-me-loading">Loading…</div>;

  if (sig) {
    // Signatory view — no header (no account/institution profile to edit).
    return (
      <div className="min-h-screen bg-brand-pale" data-testid="escrow-me-page">
        <EscrowSignatoryDashboard signatory={sig} />
      </div>
    );
  }

  if (!acc) return null;
  const inst = acc.institution || {};
  const incomplete = ["draft", "needs_clarification"].includes(inst.status);

  return (
    <div className="min-h-screen bg-brand-pale" data-testid="escrow-me-page">
      <EscrowAccountHeader account={acc} onProfileUpdated={refresh} />
      {incomplete ? (
        <EscrowAccountWizard account={acc} onDone={refresh} />
      ) : (
        <EscrowAccountDashboardBody account={acc} />
      )}
    </div>
  );
}
