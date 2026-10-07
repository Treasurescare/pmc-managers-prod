import AdminEShell from "./AdminEShell";
import EvaluationPanel from "@/apps/admin-console/EvaluationPanel";
import MoneyPanelWithFilter from "./MoneyPanelWithFilter";

export default function AdminEvaluationE() {
  return (
    <div className="min-h-screen" style={{ background: "var(--brand-pale, #F3EFE4)" }}>
      <AdminEShell crumb={<>Money &amp; compliance / <b>Evaluation</b></>}>
        <MoneyPanelWithFilter scope="[data-testid=evaluation-panel]"
                              testid="evaluation-filter"
                              presetScope="evaluation"
                              showExpiring={false}
                              statusOptions={[
                                { value: "pending",             label: "Pending" },
                                { value: "technical_cleared",   label: "Technical cleared" },
                                { value: "awarded",             label: "Awarded" },
                                { value: "rejected",            label: "Rejected" },
                              ]}>
          <div data-testid="evaluation-panel"><EvaluationPanel /></div>
        </MoneyPanelWithFilter>
      </AdminEShell>
    </div>
  );
}
