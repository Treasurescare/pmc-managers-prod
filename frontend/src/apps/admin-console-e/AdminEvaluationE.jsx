import AdminEShell from "./AdminEShell";
import EvaluationPanel from "@/apps/admin-console/EvaluationPanel";

export default function AdminEvaluationE() {
  return (
    <div data-testid="admin-evaluation-e" data-pmc-e-page="admin-evaluation-e">
      <AdminEShell active="Evaluation" crumb={<>Money &amp; compliance / <b>Evaluation</b></>}>
        <EvaluationPanel />
      </AdminEShell>
    </div>
  );
}
