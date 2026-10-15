/**
 * EscrowAccountDashboardBody — v52d. Replaces the old magic-token-driven
 * dashboard with a session-authenticated one. Reads the institution
 * snapshot from /escrow-accounts/auth/me (already fetched by parent)
 * and surfaces status + KPIs. Sidebar/tabs preserved from rev8.
 */
import { useState } from "react";

const TABS = [
  ["overview",     "Overview"],
  ["pending",      "Pending signatures"],
  ["transactions", "All transactions"],
  ["accounts",     "Joint accounts"],
  ["profile",      "Institution profile"],
];

export default function EscrowAccountDashboardBody({ account }) {
  const [tab, setTab] = useState("overview");
  const inst = account?.institution || {};

  return (
    <div className="flex" data-testid="escrow-account-dashboard">
      <aside className="w-64 bg-white border-r border-brand-navy/10 min-h-[calc(100vh-60px)] px-4 py-6 flex flex-col gap-1">
        <div className="mb-4">
          <div className="text-[10px] uppercase tracking-widest text-brand-navy/50">Institution</div>
          <div className="font-serif text-lg leading-tight text-brand-navy">
            {inst.legal_name || "—"}
          </div>
          <div className="text-[10px] text-brand-navy/50 mt-1">status · {inst.status || "—"}</div>
        </div>
        {TABS.map(([key, label]) => (
          <button key={key} type="button" onClick={() => setTab(key)}
                  data-testid={`escrow-tab-${key}`}
                  className={"text-left px-3 py-2 text-sm rounded " +
                              (tab === key
                                 ? "bg-brand-navy text-white"
                                 : "hover:bg-brand-pale text-brand-navy/80")}>
            {label}
          </button>
        ))}
      </aside>

      <main className="flex-1 p-8">
        {tab === "overview" && (
          <>
            <h1 className="font-serif text-2xl text-brand-navy">Overview</h1>
            <p className="text-sm text-brand-navy/60 mb-6">
              Signed in to {inst.legal_name || "your institution"}
            </p>
            <div className="grid md:grid-cols-3 gap-4">
              <KPI label="Status" value={inst.status || "—"} />
              <KPI label="Pending signatures" value="0" />
              <KPI label="Joint accounts" value="0" />
            </div>
            {inst.status === "submitted" && (
              <p className="mt-6 text-sm text-brand-navy/70">
                Your registration is with PMC's review team. We'll notify you by
                email and in-app when there's an update — usually within 3 business days.
              </p>
            )}
          </>
        )}
        {tab !== "overview" && (
          <div className="bg-white border border-brand-navy/15 p-6 text-sm text-brand-navy/60">
            Nothing to show here yet — this section populates once PMC opens the
            first joint escrow account with your institution.
          </div>
        )}
      </main>
    </div>
  );
}

function KPI({ label, value }) {
  return (
    <div className="bg-white p-5 border border-brand-navy/15">
      <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">{label}</div>
      <div className="text-2xl font-serif text-brand-navy mt-1">{value}</div>
    </div>
  );
}
