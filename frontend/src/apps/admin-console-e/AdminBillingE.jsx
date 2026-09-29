import AdminEShell from "./AdminEShell";
import BillingTransactionsPanel from "@/apps/admin-console/BillingTransactionsPanel";

export default function AdminBillingE() {
  return (
    <div data-testid="admin-billing-e" data-pmc-e-page="admin-billing-e">
      <AdminEShell active="Billing" crumb={<>Money &amp; compliance / <b>Billing</b></>}>
        <BillingTransactionsPanel />
      </AdminEShell>
    </div>
  );
}
