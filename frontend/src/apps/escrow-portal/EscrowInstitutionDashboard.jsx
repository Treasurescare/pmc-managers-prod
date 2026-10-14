/**
 * EscrowInstitutionDashboard — v52cz rev8
 * Vendor-portal-style sidebar with clickable KPI tiles that navigate between
 * Overview / Pending / Transactions / Accounts / Profile tabs.
 */
import { useEffect, useState } from "react";
import { useParams, Link } from "react-router-dom";
import { api, showApiError } from "@/lib/api";

const TABS = [
  ["overview",     "Overview"],
  ["pending",      "Pending signatures"],
  ["transactions", "All transactions"],
  ["accounts",     "Joint accounts"],
  ["profile",      "Institution profile"],
];

export default function EscrowInstitutionDashboard() {
  const { iid } = useParams();
  const token = new URLSearchParams(window.location.search).get("token");
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!iid || !token) return;
    api.get(`/api/v1/escrow-institutions/${iid}/dashboard`, { params: { token } })
       .then((r) => setData(r.data))
       .catch(showApiError);
  }, [iid, token]);

  const inst = data?.institution || {};
  const kpis = [
    { key: "accounts", label: "Joint accounts", value: data?.joint_accounts_count ?? 0 },
    { key: "pending",  label: "Pending signatures", value: data?.pending_signatures_count ?? 0 },
    { key: "transactions", label: "Total transactions", value: data?.total_transactions ?? 0 },
  ];

  return (
    <div className="min-h-screen flex bg-brand-pale" data-testid="escrow-institution-dashboard">
      <aside className="w-64 bg-brand-navy text-white px-4 py-6 flex flex-col gap-2">
        <div className="mb-6">
          <div className="text-[11px] uppercase tracking-widest text-white/60">Escrow institution</div>
          <div className="font-serif text-lg leading-tight">{inst.legal_name || "—"}</div>
          <div className="text-[11px] text-white/50 mt-1">status: {inst.status || "—"}</div>
        </div>
        {TABS.map(([key, label]) => (
          <button key={key} type="button"
                  onClick={() => setTab(key)}
                  data-testid={`escrow-tab-${key}`}
                  className={"text-left px-3 py-2 text-sm rounded " +
                             (tab === key ? "bg-white/15" : "hover:bg-white/5 text-white/80")}>
            {label}
          </button>
        ))}
        <div className="mt-auto pt-4 border-t border-white/15">
          <Link to="/escrow/login"
                data-testid="escrow-sign-out"
                className="text-[11px] uppercase tracking-widest text-white/60 hover:text-white">
            Sign out
          </Link>
        </div>
      </aside>

      <main className="flex-1 p-6 overflow-auto">
        {tab === "overview" && (
          <>
            <h1 className="font-serif text-2xl text-brand-navy">Overview</h1>
            <p className="text-sm text-brand-navy/60 mb-6">
              Signed in to {inst.legal_name || "your institution"}
            </p>
            <div className="grid md:grid-cols-3 gap-4 mb-8">
              {kpis.map((k) => (
                <button key={k.key} type="button"
                        onClick={() => setTab(k.key)}
                        data-testid={`escrow-kpi-${k.key}`}
                        className="text-left bg-white p-6 border border-brand-navy/15 hover:border-brand-gold transition-colors">
                  <div className="text-[11px] uppercase tracking-widest text-brand-navy/60">{k.label}</div>
                  <div className="text-3xl font-serif text-brand-navy mt-2">{k.value}</div>
                  <div className="text-[11px] text-brand-navy/40 mt-2">Click to open →</div>
                </button>
              ))}
            </div>
          </>
        )}
        {tab === "pending" && (
          <>
            <h1 className="font-serif text-2xl text-brand-navy mb-4">Pending signatures</h1>
            <div className="bg-white border border-brand-navy/15 p-6 text-sm text-brand-navy/60">
              Nothing waits on your signature right now.
            </div>
          </>
        )}
        {tab === "transactions" && (
          <>
            <h1 className="font-serif text-2xl text-brand-navy mb-4">All transactions</h1>
            <div className="bg-white border border-brand-navy/15 p-6 text-sm text-brand-navy/60">
              No transactions on your joint accounts yet.
            </div>
          </>
        )}
        {tab === "accounts" && (
          <>
            <h1 className="font-serif text-2xl text-brand-navy mb-4">Joint accounts</h1>
            <div className="bg-white border border-brand-navy/15 p-6 text-sm text-brand-navy/60">
              You'll see each joint escrow account PMC has opened with your institution here.
            </div>
          </>
        )}
        {tab === "profile" && (
          <>
            <h1 className="font-serif text-2xl text-brand-navy mb-4">Institution profile</h1>
            <div className="bg-white border border-brand-navy/15 p-6 text-sm text-brand-navy/80 space-y-1">
              <div><b>Legal name:</b> {inst.legal_name || "—"}</div>
              <div><b>Status:</b> {inst.status || "—"}</div>
              <div className="text-[11px] text-brand-navy/50 mt-2">
                To edit any registration detail, contact PMC support.
              </div>
            </div>
          </>
        )}
      </main>
    </div>
  );
}
