import AdminEShell from "./AdminEShell";
import BOQContractsPanel from "@/apps/admin-console/BOQContractsPanel";

export default function AdminBoqContractsE() {
  return (
    <div data-testid="admin-boq-contracts-e" data-pmc-e-page="admin-boq-contracts-e">
      <AdminEShell active="BOQ & contracts" crumb={<>Procurement / <b>BOQ &amp; contracts</b></>}>
        <BOQContractsPanel />
      </AdminEShell>
    </div>
  );
}
