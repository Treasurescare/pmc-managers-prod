import AdminEShell from "./AdminEShell";
import PackagesPanel from "@/apps/admin-console/PackagesPanel";

export default function AdminWorkPackagesE() {
  return (
    <div data-testid="admin-work-packages-e" data-pmc-e-page="admin-work-packages-e">
      <AdminEShell active="Work packages" crumb={<>Procurement / <b>Work packages</b></>}>
        <PackagesPanel />
      </AdminEShell>
    </div>
  );
}
