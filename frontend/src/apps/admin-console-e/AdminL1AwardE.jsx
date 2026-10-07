import AdminEShell from "./AdminEShell";
import L1ComparisonPanel from "@/apps/admin-console/L1ComparisonPanel";
import MoneyPanelWithFilter from "./MoneyPanelWithFilter";

export default function AdminL1AwardE() {
  return (
    <div className="min-h-screen" style={{ background: "var(--brand-pale, #F3EFE4)" }}>
      <AdminEShell crumb={<>Money &amp; compliance / <b>L1 comparison</b></>}>
        <MoneyPanelWithFilter scope="[data-testid=l1-panel]"
                              testid="l1-filter"
                              presetScope="l1"
                              showExpiring={false}
                              statusOptions={[
                                { value: "awarded",   label: "Awarded" },
                                { value: "pending",   label: "Pending" },
                                { value: "rejected",  label: "Rejected" },
                              ]}>
          <div data-testid="l1-panel"><L1ComparisonPanel /></div>
        </MoneyPanelWithFilter>
      </AdminEShell>
    </div>
  );
}
