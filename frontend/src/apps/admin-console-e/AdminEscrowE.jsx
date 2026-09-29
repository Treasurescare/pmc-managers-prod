import AdminEShell from "./AdminEShell";
import EscrowPanel from "@/apps/admin-console/EscrowPanel";

export default function AdminEscrowE() {
  return (
    <div data-testid="admin-escrow-e" data-pmc-e-page="admin-escrow-e">
      <AdminEShell active="Escrow / EMD" crumb={<>Money &amp; compliance / <b>Escrow / EMD</b></>}>
        <EscrowPanel />
      </AdminEShell>
    </div>
  );
}
