import AdminEShell from "./AdminEShell";
import CategoryRequestsPanel from "@/apps/admin-console/masters/CategoryRequestsPanel";

/** v50r — top-level route for Vendor category requests (moved out of Masters). */
export default function AdminVendorRequestsE() {
  return (
    <AdminEShell active="Vendor requests"
                 crumb={<>Market / <b>Vendor requests</b></>}>
      <div className="p-6">
        <h1 className="text-2xl font-serif mb-1">Vendor category requests</h1>
        <div className="text-sm text-brand-navy/60 mb-4">
          Approve or reject suppliers' requests to add new categories of interest to their profile.
        </div>
        <CategoryRequestsPanel />
      </div>
    </AdminEShell>
  );
}
