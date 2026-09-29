import AdminEShell from "./AdminEShell";
import NoticesPanel from "@/apps/admin-console/NoticesPanel";

export default function AdminNoticesE() {
  return (
    <div data-testid="admin-notices-e" data-pmc-e-page="admin-notices-e">
      <AdminEShell active="Notices" crumb={<>Procurement / <b>Notices</b></>}>
        <NoticesPanel />
      </AdminEShell>
    </div>
  );
}
