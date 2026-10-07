import AdminEShell from "./AdminEShell";
import DocuSignPanel from "@/apps/admin-console/DocuSignPanel";
import MoneyPanelWithFilter from "./MoneyPanelWithFilter";

export default function AdminDocuSignE() {
  return (
    <div data-testid="admin-docusign-e" data-pmc-e-page="admin-docusign-e">
      <AdminEShell active="DocuSign" crumb={<>Money &amp; compliance / <b>DocuSign</b></>}>
        <MoneyPanelWithFilter scope="[data-testid=docusign-panel]"
                              testid="docusign-filter"
                              presetScope="docusign"
                              showExpiring={false}
                              statusOptions={[
                                { value: "sent",      label: "Sent" },
                                { value: "delivered", label: "Delivered" },
                                { value: "signed",    label: "Signed" },
                                { value: "completed", label: "Completed" },
                                { value: "declined",  label: "Declined" },
                                { value: "voided",    label: "Voided" },
                              ]}>
          <div data-testid="docusign-panel"><DocuSignPanel /></div>
        </MoneyPanelWithFilter>
      </AdminEShell>
    </div>
  );
}
