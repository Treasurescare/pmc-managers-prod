/**
 * EscrowSignatoryDashboard — v53n.
 *
 * Signatory-side counterpart to EscrowAccountDashboardBody. Used when the
 * person signing in isn't an institution account (register-first flow)
 * but a named signatory who claimed a password via the approval magic
 * link. Reads from GET /api/v1/escrow-signatories/dashboard.
 *
 * Why this exists: before v53n the escrow /me page only knew how to read
 * `/escrow-accounts/auth/me` (the account cookie). A signatory who sets
 * their password via `/escrow/login?claim=1&iid=&token=` gets the
 * `escrow_sig_token` cookie, which doesn't match /auth/me, so the page
 * caught the 401 and bounced back to login — the "crash loop" the user
 * saw after setting their password.
 */
import { useEffect, useState } from "react";
import { api, showApiError } from "@/lib/api";

export default function EscrowSignatoryDashboard({ signatory }) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    api.get("/api/v1/escrow-signatories/dashboard")
      .then((r) => setData(r.data))
      .catch(showApiError)
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <div className="p-10 text-brand-navy/50" data-testid="sig-dash-loading">Loading dashboard…</div>;
  if (!data) return null;

  const pending = data.pending_transactions || [];
  const txs = data.transactions || [];
  const accts = data.joint_accounts || [];
  const insts = data.institutions || [];

  return (
    <div className="min-h-[calc(100vh-60px)] bg-brand-pale p-8" data-testid="escrow-signatory-dashboard">
      <div className="max-w-6xl mx-auto">
        <div className="mb-6">
          <div className="text-[10px] uppercase tracking-widest text-brand-navy/50">Signed in · signatory</div>
          <h1 className="font-serif text-3xl text-brand-navy">
            {signatory?.name || signatory?.email}
          </h1>
          <div className="text-sm text-brand-navy/60 mt-1">
            Signatory on {insts.length} institution{insts.length !== 1 ? "s" : ""}:{" "}
            {insts.map((i) => i.legal_name).filter(Boolean).join(", ") || "—"}
          </div>
        </div>

        <div className="grid md:grid-cols-3 gap-4 mb-8">
          <KPI label="Awaiting your signature" value={pending.length} tone={pending.length > 0 ? "warn" : "ok"} testId="sig-kpi-pending" />
          <KPI label="Joint accounts you can sign" value={accts.length} testId="sig-kpi-accounts" />
          <KPI label="Total transactions" value={txs.length} testId="sig-kpi-txs" />
        </div>

        <Section title="Awaiting your signature" rows={pending}
                  empty="Nothing needs your sign-off right now."
                  testid="sig-pending-section" />

        <Section title="Joint accounts" accounts={accts}
                  empty="PMC hasn't opened a joint escrow account under your institutions yet."
                  testid="sig-accounts-section" />

        <Section title="Recent transactions" rows={txs}
                  empty="No transactions yet."
                  testid="sig-txs-section" />
      </div>
    </div>
  );
}

function KPI({ label, value, tone, testId }) {
  const border = tone === "warn" ? "border-amber-500" : "border-brand-navy/15";
  return (
    <div data-testid={testId}
         className={`bg-white p-5 border-2 ${border}`}>
      <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">{label}</div>
      <div className="text-3xl font-serif text-brand-navy mt-1">{value}</div>
    </div>
  );
}

function Section({ title, rows, accounts, empty, testid }) {
  const asAccounts = Array.isArray(accounts);
  const list = asAccounts ? accounts : rows || [];
  return (
    <div className="mb-8" data-testid={testid}>
      <h2 className="font-serif text-xl text-brand-navy mb-3">{title}</h2>
      {list.length === 0 ? (
        <div className="bg-white border border-brand-navy/15 p-6 text-sm text-brand-navy/60">{empty}</div>
      ) : asAccounts ? (
        <div className="bg-white border border-brand-navy/15 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-brand-pale text-[10px] uppercase tracking-widest text-brand-navy/70">
              <tr>
                <th className="px-3 py-2 text-left">Account</th>
                <th className="px-3 py-2 text-left">Institution</th>
                <th className="px-3 py-2 text-left">Account no.</th>
                <th className="px-3 py-2 text-left">Currency</th>
              </tr>
            </thead>
            <tbody>
              {list.map((a) => (
                <tr key={a.id} className="border-t border-brand-navy/10">
                  <td className="px-3 py-2">{a.name}</td>
                  <td className="px-3 py-2">{a.institution}</td>
                  <td className="px-3 py-2 font-mono">{a.account_no}</td>
                  <td className="px-3 py-2">{a.currency}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ) : (
        <div className="bg-white border border-brand-navy/15 overflow-hidden">
          <table className="w-full text-sm">
            <thead className="bg-brand-pale text-[10px] uppercase tracking-widest text-brand-navy/70">
              <tr>
                <th className="px-3 py-2 text-left">Bid</th>
                <th className="px-3 py-2 text-left">Notice</th>
                <th className="px-3 py-2 text-right">Amount</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Signatures</th>
              </tr>
            </thead>
            <tbody>
              {list.map((t) => (
                <tr key={t.id} className="border-t border-brand-navy/10"
                    data-testid={`sig-row-${t.id}`}>
                  <td className="px-3 py-2 font-mono">{t.bid_ref || "—"}</td>
                  <td className="px-3 py-2">{t.notice_ref || "—"}</td>
                  <td className="px-3 py-2 text-right font-mono tabular-nums">
                    {t.currency} {Number(t.amount || 0).toLocaleString()}
                  </td>
                  <td className="px-3 py-2">
                    <span className="inline-block text-[10px] uppercase tracking-widest px-2 py-0.5 border border-brand-navy/15 bg-brand-pale">
                      {t.status}
                    </span>
                  </td>
                  <td className="px-3 py-2 text-xs">
                    <div>PMC {t.signed_by_pmc ? "✓" : "·"}</div>
                    <div>Inst {t.signed_by_institution ? "✓" : "·"}</div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </div>
  );
}
