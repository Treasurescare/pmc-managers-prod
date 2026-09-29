import AdminEShell from "./AdminEShell";
import PermissionsPanel from "@/apps/admin-console/PermissionsPanel";

export default function AdminPermissionsE() {
  return (
    <div data-testid="admin-permissions-e" data-pmc-e-page="admin-permissions-e">
      <AdminEShell active="Permissions" crumb={<>Money &amp; compliance / <b>Permissions</b></>}>
        <PermissionsPanel />
      </AdminEShell>
    </div>
  );
}
