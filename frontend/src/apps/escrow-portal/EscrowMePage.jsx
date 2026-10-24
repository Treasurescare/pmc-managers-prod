/**
 * EscrowMePage — v56. Signed-in landing page for the escrow institution
 * portal. Handles BOTH user types and now wraps every state in the shared
 * PortalShellE frame so it matches the admin console look exactly: a fixed
 * dark sidebar on desktop that collapses to an off-canvas drawer (single
 * hamburger + scrim) on tablet/phone, a white sticky top bar with the
 * notifications bell + avatar menu, and full content width on mobile.
 *
 *   1. Institution account — cookie `escrow_account_token`,
 *      API /escrow-accounts/auth/me. Renders the 5-section registration
 *      wizard (while draft) or the account dashboard (once approved).
 *   2. Signatory — cookie `escrow_sig_token`,
 *      API /escrow-signatories/auth/me. Renders the signatory dashboard.
 */
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api } from "@/lib/api";
import PortalShellE from "@/apps/shared/PortalShellE";
import PortalAvatarMenu from "@/apps/shared/PortalAvatarMenu";
import EscrowHeaderActions from "./EscrowAccountHeader";
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
    // (named individual with a claimed password). Only when BOTH fail do we
    // bounce back to login.
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

  if (sig) return <EscrowSignatoryShell signatory={sig} nav={nav} />;

  if (!acc) return null;
  const inst = acc.institution || {};
  const incomplete = ["draft", "needs_clarification"].includes(inst.status);

  if (incomplete) {
    return (
      <PortalShellE
        rootTestId="escrow-me-page"
        sideTestId="escrow-sidebar"
        brand={{ title: "PMC Managers", sub: "Escrow portal" }}
        items={[{ key: "registration", label: "Registration", icon: "i-file", testid: "escrow-nav-registration" }]}
        activeKey="registration"
        onSelect={() => {}}
        crumb={<>Escrow / <b>Registration</b></>}
        header={<EscrowHeaderActions account={acc} onProfileUpdated={refresh} />}
      >
        <EscrowAccountWizard account={acc} onDone={refresh} />
      </PortalShellE>
    );
  }

  return <EscrowAccountDashboardBody account={acc} onProfileUpdated={refresh} />;
}


function EscrowSignatoryShell({ signatory, nav }) {
  const signOut = async () => {
    try { await api.post("/api/v1/escrow-signatories/auth/logout"); } catch (e) { /* ignore */ }
    try { await api.post("/api/v1/escrow-accounts/auth/logout"); } catch (e) { /* ignore */ }
    toast.success("Signed out");
    nav("/login");
  };
  const initial = (signatory?.name || signatory?.email || "S").trim().charAt(0).toUpperCase();
  return (
    <PortalShellE
      rootTestId="escrow-me-page"
      sideTestId="escrow-sidebar"
      brand={{ title: "PMC Managers", sub: "Signatory" }}
      items={[{ key: "overview", label: "Overview", icon: "i-home", testid: "escrow-nav-overview" }]}
      activeKey="overview"
      onSelect={() => {}}
      crumb={<>Escrow / <b>Overview</b></>}
      header={
        <div className="pmc-atop__r">
          <PortalAvatarMenu
            initial={initial}
            title={signatory?.name || signatory?.email}
            sub="Signatory"
            items={[{ label: "Sign out", onClick: signOut, danger: true, testid: "escrow-sig-signout" }]}
            testId="escrow-sig-avatar"
          />
        </div>
      }
    >
      <EscrowSignatoryDashboard signatory={signatory} />
    </PortalShellE>
  );
}
