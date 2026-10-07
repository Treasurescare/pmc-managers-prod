import AdminEShell from "./AdminEShell";
import BillingTransactionsPanel from "@/apps/admin-console/BillingTransactionsPanel";
import MoneyPanelWithFilter from "./MoneyPanelWithFilter";

export default function AdminBillingE() {
  return (
    <div className="min-h-screen" style={{ background: "var(--brand-pale, #F3EFE4)" }}>
      <AdminEShell crumb={<>Money &amp; compliance / <b>Billing</b></>}>
        <MoneyPanelWithFilter scope="[data-testid=billing-panel]"
                              testid="billing-filter"
                              statusOptions={[
                                { value: "pending",   label: "Pending" },
                                { value: "paid",      label: "Paid" },
                                { value: "refunded",  label: "Refunded" },
                                { value: "failed",    label: "Failed" },
                              ]}>
          <div data-testid="billing-panel"><BillingTransactionsPanel /></div>
        </MoneyPanelWithFilter>
      </AdminEShell>
    </div>
  );
}
