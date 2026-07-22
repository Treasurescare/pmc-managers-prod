import { useEffect, useState } from "react";
import { toast } from "sonner";
import { Shield, ShieldAlert, ShieldCheck } from "lucide-react";
import DashboardLayout from "@/components/app/DashboardLayout";
import api, { formatApiError } from "@/lib/api";

function actionBadge(action) {
  if (action.startsWith("tender.approve") || action.endsWith(".create")) return "border-success text-success";
  if (action.includes("reject") || action.includes("forfeit")) return "border-destructive text-destructive";
  if (action.includes("award")) return "bg-primary text-white border-primary";
  return "border-muted-foreground text-muted-foreground";
}

export default function AdminAudit() {
  const [events, setEvents] = useState([]);
  const [filter, setFilter] = useState("");
  const [loading, setLoading] = useState(false);
  const [verifyResult, setVerifyResult] = useState(null);
  const [verifying, setVerifying] = useState(false);

  const load = async () => {
    setLoading(true);
    try {
      const { data } = await api.get(`/admin/audit?limit=200${filter ? `&action=${encodeURIComponent(filter)}` : ""}`);
      setEvents(data);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setLoading(false); }
  };
  useEffect(() => { load(); }, [filter]); // eslint-disable-line react-hooks/exhaustive-deps

  const verify = async () => {
    setVerifying(true);
    try {
      const { data } = await api.get("/admin/audit/verify");
      setVerifyResult(data);
      if (data.ok) toast.success(`Chain verified · ${data.checked} events, no tampering`);
      else toast.error(`Tampering detected in ${data.tampered.length} events`);
    } catch (e) { toast.error(formatApiError(e)); }
    finally { setVerifying(false); }
  };

  const actions = Array.from(new Set(events.map((e) => e.action))).sort();

  return (
    <DashboardLayout title="Audit Trail" subtitle="Immutable hash-chained ledger of every governance action" actions={
      <button onClick={verify} disabled={verifying} data-testid="verify-chain"
        className="text-sm border border-foreground px-4 py-2 hover:bg-foreground hover:text-white transition-colors disabled:opacity-60 inline-flex items-center gap-2">
        <Shield className="h-4 w-4" /> {verifying ? "Verifying..." : "Verify chain integrity"}
      </button>
    }>
      {verifyResult && (
        <div className={`border border-l-4 p-4 mb-6 ${verifyResult.ok ? "border-success bg-success/[0.05]" : "border-destructive bg-destructive/[0.05]"}`} data-testid="verify-result">
          <div className="flex items-center gap-3">
            {verifyResult.ok ? <ShieldCheck className="h-5 w-5 text-success" /> : <ShieldAlert className="h-5 w-5 text-destructive" />}
            <div>
              <div className="pmc-label">{verifyResult.ok ? "Chain intact" : "Tampering detected"}</div>
              <div className="text-sm mt-1">
                {verifyResult.checked} events checked · Head hash: <span className="font-mono text-xs">{(verifyResult.head_hash || "").slice(0, 24) || "GENESIS"}...</span>
              </div>
              {!verifyResult.ok && (
                <div className="text-xs text-destructive mt-2">Broken at: {verifyResult.tampered.map((t) => `#${t.seq}`).join(", ")}</div>
              )}
            </div>
          </div>
        </div>
      )}

      <div className="mb-4 flex gap-2 flex-wrap" data-testid="audit-filters">
        <button onClick={() => setFilter("")} data-testid="audit-filter-all"
          className={`text-[11px] tracking-widest uppercase px-2 py-1 border ${filter === "" ? "bg-foreground text-white border-foreground" : "border-muted-foreground/30 text-muted-foreground hover:border-foreground"}`}>All</button>
        {actions.map((a) => (
          <button key={a} onClick={() => setFilter(a)} data-testid={`audit-filter-${a.replace(/\./g, '-')}`}
            className={`text-[11px] tracking-widest uppercase px-2 py-1 border ${filter === a ? "bg-foreground text-white border-foreground" : "border-muted-foreground/30 text-muted-foreground hover:border-foreground"}`}>
            {a}
          </button>
        ))}
      </div>

      <div className="border overflow-x-auto">
        <table className="w-full text-sm" data-testid="audit-table">
          <thead className="bg-muted/30 border-b"><tr>
            <th className="pmc-label text-left px-3 py-2">Seq</th>
            <th className="pmc-label text-left px-3 py-2">Action</th>
            <th className="pmc-label text-left px-3 py-2">Actor</th>
            <th className="pmc-label text-left px-3 py-2">Target</th>
            <th className="pmc-label text-left px-3 py-2">Details</th>
            <th className="pmc-label text-left px-3 py-2">Timestamp</th>
            <th className="pmc-label text-left px-3 py-2">Hash</th>
          </tr></thead>
          <tbody>
            {events.map((e) => (
              <tr key={e.id} className="border-b hover:bg-muted/40" data-testid={`audit-row-${e.seq}`}>
                <td className="px-3 py-2 font-mono">#{e.seq}</td>
                <td className="px-3 py-2"><span className={`text-[10px] font-semibold tracking-widest px-1.5 py-0.5 border ${actionBadge(e.action)}`}>{e.action}</span></td>
                <td className="px-3 py-2 text-xs">
                  <div>{e.actor_email || "—"}</div>
                  <div className="text-muted-foreground">{e.actor_role}</div>
                </td>
                <td className="px-3 py-2 text-xs font-mono">{e.target_type}<br/><span className="text-muted-foreground">{e.target_id?.slice(0, 12)}...</span></td>
                <td className="px-3 py-2 text-xs">
                  <pre className="whitespace-pre-wrap max-w-md">{JSON.stringify(e.details || {}, null, 0).slice(0, 180)}</pre>
                </td>
                <td className="px-3 py-2 text-xs font-mono text-muted-foreground">{new Date(e.created_at).toLocaleString()}</td>
                <td className="px-3 py-2 text-xs font-mono text-muted-foreground" title={e.event_hash}>{(e.event_hash || "").slice(0, 8)}...</td>
              </tr>
            ))}
            {events.length === 0 && (
              <tr><td colSpan={7} className="px-3 py-12 text-center text-muted-foreground">
                {loading ? "Loading…" : "No audit events yet. Take an action (create a tender, approve, award, etc.) to start the chain."}
              </td></tr>
            )}
          </tbody>
        </table>
      </div>
    </DashboardLayout>
  );
}
