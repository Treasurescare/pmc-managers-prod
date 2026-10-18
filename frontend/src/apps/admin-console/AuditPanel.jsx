import { useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, formatApiError, showApiError} from "@/lib/api";
import { useI18n } from "@/context/I18nContext";
import { InfoDot } from "@/components/InfoDot";
import { useListPager } from "@/components/ListPager";

export default function AuditPanel() {
  const { t } = useI18n();
  const [events, setEvents] = useState([]);
  const [verifyResult, setVerifyResult] = useState(null);
  const [repairing, setRepairing] = useState(false);
  // AU-01 fix — filter bar; v52m — filters run SERVER-SIDE now (the old
  // client filter only saw the last 100 events, so older matches vanished).
  const [flt, setFlt] = useState({ actor: "", type: "", from: "", to: "" });

  useEffect(() => {
    const handle = setTimeout(() => {
      adminApi.audit({
        limit: 500,
        actor: flt.actor || undefined,
        event_type: flt.type || undefined,
        from_date: flt.from || undefined,
        to_date: flt.to || undefined,
      })
        .then(setEvents)
        .catch((err) => console.warn("Failed to load audit events:", err));
    }, 350);
    return () => clearTimeout(handle);
  }, [flt.actor, flt.type, flt.from, flt.to]);

  const filtered = events;

  const exportCsv = () => {
    const head = ["seq", "event_type", "target_type", "target_id", "actor_email", "at", "current_hash"];
    const rows = [head, ...filtered.map((e) => [e.seq, e.event_type, e.target_type, e.target_id, e.actor_email || "", e.at || "", e.current_hash || ""])];
    const csv = rows.map((r) => r.map((c) => `"${String(c ?? "").replace(/"/g, '""')}"`).join(",")).join("\n");
    const url = URL.createObjectURL(new Blob([csv], { type: "text/csv" }));
    const a = document.createElement("a");
    a.href = url;
    a.download = `pmc-audit${flt.actor ? "-" + flt.actor.replace(/[^a-z0-9]/gi, "_") : ""}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const { paged, controls } = useListPager(filtered, { testid: "audit-pager" });

  const verify = async () => {
    try { setVerifyResult(await adminApi.verifyAudit()); }
    catch (err) { showApiError(err); }
  };

  const repair = async () => {
    if (!window.confirm("Recompute hash links across the whole ledger? Event payloads are never modified — only the chain links. The repair itself is recorded on the ledger.")) return;
    setRepairing(true);
    try {
      const r = await adminApi.repairAudit();
      toast.success(`Chain repaired · ${r.events_checked} events relinked from seq #${r.first_broken_seq ?? "—"}`);
      setVerifyResult(await adminApi.verifyAudit());
    } catch (err) { showApiError(err); }
    finally { setRepairing(false); }
  };

  return (
    <div data-testid="admin-audit-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-brand-navy/70">{t("panels.audit.hint")}</div>
        <button type="button" onClick={verify} data-testid="audit-verify"
          className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">
          {t("panels.audit.verify")}
          <InfoDot tip="Re-computes the hash chain across every event and confirms nothing has been tampered with. Read-only." />
        </button>
      </div>
      {verifyResult && (
        <div data-testid="audit-verify-result" className={"mb-4 border p-4 text-sm " + (verifyResult.ok ? "border-green-500/40 bg-green-50 text-green-800" : "border-red-500/40 bg-red-50 text-red-800")}>
          {verifyResult.ok
            ? <>{t("panels.audit.verified_ok")} · {verifyResult.events_checked} {t("panels.audit.events_checked")}</>
            : <div className="flex items-center justify-between gap-3 flex-wrap">
                <span>{t("panels.audit.chain_broken_at")} #{verifyResult.at_seq} — {verifyResult.reason}. This is a broken hash link from a legacy write race; event payloads are intact.</span>
                <button type="button" onClick={repair} disabled={repairing}
                        data-testid="audit-repair"
                        className="px-4 py-1.5 text-[11px] uppercase tracking-widest bg-red-800 text-white hover:bg-red-900 disabled:opacity-50">
                  {repairing ? "Repairing…" : "Repair chain"}
                </button>
              </div>}
        </div>
      )}
      {/* AU-01 fix — filter bar: actor / type / date range */}
      <div className="border border-brand-navy/10 bg-white p-3 mb-3 grid gap-2 md:grid-cols-5 items-end" data-testid="audit-filter-bar">
        <label className="text-xs"><div className="pmc-label mb-1">Actor email<InfoDot tip="Substring match on the acting user's email. Case-insensitive." /></div>
          <input value={flt.actor} onChange={(e) => setFlt({ ...flt, actor: e.target.value })}
                 data-testid="audit-filter-actor"
                 placeholder="e.g. adminsupport@…"
                 className="w-full px-3 py-2 border border-brand-navy/20 text-sm"/></label>
        <label className="text-xs"><div className="pmc-label mb-1">Event type<InfoDot tip="Substring match on the event type slug (e.g. 'notice.publish', 'bid.decision.accept')." /></div>
          <input value={flt.type} onChange={(e) => setFlt({ ...flt, type: e.target.value })}
                 data-testid="audit-filter-type"
                 placeholder="e.g. notice.publish"
                 className="w-full px-3 py-2 border border-brand-navy/20 text-sm"/></label>
        <label className="text-xs"><div className="pmc-label mb-1">From (UTC)<InfoDot tip="Inclusive lower bound of event timestamp. UTC." /></div>
          <input type="date" value={flt.from} max={flt.to || undefined}
                 onChange={(e) => setFlt({ ...flt, from: e.target.value })}
                 data-testid="audit-filter-from"
                 className="w-full px-3 py-2 border border-brand-navy/20 text-sm"/></label>
        <label className="text-xs"><div className="pmc-label mb-1">To (UTC)<InfoDot tip="Inclusive upper bound (end-of-day UTC)." /></div>
          <input type="date" value={flt.to} min={flt.from || undefined}
                 onChange={(e) => setFlt({ ...flt, to: e.target.value })}
                 data-testid="audit-filter-to"
                 className="w-full px-3 py-2 border border-brand-navy/20 text-sm"/></label>
        <button type="button" onClick={() => setFlt({ actor: "", type: "", from: "", to: "" })}
                data-testid="audit-filter-clear"
                className="px-3 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
          Clear
        </button>
        <div className="md:col-span-5 flex items-center justify-between gap-3 flex-wrap">
          <span className="text-[11px] text-brand-navy/50">
            Showing {filtered.length} events (server-filtered, latest 500 max).
          </span>
          <button type="button" onClick={exportCsv} data-testid="audit-export-csv"
                  className="px-3 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
            Export CSV{flt.actor ? ` · ${flt.actor}` : ""}
          </button>
        </div>
      </div>

      <div className="border border-brand-navy/10 bg-white">
        {/* v52cf — table scrolls horizontally; the pager used to sit inside
            the overflow-x-auto wrapper and get clipped (user: "page numbers
            not visible on Audit Ledger"). Table and pager are now separate. */}
        <div className="overflow-x-auto">
          <table className="pmc-table w-full text-sm">
            <thead>
              <tr className="text-left text-brand-navy/60">
                <th className="px-4 py-2">#</th><th className="px-4 py-2">{t("panels.audit.col_type")}</th><th className="px-4 py-2">{t("panels.audit.col_target")}</th><th className="px-4 py-2">{t("panels.audit.col_actor")}</th><th className="px-4 py-2">{t("panels.audit.col_hash")}</th><th className="px-4 py-2">{t("panels.audit.col_when")}</th>
              </tr>
            </thead>
            <tbody>
              {paged.map((e) => (
                <tr key={e.id} className="border-t border-brand-navy/10" data-testid={`audit-row-${e.seq}`}>
                  <td className="px-4 py-2 font-mono">{e.seq}</td>
                  <td className="px-4 py-2">{e.event_type}</td>
                  <td className="px-4 py-2 font-mono text-xs">{e.target_type}:{e.target_id?.slice(-8)}</td>
                  <td className="px-4 py-2 text-xs">{e.actor_email || "—"}</td>
                  <td className="px-4 py-2 font-mono text-[10px] text-brand-navy/50">{e.current_hash?.slice(0, 12)}…</td>
                  <td className="px-4 py-2 text-xs">{e.at?.slice(0, 19).replace("T", " ")}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {controls}
      </div>
    </div>
  );
}
