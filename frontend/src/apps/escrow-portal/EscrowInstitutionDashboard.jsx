import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";
import { api, showApiError } from "@/lib/api";

/**
 * EscrowInstitutionDashboard — v51an.
 *
 * Signatory-authenticated view: shows joint accounts the institution
 * operates, every transaction tied to those accounts, and a one-click
 * "Sign off" action for every pending EMD release awaiting the current
 * signatory. Falls back to the magic-link mode (legacy prop API) when no
 * signatory session cookie is present.
 */
export default function EscrowInstitutionDashboard({ institutionId, token }) {
  const nav = useNavigate();
  const [data, setData] = useState(null);
  const [sessionMode, setSessionMode] = useState(null); // "signatory" | "magic"
  const [action, setAction] = useState({}); // txId -> intended action
  const [busy, setBusy] = useState({}); // txId -> bool

  const load = async () => {
    // Try signatory session first.
    try {
      const r = (await api.get("/api/v1/escrow-signatories/dashboard")).data;
      setData(r);
      setSessionMode("signatory");
      return;
    } catch (_e) { /* fall through to magic link */ }
    if (institutionId && token) {
      try {
        const r = (await api.get(`/api/v1/escrow-institutions/${institutionId}/dashboard`,
                                  { params: { token } })).data;
        setData({
          signatory: null, institutions: [{ id: institutionId, legal_name: r.institution?.legal_name }],
          joint_accounts: [], pending_signatures_count: r.pending_signatures_count,
          pending_transactions: [], transactions: [],
          institution_summary: r.institution,
          joint_accounts_count: r.joint_accounts_count,
        });
        setSessionMode("magic");
        return;
      } catch (e) { showApiError(e); return; }
    }
    nav("/escrow/login");
  };
  useEffect(() => { load(); /* eslint-disable-line */ }, [institutionId, token]);

  const sign = async (tx) => {
    const intended = action[tx.id];
    if (!intended) return toast.error("Pick an intended action for this transaction first.");
    setBusy((b) => ({ ...b, [tx.id]: true }));
    try {
      await api.post(`/api/v1/escrow/transactions/${tx.id}/sign`,
                     { intended_action: intended, comment: "Signed from institution dashboard" });
      toast.success(`Signed off ${tx.bid_ref} for ${intended.replace(/_/g, " ")}`);
      await load();
    } catch (e) { showApiError(e); }
    finally { setBusy((b) => ({ ...b, [tx.id]: false })); }
  };

  const logout = async () => {
    try { await api.post("/api/v1/escrow-signatories/auth/logout"); } catch { /* ignore */ }
    nav("/escrow/login");
  };

  if (!data) return <div className="p-8 text-brand-navy/50">Loading…</div>;
  const insts = data.institutions || [];
  const txRows = data.transactions || [];
  const pending = data.pending_transactions || [];

  return (
    <div className="max-w-6xl mx-auto p-6" data-testid="escrow-dashboard">
      <div className="flex items-start justify-between gap-4 flex-wrap mb-4">
        <div>
          <h1 className="text-2xl font-semibold text-brand-navy">
            {insts.map((i) => i.legal_name).filter(Boolean).join(" · ") || "Escrow Institution"}
          </h1>
          {data.signatory?.email && (
            <div className="text-xs text-brand-navy/60 mt-1">
              Signed in as <strong>{data.signatory.email}</strong>
            </div>
          )}
        </div>
        {sessionMode === "signatory" && (
          <button onClick={logout} data-testid="escrow-dashboard-logout"
                  className="text-xs uppercase tracking-widest border border-brand-navy/30 px-3 py-1.5 text-brand-navy hover:bg-brand-navy hover:text-white">
            Sign out
          </button>
        )}
      </div>

      <div className="grid md:grid-cols-3 gap-4 mb-6">
        <KPI label="Joint accounts" n={data.joint_accounts?.length ?? data.joint_accounts_count}
             testid="kpi-accounts" />
        <KPI label="Pending signatures" n={data.pending_signatures_count}
             testid="kpi-pending"
             highlight={(data.pending_signatures_count || 0) > 0} />
        <KPI label="Total transactions" n={txRows.length} testid="kpi-total" />
      </div>

      <section className="bg-white border border-brand-navy/15 mb-6">
        <div className="pmc-label p-4 border-b border-brand-navy/10">
          Pending — awaiting your signature · {pending.length}
        </div>
        {pending.length === 0 ? (
          <div className="p-6 text-sm text-brand-navy/50">
            Nothing waits on your signature right now.
          </div>
        ) : (
          <table className="w-full text-sm" data-testid="pending-tx-table">
            <thead className="text-left text-[10px] uppercase tracking-widest text-brand-navy/50">
              <tr>
                <th className="p-3">Bid</th>
                <th className="p-3">Account</th>
                <th className="p-3">Amount</th>
                <th className="p-3">Received</th>
                <th className="p-3 text-right">Intended action + sign</th>
              </tr>
            </thead>
            <tbody>
              {pending.map((t) => (
                <tr key={t.id} className="border-t border-brand-navy/5" data-testid={`pending-tx-${t.id}`}>
                  <td className="p-3 font-mono text-xs">
                    {t.bid_ref}<br />
                    <span className="text-brand-navy/50">{t.notice_ref}</span>
                  </td>
                  <td className="p-3">
                    {t.account_name || "—"}<br />
                    <span className="text-[11px] text-brand-navy/50">{t.institution}</span>
                  </td>
                  <td className="p-3 font-semibold">
                    {t.currency} {Number(t.amount || 0).toLocaleString()}
                  </td>
                  <td className="p-3 text-xs text-brand-navy/60">
                    {(t.received_at || t.created_at || "").slice(0, 16).replace("T", " ")}
                  </td>
                  <td className="p-3 text-right">
                    <div className="flex items-center justify-end gap-2 flex-wrap">
                      <select value={action[t.id] || ""}
                              onChange={(e) => setAction((a) => ({ ...a, [t.id]: e.target.value }))}
                              data-testid={`pending-tx-action-${t.id}`}
                              className="px-2 py-1 border border-brand-navy/20 text-xs bg-white">
                        <option value="">Pick action…</option>
                        <option value="release_to_contractor">Release → contractor</option>
                        <option value="release_to_vendor">Refund → vendor</option>
                        <option value="forfeit">Forfeit</option>
                      </select>
                      <button onClick={() => sign(t)} disabled={busy[t.id] || !action[t.id]}
                              data-testid={`pending-tx-sign-${t.id}`}
                              className="px-3 py-1 text-[11px] uppercase tracking-widest bg-brand-navy text-white disabled:opacity-40 hover:bg-brand-navy-deep">
                        {busy[t.id] ? "Signing…" : "Sign off"}
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>

      <section className="bg-white border border-brand-navy/15">
        <div className="pmc-label p-4 border-b border-brand-navy/10">
          All transactions · {txRows.length}
        </div>
        {txRows.length === 0 ? (
          <div className="p-6 text-sm text-brand-navy/50">
            No transactions on your joint accounts yet.
          </div>
        ) : (
          <table className="w-full text-sm" data-testid="all-tx-table">
            <thead className="text-left text-[10px] uppercase tracking-widest text-brand-navy/50">
              <tr>
                <th className="p-3">Bid</th>
                <th className="p-3">Account</th>
                <th className="p-3">Amount</th>
                <th className="p-3">Status</th>
                <th className="p-3">Signatures</th>
              </tr>
            </thead>
            <tbody>
              {txRows.map((t) => (
                <tr key={t.id} className="border-t border-brand-navy/5">
                  <td className="p-3 font-mono text-xs">{t.bid_ref}</td>
                  <td className="p-3">{t.account_name || "—"}</td>
                  <td className="p-3">{t.currency} {Number(t.amount || 0).toLocaleString()}</td>
                  <td className="p-3 text-xs">{t.status}</td>
                  <td className="p-3 text-xs">
                    <span className={t.signed_by_pmc ? "text-emerald-700" : "text-brand-navy/40"}>
                      PMC {t.signed_by_pmc ? "✓" : "·"}
                    </span>
                    {" / "}
                    <span className={t.signed_by_institution ? "text-emerald-700" : "text-brand-navy/40"}>
                      Inst {t.signed_by_institution ? "✓" : "·"}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </section>
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
