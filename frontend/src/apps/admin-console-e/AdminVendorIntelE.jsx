import AdminEShell from "./AdminEShell";
import VendorIntelPanel from "@/apps/admin-console/VendorIntelPanel";

export default function AdminVendorIntelE() {
  return (
    <div data-testid="admin-vendor-intel-e" data-pmc-e-page="admin-vendor-intel-e">
      <AdminEShell active="Vendor intel" crumb={<>Market / <b>Vendor intel</b></>}>
        <VendorIntelPanel />
      </AdminEShell>
    </div>
  );
}
