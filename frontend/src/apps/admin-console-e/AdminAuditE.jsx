import AdminEShell from "./AdminEShell";
import AuditPanel from "@/apps/admin-console/AuditPanel";

export default function AdminAuditE() {
  return (
    <div data-testid="admin-audit-e" data-pmc-e-page="admin-audit-e">
      <AdminEShell active="Audit ledger" crumb={<>Overview / <b>Audit ledger</b></>}>
        <AuditPanel />
      </AdminEShell>
    </div>
  );
}
