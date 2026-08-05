/**
 * ReportsPanel — one-click stakeholder deliverables.
 *
 * Streams five artefacts direct from the backend so the admin can circulate
 * the exact same "asked vs delivered" statement across Excel/Word/PDF and
 * hand the flowchart to the board.
 */
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
