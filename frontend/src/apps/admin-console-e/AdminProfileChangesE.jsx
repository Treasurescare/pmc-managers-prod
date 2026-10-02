import AdminEShell from "./AdminEShell";
import ProfileChangeRequestsPanel from "@/apps/admin-console/masters/ProfileChangeRequestsPanel";

/** v50r — top-level route for Vendor profile change requests (moved out of Masters). */
export default function AdminProfileChangesE() {
  return (
    <AdminEShell active="Profile changes"
                 crumb={<>Market / <b>Profile changes</b></>}>
      <div className="p-6">
        <h1 className="text-2xl font-serif mb-1">Vendor profile change requests</h1>
        <div className="text-sm text-brand-navy/60 mb-4">
          Approve or reject supplier edits to company name, address, phone and login email.
          Email changes also require the supplier to click a verification link sent to the new address.
        </div>
        <ProfileChangeRequestsPanel />
      </div>
    </AdminEShell>
  );
}
