import AdminEShell from "./AdminEShell";
import RegistrationsPanel from "@/apps/admin-console/RegistrationsPanel";

export default function AdminRegistrationsE() {
  return (
    <div data-testid="admin-registrations-e" data-pmc-e-page="admin-registrations-e">
      <AdminEShell active="Registrations" crumb={<>Market / <b>Registrations</b></>}>
        <RegistrationsPanel />
      </AdminEShell>
    </div>
  );
}
