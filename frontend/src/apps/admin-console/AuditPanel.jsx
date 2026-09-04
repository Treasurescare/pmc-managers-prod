import { useEffect, useState } from "react";
import { toast } from "sonner";
import { adminApi, formatApiError } from "@/lib/api";
import { useI18n } from "@/context/I18nContext";

export default function AuditPanel() {
  const { t } = useI18n();
  const [events, setEvents] = useState([]);
  const [verifyResult, setVerifyResult] = useState(null);
  // AU-01 fix — filter bar
  const [flt, setFlt] = useState({ actor: "", type: "", from: "", to: "" });

  useEffect(() => {
    adminApi.audit({ limit: 100 })
      .then(setEvents)
      .catch((err) => console.warn("Failed to load audit events:", err));
  }, []);

  const filtered = events.filter((e) => {
    if (flt.actor && !(e.actor_email || "").toLowerCase().includes(flt.actor.toLowerCase())) return false;
    if (flt.type && !(e.event_type || "").toLowerCase().includes(flt.type.toLowerCase())) return false;
    if (flt.from && e.at && e.at < flt.from) return false;
    if (flt.to && e.at && e.at > flt.to + "T23:59:59Z") return false;
    return true;
  });

  const verify = async () => {
    try { setVerifyResult(await adminApi.verifyAudit()); }
    catch (err) { toast.error(formatApiError(err)); }
  };

  return (
    <div data-testid="admin-audit-panel">
      <div className="flex items-center justify-between mb-4">
        <div className="text-sm text-brand-navy/70">{t("panels.audit.hint")}</div>
        <button type="button" onClick={verify} data-testid="audit-verify"
          className="px-5 py-2 text-[11px] font-semibold uppercase tracking-widest bg-brand-navy text-white hover:bg-brand-navy-deep">{t("panels.audit.verify")}</button>
      </div>
      {verifyResult && (
        <div data-testid="audit-verify-result" className={"mb-4 border p-4 text-sm " + (verifyResult.ok ? "border-green-500/40 bg-green-50 text-green-800" : "border-red-500/40 bg-red-50 text-red-800")}>
          {verifyResult.ok
            ? <>{t("panels.audit.verified_ok")} · {verifyResult.events_checked} {t("panels.audit.events_checked")}</>
            : <>{t("panels.audit.chain_broken_at")} #{verifyResult.at_seq} — {verifyResult.reason}</>}
        </div>
      )}
      {/* AU-01 fix — filter bar: actor / type / date range */}
      <div className="border border-brand-navy/10 bg-white p-3 mb-3 grid gap-2 md:grid-cols-5 items-end" data-testid="audit-filter-bar">
        <label className="text-xs"><div className="pmc-label mb-1">Actor email</div>
          <input value={flt.actor} onChange={(e) => setFlt({ ...flt, actor: e.target.value })}
                 data-testid="audit-filter-actor"
                 placeholder="e.g. adminsupport@…"
                 className="w-full px-3 py-2 border border-brand-navy/20 text-sm"/></label>
        <label className="text-xs"><div className="pmc-label mb-1">Event type</div>
          <input value={flt.type} onChange={(e) => setFlt({ ...flt, type: e.target.value })}
                 data-testid="audit-filter-type"
                 placeholder="e.g. notice.publish"
                 className="w-full px-3 py-2 border border-brand-navy/20 text-sm"/></label>
        <label className="text-xs"><div className="pmc-label mb-1">From (UTC)</div>
          <input type="date" value={flt.from} onChange={(e) => setFlt({ ...flt, from: e.target.value })}
                 data-testid="audit-filter-from"
                 className="w-full px-3 py-2 border border-brand-navy/20 text-sm"/></label>
        <label className="text-xs"><div className="pmc-label mb-1">To (UTC)</div>
          <input type="date" value={flt.to} onChange={(e) => setFlt({ ...flt, to: e.target.value })}
                 data-testid="audit-filter-to"
                 className="w-full px-3 py-2 border border-brand-navy/20 text-sm"/></label>
        <button type="button" onClick={() => setFlt({ actor: "", type: "", from: "", to: "" })}
                data-testid="audit-filter-clear"
                className="px-3 py-2 text-[11px] uppercase tracking-widest border border-brand-navy/20 text-brand-navy hover:bg-brand-navy/5">
          Clear
        </button>
        <div className="md:col-span-5 text-[11px] text-brand-navy/50">
          Showing {filtered.length} of {events.length} events.
        </div>
      </div>

      <div className="border border-brand-navy/10 bg-white overflow-x-auto">
        <table className="pmc-table w-full text-sm">
          <thead>
            <tr className="text-left text-brand-navy/60">
              <th className="px-4 py-2">#</th><th className="px-4 py-2">{t("panels.audit.col_type")}</th><th className="px-4 py-2">{t("panels.audit.col_target")}</th><th className="px-4 py-2">{t("panels.audit.col_actor")}</th><th className="px-4 py-2">{t("panels.audit.col_hash")}</th><th className="px-4 py-2">{t("panels.audit.col_when")}</th>
            </tr>
          </thead>
          <tbody>
            {filtered.map((e) => (
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
    </div>
  );
}
