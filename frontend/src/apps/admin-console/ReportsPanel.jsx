/**
 * ReportsPanel — one-click stakeholder deliverables.
 *
 * Streams five artefacts direct from the backend so the admin can circulate
 * the exact same "asked vs delivered" statement across Excel/Word/PDF and
 * hand the flowchart to the board.
 */
import { useState } from "react";

const API = process.env.REACT_APP_BACKEND_URL;

const CARDS = [
  { id: "xlsx", title: "Excel — Asked vs Delivered",
    hint: "Row-per-scope-item, colour-coded by status. Best for tracking updates.",
    href: `${API}/api/v1/reports/comparative-statement.xlsx`, tone: "emerald" },
  { id: "docx", title: "Word — Narrative brief",
    hint: "Executive summary + full comparison table + architecture guardrails.",
    href: `${API}/api/v1/reports/comparative-statement.docx`, tone: "sky" },
  { id: "pdf", title: "PDF — Boardroom handout",
    hint: "A4 landscape, watermarked, ready to email or print for stakeholders.",
    href: `${API}/api/v1/reports/comparative-statement.pdf`, tone: "navy" },
  { id: "flow-svg", title: "Flow chart — SVG",
    hint: "Vector chart with 5 swim lanes: Tender · Vendor · Escrow · Award · Governance.",
    href: `${API}/api/v1/reports/flowchart.svg`, tone: "purple" },
  { id: "flow-pdf", title: "Flow chart — PDF (A3)",
    hint: "Same chart rendered A3-landscape for large-format print or presentations.",
    href: `${API}/api/v1/reports/flowchart.pdf`, tone: "purple" },
];

const TONE = {
  emerald: "border-emerald-500 text-emerald-800 hover:bg-emerald-50",
  sky:     "border-sky-500     text-sky-800     hover:bg-sky-50",
  navy:    "border-brand-navy  text-brand-navy  hover:bg-brand-navy hover:text-white",
  purple:  "border-purple-500  text-purple-800  hover:bg-purple-50",
};

export default function ReportsPanel() {
  const [snap, setSnap] = useState({ state: "idle", data: null, error: null });

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
        <div className="pmc-label">Stakeholder brief</div>
        <h2 className="font-display text-2xl text-brand-navy mt-1">
          A live snapshot of what was asked vs what has been delivered
        </h2>
        <p className="text-sm text-brand-navy/60 mt-2 max-w-2xl">
          Each file is rendered on-the-fly from the same source of truth — the roadmap
          you and the team have been iterating on. Download and circulate freely.
          Every substantive action on this platform is audit-logged; the AI copilot is
          advisory-only.
        </p>
      </section>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {CARDS.map((c) => (
          <a key={c.id} href={c.href} target="_blank" rel="noreferrer"
             data-testid={`report-${c.id}`}
             className={`block border-2 bg-white p-5 transition-colors ${TONE[c.tone]}`}>
            <div className="text-[10px] uppercase tracking-widest opacity-70">
              {c.id.startsWith("flow") ? "Flow chart" : "Comparative statement"}
            </div>
            <h3 className="font-display text-lg mt-1">{c.title}</h3>
            <p className="text-xs opacity-80 mt-2">{c.hint}</p>
            <div className="mt-4 text-[11px] uppercase tracking-widest font-semibold">
              ⬇ Download
            </div>
          </a>
        ))}
      </div>

      <section className="border-t border-brand-navy/10 pt-6">
        <div className="pmc-label">Save snapshot to repo</div>
        <h3 className="font-display text-lg text-brand-navy mt-1">
          Persist all five artefacts into <code>/app/docs/reports/</code> so the next
          "Save to Github" carries them
        </h3>
        <p className="text-sm text-brand-navy/60 mt-1 max-w-2xl">
          Downloads are in-memory only — they never touch the repo. Click below and
          the backend writes fresh copies into the Git-tracked <code>docs/reports</code> folder;
          then use <em>Save to Github</em> in the chat input to push them.
        </p>
        <button
          type="button"
          onClick={runSnapshot}
          disabled={snap.state === "busy"}
          data-testid="reports-snapshot-btn"
          className="mt-3 border-2 border-brand-navy text-brand-navy px-5 py-2 text-sm font-semibold uppercase tracking-widest hover:bg-brand-navy hover:text-white transition-colors disabled:opacity-50"
        >
          {snap.state === "busy" ? "Saving…" : "Save snapshot to repo"}
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
              Wrote {snap.data.files.length} file(s) at {snap.data.generated_at}
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
              Now click <strong>Save to Github</strong> in the chat input to push these into your repo.
            </p>
          </div>
        )}
      </section>

      <section className="mt-6 border-l-4 border-brand-navy-soft/40 pl-5 max-w-2xl">
        <div className="pmc-label">Architecture guardrails accepted</div>
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
