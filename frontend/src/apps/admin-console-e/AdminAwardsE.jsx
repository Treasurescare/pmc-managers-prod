import AdminEShell from "./AdminEShell";
import AwardsPanel from "@/apps/admin-console/AwardsPanel";

export default function AdminAwardsE() {
  return (
    <div data-testid="admin-awards-e" data-pmc-e-page="admin-awards-e">
      <AdminEShell active="Awards" crumb={<>Money &amp; compliance / <b>Awards</b></>}>
        <AwardsPanel />
      </AdminEShell>
    </div>
  );
}
