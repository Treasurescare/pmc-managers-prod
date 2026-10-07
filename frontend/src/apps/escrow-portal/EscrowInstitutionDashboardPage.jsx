import { useParams, useSearchParams } from "react-router-dom";
import EscrowInstitutionDashboard from "./EscrowInstitutionDashboard";

/**
 * Route wrapper — reads :iid from the URL and ?token=... from the query
 * string so the dashboard component can stay a dumb render component. v51al.
 */
export default function EscrowInstitutionDashboardPage() {
  const { iid } = useParams();
  const [params] = useSearchParams();
  const token = params.get("token");
  return <EscrowInstitutionDashboard institutionId={iid} token={token} />;
}
