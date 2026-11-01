import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { TenderTracker } from "@/apps/admin-console/notice/TenderTracker";

export const DashTenderTracker = () => {
  const [rows, setRows] = useState(null);
  useEffect(() => { api.get("/api/v1/tender-tracker/live").then((r) => setRows(r.data.tenders)).catch(() => setRows([])); }, []);
  return (
    <section className="pmc-panel" style={{ overflow: "hidden" }} data-testid="dash-tracker-panel">
      <div className="pmc-panel__head"><h2 className="pmc-panel__title">Live tender progress</h2>
        <span className="pmc-muted" style={{ fontSize: "12px" }}>{rows ? `${rows.length} live tender(s) · gold dot = current step` : "Loading…"}</span></div>
      <div className="px-4 pb-3">
        {rows && !rows.length && <div className="text-sm py-3 text-brand-navy/60" data-testid="dash-tracker-empty">No live tenders in progress.</div>}
        {(rows || []).map((t) => (
          <a key={t.notice_ref} href={`/admin/e/notices?q=${encodeURIComponent(t.notice_ref)}`} className="block py-2 border-t border-brand-navy/10 hover:bg-brand-navy/[0.03] transition-colors" data-testid={`dash-tracker-row-${t.notice_ref}`}>
            <div className="text-xs flex gap-3 flex-wrap"><span className="font-mono">{t.notice_ref}</span><b className="truncate max-w-[480px]">{t.title}</b>
              {t.deadline && <span className="text-brand-navy/50">closes {String(t.deadline).slice(0, 10)}</span>}</div>
            <TenderTracker refKey={`dash-${t.notice_ref}`} t={t} />
          </a>))}
      </div>
    </section>);
};
