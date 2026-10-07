import AdminEShell from "./AdminEShell";
import EscrowPanel from "@/apps/admin-console/EscrowPanel";
import MoneyPanelWithFilter from "./MoneyPanelWithFilter";

export default function AdminEscrowE() {
  return (
    <div className="min-h-screen" style={{ background: "var(--brand-pale, #F3EFE4)" }}>
      <AdminEShell crumb={<>Money &amp; compliance / <b>Escrow / EMD</b></>}>
        <MoneyPanelWithFilter scope="[data-testid=escrow-panel]"
                              testid="escrow-filter"
                              presetScope="escrow"
                              showExpiring={false}
                              statusOptions={[
                                { value: "pending",             label: "Pending" },
                                { value: "received",            label: "Received" },
                                { value: "awaiting_signatures", label: "Awaiting signatures" },
                                { value: "released_to_vendor",  label: "Released → vendor" },
                                { value: "released_to_contractor", label: "Released → contractor" },
                                { value: "forfeited",           label: "Forfeited" },
                              ]}>
          <div data-testid="escrow-panel"><EscrowPanel /></div>
        </MoneyPanelWithFilter>
      </AdminEShell>
    </div>
  );
}
