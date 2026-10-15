/**
 * EscrowMePage — v52d. Signed-in landing page for escrow institution
 * primary contacts.
 *
 * Flow:
 *  - GET /api/v1/escrow-accounts/auth/me → identify user
 *  - If institution.status in {draft, needs_clarification} → render the
 *    5-section wizard, autosaving to the owned institution.
 *  - Otherwise → render the dashboard body with the shared header
 *    (bell + avatar menu).
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "@/lib/api";
import EscrowAccountHeader from "./EscrowAccountHeader";
import EscrowAccountWizard from "./EscrowAccountWizard";
import EscrowAccountDashboardBody from "./EscrowAccountDashboardBody";

export default function EscrowMePage() {
  const nav = useNavigate();
  const [acc, setAcc] = useState(null);
  const [loading, setLoading] = useState(true);

  const refresh = () => {
    api.get("/api/v1/escrow-accounts/auth/me")
      .then((r) => { setAcc(r.data); setLoading(false); })
      .catch(() => nav("/escrow/login"));
  };

  useEffect(() => { refresh(); }, []); // eslint-disable-line

  if (loading) return <div className="p-10 text-brand-navy/50">Loading…</div>;
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
