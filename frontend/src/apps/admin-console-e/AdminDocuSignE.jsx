import AdminEShell from "./AdminEShell";
import DocuSignPanel from "@/apps/admin-console/DocuSignPanel";

export default function AdminDocuSignE() {
  return (
    <div data-testid="admin-docusign-e" data-pmc-e-page="admin-docusign-e">
      <AdminEShell active="DocuSign" crumb={<>Money &amp; compliance / <b>DocuSign</b></>}>
        <DocuSignPanel />
      </AdminEShell>
    </div>
  );
}
