/**
 * EscrowAccountDashboardBody — v56. Approved-institution landing view. Now
 * wrapped in the shared PortalShellE frame so it matches the admin console
 * exactly: a fixed dark sidebar on desktop that collapses to an off-canvas
 * drawer (single hamburger + scrim) on tablet/phone, and a white sticky top
 * bar carrying the notifications bell + avatar menu. The five sections live
 * as shell nav items; no more legacy fixed `w-64` sidebar.
 *
 * Reads real data from /api/v1/escrow-accounts/me/dashboard.
 */
import { useEffect, useState } from "react";
import { toast } from "sonner";
import { api, showApiError } from "@/lib/api";
import PortalShellE from "@/apps/shared/PortalShellE";
import EscrowHeaderActions from "./EscrowAccountHeader";
import EscrowDashboardChart from "./EscrowDashboardChart";
import EscrowInstitutionProfile from "./EscrowInstitutionProfile";
import TransactionDetailModal from "./TransactionDetailModal";

const TABS = [
  ["overview",     "Overview",            "i-home"],
  ["pending",      "Pending signatures",  "i-sign"],
  ["transactions", "All transactions",    "i-file"],
  ["accounts",     "Joint accounts",      "i-briefcase"],
  ["profile",      "Institution profile", "i-users"],
];

export default function EscrowAccountDashboardBody({ account, onProfileUpdated }) {
  const [tab, setTab] = useState("overview");
  const [data, setData] = useState(null);
  const [openTxId, setOpenTxId] = useState(null);

  const reload = () =>
    api.get("/api/v1/escrow-accounts/me/dashboard")
      .then((r) => setData(r.data))
      .catch(showApiError);

  useEffect(() => { reload(); }, []);

  const inst = data?.institution || account?.institution || {};
  const pending = data?.pending_signatures || [];
  const txs = data?.transactions || [];
  const accounts = data?.joint_accounts || [];

  const badges = { pending: pending.length, transactions: txs.length, accounts: accounts.length };
  const shellNav = TABS.map(([key, label, icon]) => ({
    key, label, icon, badge: badges[key] || null, testid: `escrow-tab-${key}`,
  }));
  const activeLabel = (TABS.find(([k]) => k === tab) || [])[1] || "Overview";

  return (
    <PortalShellE
      rootTestId="escrow-account-dashboard"
      sideTestId="escrow-sidebar"
      brand={{ title: "PMC Managers", sub: inst.legal_name || "Escrow portal" }}
      items={shellNav}
      activeKey={tab}
      onSelect={setTab}
      crumb={<>Escrow / <b>{activeLabel}</b></>}
      header={<EscrowHeaderActions account={account} onProfileUpdated={onProfileUpdated} />}
    >
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
          {inst.status === "changes_requested" && (
            <div className="mt-6 px-4 py-3 border border-orange-300 bg-orange-50 text-orange-900 text-sm"
                 data-testid="escrow-changes-pending-banner">
              <strong>Changes pending PMC review.</strong> Your institution is paused
              (not live) while your requested edits await approval. Signatory invites
              are temporarily locked — everything re-activates automatically once PMC
              clears the queue.
            </div>
          )}
          {inst.status === "approved" && pending.length === 0 && accounts.length === 0 && (
            <p className="mt-6 text-sm text-brand-navy/70">
              Approved — waiting for PMC to open the first joint escrow account
              with your institution. Your signatories can already sign in from the
              main login page.
            </p>
          )}
          <div className="mt-6">
            <EscrowDashboardChart />
          </div>
        </>
      )}
      {tab === "pending" && (
        <TxList title="Pending signatures" rows={pending}
                empty="Nothing is waiting on your signature right now."
                onOpen={setOpenTxId}/>
      )}
      {tab === "transactions" && (
        <TxList title="All transactions" rows={txs}
                empty="No transactions on your joint accounts yet."
                onOpen={setOpenTxId}/>
      )}
      {tab === "accounts" && (
        <AccountsList rows={accounts} />
      )}
      {tab === "profile" && (
        <EscrowInstitutionProfile account={account} inst={inst}
                                   onInvited={() => window.location.reload()} />
      )}
      {openTxId && (
        <TransactionDetailModal txId={openTxId}
                                 onClose={() => { setOpenTxId(null); reload(); }}/>
      )}
    </PortalShellE>
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

function SigChip({ label, signed, testId }) {
  return (
    <span
      data-testid={testId}
      className={`inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-[10px] font-semibold uppercase tracking-wide border ${
        signed
          ? "bg-emerald-50 text-emerald-700 border-emerald-200"
          : "bg-amber-50 text-amber-700 border-amber-200"
      }`}
    >
      <span className={`h-1.5 w-1.5 rounded-full ${signed ? "bg-emerald-500" : "bg-amber-500"}`} />
      {label} {signed ? "signed" : "pending"}
    </span>
  );
}

function TxList({ title, rows, empty, onOpen }) {
  return (
    <>
      <h1 className="font-serif text-2xl text-brand-navy mb-4">{title}</h1>
      {rows.length === 0 ? (
        <div className="bg-white border border-brand-navy/15 p-6 text-sm text-brand-navy/60">
          {empty}
        </div>
      ) : (
        <div className="bg-white border border-brand-navy/15 overflow-x-auto">
          <table className="w-full text-sm min-w-[640px]" data-testid="escrow-tx-table">
            <thead className="bg-brand-pale text-[10px] uppercase tracking-widest text-brand-navy/70">
              <tr>
                <th className="px-3 py-2 text-left">Bid</th>
                <th className="px-3 py-2 text-left">Notice</th>
                <th className="px-3 py-2 text-right">Amount</th>
                <th className="px-3 py-2 text-left">Status</th>
                <th className="px-3 py-2 text-left">Signatures</th>
                <th className="px-3 py-2 text-right"></th>
              </tr>
            </thead>
            <tbody>
              {rows.map((t) => (
                <tr key={t.id} className="border-t border-brand-navy/5 hover:bg-brand-pale/50 cursor-pointer"
                    data-testid={`escrow-tx-list-row-${t.id}`}
                    onClick={() => onOpen?.(t.id)}>
                  <td data-label="Bid" className="px-3 py-2 font-mono text-xs">{t.bid_ref || "—"}</td>
                  <td data-label="Notice" className="px-3 py-2 font-mono text-xs">{t.notice_ref || "—"}</td>
                  <td data-label="Amount" className="px-3 py-2 text-right">
                    {t.amount != null ? `${t.amount.toLocaleString?.()} ${t.currency || ""}`.trim() : "—"}
                  </td>
                  <td data-label="Status" className="px-3 py-2 text-xs">{t.status || "—"}</td>
                  <td data-label="Signatures" className="px-3 py-2 text-xs">
                    <span className="inline-flex flex-wrap gap-1.5">
                      <SigChip label="PMC" signed={!!t.signed_by_pmc} testId={`escrow-tx-sig-pmc-${t.id}`} />
                      <SigChip label="Us" signed={!!t.signed_by_institution} testId={`escrow-tx-sig-us-${t.id}`} />
                    </span>
                  </td>
                  <td data-label="" className="px-3 py-2 text-xs text-right text-brand-navy/60">
                    Open →
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
          <div className="px-3 py-2 bg-brand-pale/50 text-[11px] text-brand-navy/60 border-t border-brand-navy/5">
            Click any row to view details · sign the DocuSign document · record payment entries.
          </div>
        </div>
      )}
    </>
  );
}

function AccountsList({ rows }) {
  const dl = (aid, name, emailToo) => {
    const url = `/api/v1/escrow-accounts/me/joint-accounts/${aid}/statement.pdf?email_me=${emailToo ? 1 : 0}`;
    const a = document.createElement("a");
    a.href = url;
    a.download = `statement-${(name || "account").replace(/\s+/g, "_")}.pdf`;
    document.body.appendChild(a); a.click(); a.remove();
    if (emailToo) toast.success("Statement downloaded and emailed");
    else toast.success("Statement downloaded");
  };
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
            <div key={a.id} className="bg-white p-5 border border-brand-navy/15"
                 data-testid={`escrow-joint-${a.id}`}>
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
              <div className="mt-3 flex flex-wrap gap-2">
                <button type="button" onClick={() => dl(a.id, a.name, false)}
                        data-testid={`escrow-statement-dl-${a.id}`}
                        className="px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-navy/30 text-brand-navy hover:bg-brand-navy hover:text-white">
                  Download statement
                </button>
                <button type="button" onClick={() => dl(a.id, a.name, true)}
                        data-testid={`escrow-statement-email-${a.id}`}
                        className="px-3 py-1.5 text-[10px] uppercase tracking-widest border border-brand-gold text-brand-navy hover:bg-brand-gold">
                  Download + email me
                </button>
              </div>
            </div>
          ))}
        </div>
      )}
    </>
  );
}
