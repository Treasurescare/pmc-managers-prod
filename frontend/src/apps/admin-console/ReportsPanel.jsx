/**
 * ReportsPanel — one-click stakeholder deliverables.
 *
 * Streams five artefacts direct from the backend so the admin can circulate
 * the exact same "asked vs delivered" statement across Excel/Word/PDF and
 * hand the flowchart to the board.
 */
import { useState } from "react";
import { useI18n } from "@/context/I18nContext";

const API = process.env.REACT_APP_BACKEND_URL;

const TONE = {
  emerald: "border-emerald-500 text-emerald-800 hover:bg-emerald-50",
  sky:     "border-sky-500     text-sky-800     hover:bg-sky-50",
  navy:    "border-brand-navy  text-brand-navy  hover:bg-brand-navy hover:text-white",
  purple:  "border-purple-500  text-purple-800  hover:bg-purple-50",
};

export default function ReportsPanel() {
  const { t } = useI18n();
  const [snap, setSnap] = useState({ state: "idle", data: null, error: null });

  const CARDS = [
    { id: "xlsx", title: t("panels.reports.xlsx_title"),
      hint: t("panels.reports.xlsx_hint"),
      href: `${API}/api/v1/reports/comparative-statement.xlsx`, tone: "emerald" },
    { id: "docx", title: t("panels.reports.docx_title"),
      hint: t("panels.reports.docx_hint"),
      href: `${API}/api/v1/reports/comparative-statement.docx`, tone: "sky" },
    { id: "pdf", title: t("panels.reports.pdf_title"),
      hint: t("panels.reports.pdf_hint"),
      href: `${API}/api/v1/reports/comparative-statement.pdf`, tone: "navy" },
    { id: "flow-svg", title: t("panels.reports.svg_title"),
      hint: t("panels.reports.svg_hint"),
      href: `${API}/api/v1/reports/flowchart.svg`, tone: "purple" },
    { id: "flow-pdf", title: t("panels.reports.flow_pdf_title"),
      hint: t("panels.reports.flow_pdf_hint"),
      href: `${API}/api/v1/reports/flowchart.pdf`, tone: "purple" },
  ];

  const runSnapshot = async () => {
    setSnap({ state: "busy", data: null, error: null });
    try {
      const r = await fetch(`${API}/api/v1/reports/snapshot`, {
        method: "POST", credentials: "include",
      });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      setSnap({ state: "done", data: await r.json(), error: null });
    } catch (e) {
      setSnap({ state: "error", data: null, error: e.message });
    }
  };

  return (
    <div className="space-y-8" data-testid="reports-panel">
      <section>
        <div className="pmc-label">{t("panels.reports.kicker")}</div>
        <h2 className="font-display text-2xl text-brand-navy mt-1">
          {t("panels.reports.heading")}
        </h2>
        <p className="text-sm text-brand-navy/60 mt-2 max-w-2xl">
          {t("panels.reports.description")}
        </p>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {CARDS.map((c) => (
          <a key={c.id} href={c.href} target="_blank" rel="noreferrer"
             data-testid={`report-${c.id}`}
             className={`block border-2 bg-white p-5 transition-colors ${TONE[c.tone]}`}>
            <div className="text-[10px] uppercase tracking-widest opacity-70">
              {c.id.startsWith("flow") ? t("panels.reports.flow_kicker") : t("panels.reports.cs_kicker")}
            </div>
            <h3 className="font-display text-lg mt-1">{c.title}</h3>
            <p className="text-xs opacity-80 mt-2">{c.hint}</p>
            <div className="mt-4 text-[11px] uppercase tracking-widest font-semibold">
              ⬇ {t("panels.reports.download")}
            </div>
          </a>
        ))}
      </div>

      <section className="border-t border-brand-navy/10 pt-6">
        <div className="pmc-label">{t("panels.reports.snapshot_kicker")}</div>
        <h3 className="font-display text-lg text-brand-navy mt-1">
          {t("panels.reports.snapshot_heading")}
        </h3>
        <p className="text-sm text-brand-navy/60 mt-1 max-w-2xl">
          {t("panels.reports.snapshot_desc")}
        </p>
        <button
          type="button"
          onClick={runSnapshot}
          disabled={snap.state === "busy"}
          data-testid="reports-snapshot-btn"
          className="mt-3 border-2 border-brand-navy text-brand-navy px-5 py-2 text-sm font-semibold uppercase tracking-widest hover:bg-brand-navy hover:text-white transition-colors disabled:opacity-50"
        >
          {snap.state === "busy" ? t("panels.reports.snapshot_saving") : t("panels.reports.snapshot_btn")}
        </button>
        {snap.state === "error" && (
          <p className="text-sm text-red-600 mt-3" data-testid="reports-snapshot-error">
            Snapshot failed: {snap.error}
          </p>
        )}
        {snap.state === "done" && snap.data && (
          <div className="mt-3 border border-emerald-500 bg-emerald-50 p-4"
               data-testid="reports-snapshot-result">
            <div className="text-xs uppercase tracking-widest text-emerald-800 font-semibold">
              {t("panels.reports.wrote_prefix")} {snap.data.files.length} {t("panels.reports.files_at")} {snap.data.generated_at}
            </div>
            <ul className="mt-2 space-y-1 text-sm text-emerald-900">
              {snap.data.files.map((f) => (
                <li key={f.file} className="flex justify-between gap-4">
                  <code>{f.path}</code>
                  <span className="opacity-70">{Math.round(f.bytes / 1024)} KB</span>
                </li>
              ))}
            </ul>
            <p className="text-xs text-emerald-800/80 mt-3">
              {t("panels.reports.push_hint")}
            </p>
          </div>
        )}
      </section>

      <section className="mt-6 border-l-4 border-brand-navy-soft/40 pl-5 max-w-2xl">
        <div className="pmc-label">{t("panels.reports.guardrails_title")}</div>
        <ul className="mt-2 space-y-2 text-sm text-brand-navy/85 list-disc pl-4">
          <li>EMD held in a joint escrow account, dual-officer control (PMC + escrow institution).</li>
          <li>Release requires both officers to sign the same action (contractor / vendor refund / forfeit).</li>
          <li>KYC moves forward in the workflow so vendors are validated before bidding (planned).</li>
          <li>Technical &amp; commercial evaluations remain segregated with per-stage authority (planned).</li>
          <li>AI stays advisory. All substantive decisions remain attributable and auditable.</li>
        </ul>
      </section>
    </div>
  );
}
