import { useState } from "react";
import AdminEShell from "./AdminEShell";
import { BuyerAppsTab } from "./growth/BuyerAppsTab";
import { ConsultingTab } from "./growth/ConsultingTab";
import { DataApiTab, DirectoryTab, SourcesTab } from "./growth/OtherTabs";
import { TranslationsTab } from "./growth/TranslationsTab";

const TABS = [["buyers", "Buyer applications", BuyerAppsTab], ["consulting", "Consultancy services", ConsultingTab],
  ["directory", "Supplier directory", DirectoryTab], ["sources", "Global tender sources", SourcesTab], ["api", "Data API clients", DataApiTab], ["translations", "Translation review", TranslationsTab]];

export default function AdminGrowthE() {
  const [tab, setTab] = useState(() => (new URLSearchParams(window.location.search).get("tab") || "buyers"));
  const Cur = (TABS.find((t) => t[0] === tab) || TABS[0])[2];
  return (
    <div className="min-h-screen" style={{ background: "var(--brand-pale, #F3EFE4)" }}>
      <AdminEShell crumb={<>Operations / <b>Growth</b></>}>
        <div className="flex flex-wrap gap-2 mb-4" data-testid="growth-tabs">
          {TABS.map(([k, l]) => <button key={k} onClick={() => setTab(k)} data-testid={`growth-tab-${k}`}
            className={`px-3 py-1.5 text-[10px] uppercase tracking-widest border ${tab === k ? "bg-brand-navy text-white border-brand-navy" : "border-brand-navy/30 text-brand-navy"}`}>{l}</button>)}
        </div>
        <Cur />
      </AdminEShell>
    </div>);
}
