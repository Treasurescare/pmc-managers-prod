import { useEffect, useState } from "react";
import { api, showApiError } from "@/lib/api";

/**
 * EscrowInstitutionDashboard — scaffold v51al.
 * NOT YET wired into App.js. Shown to escrow institution signatories after
 * they sign in (or hit a magic link). Lists their joint accounts and the
 * transactions waiting on one of their signatories' signatures.
 */
export default function EscrowInstitutionDashboard({ institutionId, token }) {
  const [data, setData] = useState(null);
  useEffect(() => {
    if (!institutionId || !token) return;
    api.get(`/api/v1/escrow-institutions/${institutionId}/dashboard`, { params: { token } })
      .then((r) => setData(r.data))
      .catch(showApiError);
  }, [institutionId, token]);

  if (!data) return <div className="p-8 text-brand-navy/50">Loading…</div>;

  return (
    <div className="max-w-5xl mx-auto p-6" data-testid="escrow-dashboard">
      <div className="mb-4">
        <h1 className="text-2xl font-semibold text-brand-navy">
          {data.institution?.legal_name || "Escrow Institution"}
        </h1>
        <span className={"text-[10px] uppercase tracking-widest px-2 py-0.5 " +
          (data.institution?.status === "approved"
            ? "bg-emerald-50 text-emerald-900 border border-emerald-200"
            : "bg-amber-50 text-amber-900 border border-amber-300")}>
          {data.institution?.status}
        </span>
      </div>

      <div className="grid md:grid-cols-2 gap-4">
        <KPI label="Joint accounts you operate" n={data.joint_accounts_count} testid="kpi-accounts" />
        <KPI label="Transactions awaiting your signature" n={data.pending_signatures_count}
             testid="kpi-pending" highlight={(data.pending_signatures_count || 0) > 0} />
      </div>

      <div className="mt-6 bg-white border border-brand-navy/15 p-6">
        <div className="pmc-label">Next steps</div>
        <ul className="mt-2 text-sm text-brand-navy/80 list-disc list-inside space-y-1">
          <li>Sign pending EMD releases from the transactions list.</li>
          <li>Keep signatory details current — PMC blocks releases if any signatory email has expired.</li>
          <li>Upload refreshed licence/audited financials before expiry.</li>
        </ul>
      </div>
    </div>
  );
}

function KPI({ label, n, highlight, testid }) {
  return (
    <div className={"p-6 border " + (highlight ? "bg-amber-50 border-amber-300" : "bg-white border-brand-navy/15")}
         data-testid={testid}>
      <div className="pmc-label">{label}</div>
      <div className="text-3xl font-semibold text-brand-navy mt-1">{n ?? "—"}</div>
    </div>
  );
}
