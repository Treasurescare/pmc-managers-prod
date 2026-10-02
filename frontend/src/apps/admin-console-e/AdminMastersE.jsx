import AdminEShell from "./AdminEShell";
import MastersPanel from "../admin-console/MastersPanel";

// v50g — Restores the Masters tab in the new Option E admin console.
// Wraps the fully-wired legacy MastersPanel (Staff, Companies, Tenants,
// Approval Matrix, Hierarchy, Rating & Fees, Charge Fee, Investor Demo,
// Categories) inside the shared AdminEShell chrome.
export default function AdminMastersE() {
  return (
    <AdminEShell active="Masters" crumb="Procurement / Masters">
      <MastersPanel />
    </AdminEShell>
  );
}
