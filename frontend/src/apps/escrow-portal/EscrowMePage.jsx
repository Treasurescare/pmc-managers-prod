import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import EscrowInstitutionDashboard from "./EscrowInstitutionDashboard";
import { api } from "@/lib/api";

/**
 * EscrowMePage — v51an. Lightweight wrapper used after signatory login.
 * Confirms the session via /me and renders the enhanced dashboard
 * component (which fetches via the signatory-scoped endpoint).
 */
export default function EscrowMePage() {
  const nav = useNavigate();
  const [checked, setChecked] = useState(false);
  useEffect(() => {
    api.get("/api/v1/escrow-signatories/auth/me")
      .then(() => setChecked(true))
      .catch(() => nav("/escrow/login"));
  }, [nav]);
  if (!checked) return <div className="p-8 text-brand-navy/50">Loading…</div>;
  return <EscrowInstitutionDashboard />;
}
