import AdminEShell from "./AdminEShell";
import L1ComparisonPanel from "@/apps/admin-console/L1ComparisonPanel";

export default function AdminL1AwardE() {
  return (
    <div data-testid="admin-l1-award-e" data-pmc-e-page="admin-l1-award-e">
      <AdminEShell active="L1 comparison" crumb={<>Money &amp; compliance / <b>L1 comparison</b></>}>
        <L1ComparisonPanel />
      </AdminEShell>
    </div>
  );
}
