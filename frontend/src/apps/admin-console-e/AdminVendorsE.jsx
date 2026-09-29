import AdminEShell from "./AdminEShell";
import VendorsPanel from "@/apps/admin-console/VendorsPanel";

export default function AdminVendorsE() {
  return (
    <div data-testid="admin-vendors-e" data-pmc-e-page="admin-vendors-e">
      <AdminEShell active="Vendors" crumb={<>Market / <b>Vendors</b></>}>
        <VendorsPanel />
      </AdminEShell>
    </div>
  );
}
