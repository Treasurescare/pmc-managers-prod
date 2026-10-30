import { useState } from "react";
import AdminEShell from "./AdminEShell";
import { CampaignsTab } from "./marketing/CampaignsTab";
import { ContactsTab } from "./marketing/ContactsTab";
import { SegmentsTab } from "./marketing/SegmentsTab";
import { AlertsTab, ReferralsTab } from "./marketing/AlertsReferralsTabs";
import { BuyerInvitesTab } from "./marketing/BuyerInvitesTab";

const TABS = [["campaigns", "Email campaigns", CampaignsTab], ["contacts", "Contacts", ContactsTab],
  ["segments", "Lists & segments", SegmentsTab], ["alerts", "New-tender alerts", AlertsTab], ["invites", "Buyer invites", BuyerInvitesTab], ["referrals", "Referrals", ReferralsTab]];

export default function AdminMarketingE() {
  const [tab, setTab] = useState("campaigns");
  const Body = TABS.find(([k]) => k === tab)[2];
  return (
    <div className="min-h-screen" style={{ background: "var(--brand-pale, #F3EFE4)" }}>
      <AdminEShell crumb={<>Market / <b>Marketing</b></>}>
        <div data-testid="admin-marketing" className="space-y-5">
          <div>
            <div className="text-xs uppercase tracking-[0.2em] text-brand-navy/60">Grow the marketplace</div>
            <h1 className="text-3xl font-serif text-brand-navy">Marketing</h1>
          </div>
          <div className="flex flex-wrap gap-2">
            {TABS.map(([k, l]) => (
              <button key={k} onClick={() => setTab(k)} data-testid={`mkt-tab-${k}`}
                      className={"px-4 py-2 text-xs uppercase tracking-widest border " + (tab === k ? "bg-brand-navy text-white border-brand-navy" : "bg-white border-brand-navy/20 text-brand-navy")}>{l}</button>))}
          </div>
          <Body />
        </div>
      </AdminEShell>
    </div>
  );
}
