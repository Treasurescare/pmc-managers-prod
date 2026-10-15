/**
 * EscrowAccountDashboardBody — v52e. Reads real data from
 * /api/v1/escrow-accounts/me/dashboard: joint accounts the institution's
 * signatories operate, every transaction on those accounts and the
 * subset awaiting the institution's signature. Falls back cleanly to the
 * empty state when PMC hasn't opened a joint account yet.
 */
import { useEffect, useState } from "react";
import { api, showApiError } from "@/lib/api";

const TABS = [
  ["overview",     "Overview"],
  ["pending",      "Pending signatures"],
  ["transactions", "All transactions"],
  ["accounts",     "Joint accounts"],
  ["profile",      "Institution profile"],
];

export default function EscrowAccountDashboardBody({ account }) {
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState(null);

  useEffect(() => {
    api.get("/api/v1/escrow-accounts/me/dashboard")
      .then((r) => setData(r.data))
      .catch(showApiError);
  }, []);

  const inst = data?.institution || account?.institution || {};
  const pending = data?.pending_signatures || [];
  const txs = data?.transactions || [];
  const accounts = data?.joint_accounts || [];

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
        {TABS.map(([key, label]) => {
          const badge =
            key === "pending" ? pending.length :
            key === "transactions" ? txs.length :
            key === "accounts" ? accounts.length : 0;
          return (
            <button key={key} type="button" onClick={() => setTab(key)}
                    data-testid={`escrow-tab-${key}`}
                    className={"text-left px-3 py-2 text-sm rounded flex items-center justify-between " +
                                (tab === key
                                   ? "bg-brand-navy text-white"
                                   : "hover:bg-brand-pale text-brand-navy/80")}>
              <span>{label}</span>
              {badge > 0 && (
                <span className={"text-[10px] px-1.5 py-0.5 rounded-full " +
                                  (tab === key ? "bg-white text-brand-navy" : "bg-brand-navy text-white")}>
                  {badge}
                </span>
              )}
            </button>
          );
        })}
      </aside>

      <main className="flex-1 p-8">
        {tab === "overview" && (
          <>
            <h1 className="font-serif text-2xl text-brand-navy">Overview</h1>
            <p className="text-sm text-brand-navy/60 mb-6">
              Signed in to {inst.legal_name || "your institution"}
            </p>
            <div className="grid md:grid-cols-3 gap-4">
              <KPI label="Pending signatures" value={pending.length}
                   onClick={() => setTab("pending")} testId="escrow-kpi-pending" />
              <KPI label="Joint accounts" value={accounts.length}
                   onClick={() => setTab("accounts")} testId="escrow-kpi-accounts" />
              <KPI label="Transactions" value={txs.length}
                   onClick={() => setTab("transactions")} testId="escrow-kpi-transactions" />
            </div>
            {inst.status === "submitted" && (
              <p className="mt-6 text-sm text-brand-navy/70">
                Your registration is with PMC's review team. We'll notify you by
                email and in-app when there's an update — usually within 3 business days.
              </p>
            )}
            {inst.status === "approved" && pending.length === 0 && accounts.length === 0 && (
              <p className="mt-6 text-sm text-brand-navy/70">
                Approved — waiting for PMC to open the first joint escrow account
                with your institution. Your signatories can already sign in from the
                main login page.
              </p>
            )}
          </>
        )}
        {tab === "pending" && (
          <TxList title="Pending signatures" rows={pending} empty="Nothing is waiting on your signature right now." />
        )}
        {tab === "transactions" && (
          <TxList title="All transactions" rows={txs} empty="No transactions on your joint accounts yet." />
        )}
        {tab === "accounts" && (
          <AccountsList rows={accounts} />
        )}
        {tab === "profile" && (
          <ProfileView account={account} inst={inst} />
        )}
      </main>
    </div>
  );
}

function KPI({ label, value, onClick, testId }) {
  return (
    <button type="button" onClick={onClick}
            data-testid={testId}
            className="text-left bg-white p-5 border border-brand-navy/15 hover:border-brand-gold transition-colors">
      <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">{label}</div>
      <div className="text-3xl font-serif text-brand-navy mt-1">{value}</div>
      <div className="text-[10px] text-brand-navy/40 mt-1">Click to open →</div>
    </button>
  );
}

function TxList({ title, rows, empty }) {
  return (
    <>
      <h1 className="font-serif text-2xl text-brand-navy mb-4">{title}</h1>
      {rows.length === 0 ? (
        <div className="bg-white border border-brand-navy/15 p-6 text-sm text-brand-navy/60">
          {empty}
        </div>
      ) : (
        <div className="bg-white border border-brand-navy/15 overflow-hidden">
          <table className="w-full text-sm" data-testid="escrow-tx-table">
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
              {rows.map((t) => (
                <tr key={t.id} className="border-t border-brand-navy/5">
                  <td className="px-3 py-2 font-mono text-xs">{t.bid_ref}</td>
                  <td className="px-3 py-2 font-mono text-xs">{t.notice_ref}</td>
                  <td className="px-3 py-2 text-right">
                    {t.amount?.toLocaleString?.()} {t.currency}
                  </td>
                  <td className="px-3 py-2 text-xs">{t.status}</td>
                  <td className="px-3 py-2 text-xs">
                    {t.signed_by_pmc ? "PMC ✓" : "PMC ·"} ·{" "}
                    {t.signed_by_institution ? "Us ✓" : "Us ·"}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
    </>
  );
}

function AccountsList({ rows }) {
  return (
    <>
      <h1 className="font-serif text-2xl text-brand-navy mb-4">Joint accounts</h1>
      {rows.length === 0 ? (
        <div className="bg-white border border-brand-navy/15 p-6 text-sm text-brand-navy/60">
          You'll see each joint escrow account PMC has opened with your institution here.
        </div>
      ) : (
        <div className="grid md:grid-cols-2 gap-3">
          {rows.map((a) => (
            <div key={a.id} className="bg-white p-5 border border-brand-navy/15">
              <div className="text-[10px] uppercase tracking-widest text-brand-navy/60">
                {a.currency || "—"} account
              </div>
              <div className="font-serif text-lg text-brand-navy mt-1">{a.name}</div>
              <div className="text-xs font-mono text-brand-navy/60 mt-1">{a.account_no}</div>
              {typeof a.balance === "number" && (
                <div className="text-sm mt-2">
                  Balance:{" "}
                  <strong>{a.balance.toLocaleString?.()} {a.currency}</strong>
                </div>
              )}
            </div>
          ))}
        </div>
      )}
    </>
  );
}

function ProfileView({ account, inst }) {
  return (
    <>
      <h1 className="font-serif text-2xl text-brand-navy mb-4">Institution profile</h1>
      <div className="bg-white border border-brand-navy/15 p-6 text-sm text-brand-navy/80 space-y-1">
        <div><b>Legal name:</b> {inst.legal_name || "—"}</div>
        <div><b>Status:</b> {inst.status || "—"}</div>
        <div><b>Primary contact:</b> {account?.email}</div>
        <div><b>Phone:</b> {account?.primary_contact_phone || "—"}</div>
        <div className="text-[11px] text-brand-navy/50 mt-2">
          Use the avatar menu (top right) to update your name or phone.
          To change registration data after approval, contact PMC support.
        </div>
      </div>
    </>
  );
}
