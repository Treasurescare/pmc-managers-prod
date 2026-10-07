import AdminEShell from "./AdminEShell";
import AwardsPanel from "@/apps/admin-console/AwardsPanel";
import MoneyPanelWithFilter from "./MoneyPanelWithFilter";

export default function AdminAwardsE() {
  return (
    <div className="min-h-screen" style={{ background: "var(--brand-pale, #F3EFE4)" }}>
      <AdminEShell crumb={<>Money &amp; compliance / <b>Awards</b></>}>
        <MoneyPanelWithFilter scope="[data-testid=awards-panel]"
                              testid="awards-filter"
                              statusOptions={[
                                { value: "pending", label: "Pending" },
                                { value: "signed",  label: "Signed" },
                                { value: "closed",  label: "Closed" },
                              ]}>
          <div data-testid="awards-panel"><AwardsPanel /></div>
        </MoneyPanelWithFilter>
      </AdminEShell>
    </div>
  );
}
