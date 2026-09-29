import AdminEShell from "./AdminEShell";
import CorrigendaPanel from "@/apps/admin-console/CorrigendaPanel";

export default function AdminCorrigendaE() {
  return (
    <div data-testid="admin-corrigenda-e" data-pmc-e-page="admin-corrigenda-e">
      <AdminEShell active="Corrigenda" crumb={<>Procurement / <b>Corrigenda</b></>}>
        <CorrigendaPanel />
      </AdminEShell>
    </div>
  );
}
