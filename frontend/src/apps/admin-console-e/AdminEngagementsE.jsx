import AdminEShell from "./AdminEShell";
import EngagementsPanel from "@/apps/admin-console/EngagementsPanel";

export default function AdminEngagementsE() {
  return (
    <div data-testid="admin-engagements-e" data-pmc-e-page="admin-engagements-e">
      <AdminEShell active="Engagements" crumb={<>Market / <b>Engagements</b></>}>
        <EngagementsPanel />
      </AdminEShell>
    </div>
  );
}
