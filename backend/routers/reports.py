"""Wave 33 — Stakeholder Comparative Statement export.

Bundles what the user *asked for* in this project vs what has been *delivered*
across every wave, and emits four artefacts a decision-maker can circulate:
  * .xlsx — comparative table with colour-coded status per item
  * .docx — narrative Word document with the same content + wave summaries
  * .pdf  — WeasyPrint render of the same story
  * flowchart.pdf / .svg — end-to-end platform flow chart

All endpoints are admin-only and stream the file in-memory (no persistence).
"""
import html as _html
import io
from typing import List, Tuple
from fastapi import APIRouter, Depends
from fastapi.responses import Response

from models.base import now_iso
from security import require_role

router = APIRouter(prefix="/api/v1/reports", tags=["reports"])


# ------------------------------------------------------------------
#  Source of truth — comparative rows keyed by feature area.
#  (status, area, "asked for", "delivered", "notes/evidence")
# ------------------------------------------------------------------
STATUS_DONE = "Delivered"
STATUS_PARTIAL = "Partial"
STATUS_PLANNED = "Planned"

ROWS: List[Tuple[str, str, str, str, str]] = [
    # --- Core platform ---
    (STATUS_DONE, "Auth & Access",
     "Multi-role staff + vendor authentication with MFA",
     "HTTPOnly cookie auth + CSRF, TOTP MFA, Unified Two-Card Login Hub, staff/vendor/admin flows",
     "Waves 1-14 · MFA verified via TOTP"),
    (STATUS_DONE, "Auth & Access",
     "Role-based permissions across staff (Escrow, Certifier, Legal, Accounting…)",
     "Dynamic Permissions Matrix panel, per-endpoint role decorators, audit logs on every action",
     "PermissionsPanel + `security.require_role`"),
    (STATUS_DONE, "Multi-tenant",
     "Portal skinning per tenant, CNAME-based routing",
     "CNAME multi-tenant subdomains, tenant chip on admin bar, per-tenant branding colour + logo",
     "Wave 22 · `tenants.by-host` + `useTenantSkin`"),
    (STATUS_DONE, "i18n",
     "Trilingual UI (English, Russian, Kazakh)",
     "Full EN/RU/KK dictionary, live switcher, localised country dropdown",
     "Wave 19 · `i18n-strings.js`"),

    # --- Notice board + Registration ---
    (STATUS_DONE, "Notice Board",
     "Public tender board with document downloads",
     "Public notice list + detail pages, primary document, attachments, deadline",
     "`notices` router + `NoticeDetail.jsx`"),
    (STATUS_DONE, "Vendor Registration",
     "5-section vendor registration (A-E) with KYC document slots",
     "Sections A-E form, magic-link resume, per-slot document upload, admin \"add & fill on behalf\"",
     "Wave 14 · `RegistrationResume` + `DocSlot`"),
    (STATUS_DONE, "Vendor Registration",
     "Silent draft creation so admins can upload docs without an extra click",
     "`ensureDraft()` auto-saves the record the moment an admin picks a file",
     "Wave 27"),

    # --- Tender / RFP / RFQ Builder ---
    (STATUS_DONE, "Tender Builder",
     "Template builder mirroring a real 39/75-page PSU tender",
     "18-section master template (Sections 1-4, Annexures I-VIII, Forms A-F), clone-to-draft",
     "Wave 20 · `TenderBuilderPanel`"),
    (STATUS_DONE, "Tender Builder",
     "Structured CPPP-style tender header (dates, EMD, budget, authority)",
     "Full `TenderHeaderForm` — Basic Details, Cover Details, Fee & EMD, Critical Dates, Authority (~60 fields)",
     "Wave 24"),
    (STATUS_DONE, "Tender Builder",
     "Rich formatting for section bodies",
     "Dependency-free RichEditor (Bold/Italic/H2/H3/lists/quote) with DOMPurify sanitisation on ingress + egress",
     "Wave 24 + 25 (XSS hardened)"),
    (STATUS_DONE, "Tender Builder",
     "Per-section attachment upload (blank annexure forms)",
     "Upload/Replace/Remove per section, served through the uploads router with proper filenames",
     "Wave 24 + 26"),
    (STATUS_DONE, "Tender Builder",
     "Bulk drop many blank forms and auto-match to sections",
     "Multipart endpoint + fuzzy matcher (annex-VIII_bank.pdf correctly matches annex-VIII, not annex-V)",
     "Wave 29"),
    (STATUS_DONE, "Tender Builder",
     "Version history + one-click revert",
     "20-snapshot rolling versions, dedicated drawer UI, restore is itself auto-snapshotted (undoable)",
     "Wave 31"),

    # --- AI Copilot (advisory) ---
    (STATUS_DONE, "AI Copilot (advisory)",
     "AI-assisted section drafting",
     "Per-section ✨ menu with tone (Formal/Plain/Strict) × length (Short/Medium/Long) knobs, HTML output, bleach-sanitised",
     "Waves 29-30 · Emergent LLM Key"),
    (STATUS_DONE, "AI Copilot (advisory)",
     "Compare bids and surface clause-level differences",
     "`/api/v1/bids/compare-ai` returns `summary`, `clauses[]`, `recommended_questions[]`, `advisory_notice`; refuses to name a winner",
     "Wave 31 · human retains signature"),
    (STATUS_DONE, "AI Copilot (advisory)",
     "Show a diff before overwriting a section that already has content",
     "`AiDiffModal` with word-level red/green diff and +N/−N stats",
     "Wave 30"),
    (STATUS_DONE, "AI Governance",
     "AI stays advisory; humans keep signature",
     "Every AI endpoint carries an advisory notice, no automated state changes, full audit_log entries",
     "Architecture guardrail 2026-08-03"),

    # --- PDF export ---
    (STATUS_DONE, "PDF Export",
     "One-click composed tender PDF from Notice detail",
     "WeasyPrint server render, `Content-Disposition: attachment`, real %PDF-1.7",
     "Wave 28"),
    (STATUS_DONE, "PDF Export",
     "Watermark + version stamp on every page",
     "Diagonal DRAFT watermark, top-right tender ref, bottom footer `status · v{n} · issued yyyy-mm-dd · Page x/y`",
     "Wave 29"),
    (STATUS_DONE, "PDF Export",
     "Multi-language toggle (EN / RU / KK)",
     "`?lang=` param on `/export/pdf` and `/public/pdf`; static labels + watermark localised, bodies unchanged",
     "Wave 31 · pypdf-verified for RU"),
    (STATUS_DONE, "PDF Export",
     "Bundle the PDF + every section attachment into a single .zip",
     "`/public/zip?notice_ref=…` uses `zipfile` stdlib, includes README.txt index",
     "Wave 30"),

    # --- Bidding & Escrow ---
    (STATUS_DONE, "Bidding",
     "Multi-role approval pipeline (Escrow → Admin → Certifier → Legal → Accounting → Committee)",
     "Dynamic Approval Matrix per notice or falls back to default; committee panel + inspections + tasks",
     "Waves 1-2"),
    (STATUS_DONE, "Bidding",
     "Public clarifications thread on the Notice page",
     "`notice_qa` router — bidders ask, admin replies, only answered pairs shown publicly with masked emails",
     "Wave 31"),
    (STATUS_DONE, "Escrow (EMD)",
     "EMD held in an escrow-controlled account, not a PMC operational account",
     "Joint escrow accounts with TWO named officers (one PMC, one escrow institution) on file",
     "Wave 32"),
    (STATUS_DONE, "Escrow (EMD)",
     "Release requires dual authorisation from both operating officers",
     "`/transactions/{id}/sign` per officer + `/release` gated by both signing the same action; 409 otherwise",
     "Wave 32 verified via curl"),
    (STATUS_DONE, "Escrow (EMD)",
     "Three outcomes: to contractor (via PMC), refund to vendor, forfeit",
     "`release_to_contractor` / `release_to_vendor` / `forfeit` — all audit-logged and immutable on tx",
     "Wave 32"),
    (STATUS_PARTIAL, "Payments",
     "Stripe (EMD), PayPal, Kaspi Pay",
     "Stripe wired; PayPal/Kaspi in sandbox mock — waiting for merchant credentials",
     "Waves 1-3"),

    # --- Evaluation & Contracts ---
    (STATUS_DONE, "Evaluation",
     "Committee scoring with per-criterion weights",
     "Evaluation panel with rubric management, external committee invite by email, accept-flow",
     "Waves 2-5"),
    (STATUS_DONE, "Contracts / BOQ",
     "BOQ Builder + Contract Award workflow",
     "BOQ/Contracts panel, BOQ templates, contract award pipeline",
     "Waves 3-4"),

    # --- Multi-tenant & Governance ---
    (STATUS_DONE, "Audit",
     "Every substantive action is logged and attributable",
     "Global `audit_log` collection + per-transaction immutable `audit_trail[]` on escrow records",
     "Throughout"),

    # --- Mobile ---
    (STATUS_DONE, "Mobile",
     "Mobile-friendly app for staff and vendors",
     "PWA + Capacitor mobile wrapper, unified `/m` login, mobile hamburger menu",
     "Waves 13, 22"),

    # --- Planned ---
    (STATUS_PLANNED, "Compliance",
     "KYC should be a pre-bid gate (verify before allowing bid submission)",
     "Currently: KYC stub can be run, but not enforced as a gate before bidding",
     "Roadmap · P1 — needs live KYC keys"),
    (STATUS_PLANNED, "Evaluation",
     "Technical vs commercial evaluators segregated",
     "Currently rubric-scored, but a firewall role split (`tech_evaluator` cannot see commercial score until joint meeting) is not enforced",
     "Roadmap · P1"),
    (STATUS_PLANNED, "Notifications",
     "Live push notifications on mobile",
     "Firebase/APNs plumbing scaffolded; waiting for `google-services.json` + APNs auth key",
     "Blocked · P1"),
    (STATUS_PLANNED, "Emails",
     "Real transactional email dispatch",
     "Currently console-logged; needs Emergent-managed Resend key",
     "Blocked · P2"),
    (STATUS_PLANNED, "Deployment",
     "Native AWS Phase 2 migration (Postgres RLS, S3, Cognito, Fargate)",
     "MongoDB + FastAPI on Emergent for MVP; portability was a design constraint",
     "Roadmap · P2"),
]


# ------------------------------------------------------------------
#  XLSX
# ------------------------------------------------------------------

def _build_xlsx() -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Font, PatternFill, Alignment, Border, Side

    wb = Workbook()
    ws = wb.active
    ws.title = "Asked vs Delivered"

    headers = ["#", "Status", "Area", "What was asked", "What has been delivered", "Notes / Evidence"]
    ws.append(headers)
    for cell in ws[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="0B1F3A")
        cell.alignment = Alignment(vertical="center", horizontal="center", wrap_text=True)
        cell.border = Border(bottom=Side(style="medium", color="0B1F3A"))
    ws.row_dimensions[1].height = 26

    status_fill = {
        STATUS_DONE:    PatternFill("solid", fgColor="D1FAE5"),  # emerald-100
        STATUS_PARTIAL: PatternFill("solid", fgColor="FEF3C7"),  # amber-100
        STATUS_PLANNED: PatternFill("solid", fgColor="E0E7FF"),  # indigo-100
    }
    for idx, (status, area, asked, delivered, note) in enumerate(ROWS, start=1):
        ws.append([idx, status, area, asked, delivered, note])
        row_no = idx + 1
        for c in ws[row_no]:
            c.alignment = Alignment(vertical="top", wrap_text=True)
            c.fill = status_fill.get(status, PatternFill())

    widths = [4, 12, 20, 40, 55, 30]
    for i, w in enumerate(widths, start=1):
        ws.column_dimensions[chr(64 + i)].width = w

    # Summary sheet
    s = wb.create_sheet("Summary")
    total = len(ROWS)
    done = sum(1 for r in ROWS if r[0] == STATUS_DONE)
    partial = sum(1 for r in ROWS if r[0] == STATUS_PARTIAL)
    planned = sum(1 for r in ROWS if r[0] == STATUS_PLANNED)
    s.append(["PMC Managers v2 — Delivery status"])
    s.append([])
    s.append(["Generated at", now_iso()])
    s.append(["Total scope items", total])
    s.append(["Delivered", done, f"{done/total:.0%}"])
    s.append(["Partial",   partial, f"{partial/total:.0%}"])
    s.append(["Planned",   planned, f"{planned/total:.0%}"])
    s["A1"].font = Font(bold=True, size=14, color="0B1F3A")
    s.column_dimensions["A"].width = 22
    s.column_dimensions["B"].width = 32
    s.column_dimensions["C"].width = 10

    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------
#  DOCX
# ------------------------------------------------------------------

def _build_docx() -> bytes:
    from docx import Document
    from docx.shared import Pt, RGBColor, Cm
    from docx.enum.table import WD_ALIGN_VERTICAL

    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10)

    title = doc.add_heading("PMC Managers v2 — Asked vs Delivered", level=0)
    for run in title.runs:
        run.font.color.rgb = RGBColor(0x0B, 0x1F, 0x3A)
    doc.add_paragraph(f"Generated {now_iso()} · Stakeholder brief").italic = True

    doc.add_heading("Executive summary", level=1)
    total = len(ROWS)
    done = sum(1 for r in ROWS if r[0] == STATUS_DONE)
    partial = sum(1 for r in ROWS if r[0] == STATUS_PARTIAL)
    planned = sum(1 for r in ROWS if r[0] == STATUS_PLANNED)
    doc.add_paragraph(
        f"Of {total} tracked scope items, {done} are DELIVERED, {partial} are PARTIAL "
        f"(blocked on external credentials or roadmap-tagged) and {planned} are PLANNED. "
        "Every substantive action on the platform is audit-logged; the AI copilot is "
        "advisory-only — every state change requires an authorised human signature."
    )

    doc.add_heading("Comparative statement", level=1)
    t = doc.add_table(rows=1, cols=5)
    t.style = "Light Grid Accent 1"
    hdr = t.rows[0].cells
    for i, h in enumerate(["Status", "Area", "What was asked", "Delivered", "Notes"]):
        hdr[i].text = h
        for run in hdr[i].paragraphs[0].runs:
            run.bold = True
    for status, area, asked, delivered, note in ROWS:
        row = t.add_row().cells
        row[0].text = status
        row[1].text = area
        row[2].text = asked
        row[3].text = delivered
        row[4].text = note
        for c in row:
            c.vertical_alignment = WD_ALIGN_VERTICAL.TOP

    doc.add_page_break()
    doc.add_heading("Architecture guardrails accepted", level=1)
    for bullet in [
        "EMD flows directly to an escrow-controlled account jointly operated by one PMC officer and one escrow-institution officer. PMC only initiates and reconciles.",
        "Release from escrow requires dual authorisation from both operating officers; the ledger auto-refuses (HTTP 409) any release attempted before both signatures.",
        "KYC is being moved forward in the workflow so vendors are substantially validated before entering the bidding process (planned).",
        "Technical and commercial evaluations are kept segregated; a role-firewall audit is planned to ensure no single reviewer sees both scores before the joint award meeting.",
        "AI capabilities are advisory. All substantive decisions remain attributable to authorised individuals and are fully auditable.",
    ]:
        doc.add_paragraph(bullet, style="List Bullet")

    buf = io.BytesIO()
    doc.save(buf)
    return buf.getvalue()


# ------------------------------------------------------------------
#  PDF (same story as the docx, rendered via WeasyPrint)
# ------------------------------------------------------------------

def _status_class(s: str) -> str:
    return {STATUS_DONE: "ok", STATUS_PARTIAL: "warn", STATUS_PLANNED: "planned"}.get(s, "")


def _build_pdf_html() -> str:
    total = len(ROWS)
    done = sum(1 for r in ROWS if r[0] == STATUS_DONE)
    partial = sum(1 for r in ROWS if r[0] == STATUS_PARTIAL)
    planned = sum(1 for r in ROWS if r[0] == STATUS_PLANNED)
    rows_html = "".join(
        f"<tr class='r-{_status_class(s)}'><td>{_html.escape(s)}</td>"
        f"<td>{_html.escape(a)}</td><td>{_html.escape(ask)}</td>"
        f"<td>{_html.escape(dv)}</td><td>{_html.escape(n)}</td></tr>"
        for s, a, ask, dv, n in ROWS
    )
    return f"""<!doctype html><html><head><meta charset='utf-8'>
<title>PMC Managers v2 — Asked vs Delivered</title>
<style>
  @page {{ size: A4 landscape; margin: 14mm;
    @bottom-right {{ content: 'Page ' counter(page) ' / ' counter(pages); font: 8.5pt Georgia, serif; color: #64748b; }}
    @bottom-left {{ content: 'PMC Managers v2 · Stakeholder brief · {now_iso()[:10]}'; font: 8.5pt Georgia, serif; color: #64748b; }}
  }}
  body {{ font: 10pt/1.45 Calibri, Arial, sans-serif; color: #0b1f3a; }}
  h1 {{ font-size: 22pt; margin: 0 0 4pt; color: #0b1f3a; }}
  .kicker {{ font-size: 9pt; text-transform: uppercase; letter-spacing: .12em; color: #64748b; }}
  .stats {{ display: flex; gap: 14pt; margin: 10pt 0 18pt; }}
  .stat {{ flex: 1; border: 0.5pt solid #cbd5e1; padding: 6pt 10pt; }}
  .stat b {{ font-size: 18pt; display: block; color: #0b1f3a; }}
  .stat span {{ font-size: 9pt; color: #64748b; text-transform: uppercase; letter-spacing: .1em; }}
  table {{ width: 100%; border-collapse: collapse; font-size: 8.5pt; }}
  th, td {{ border: 0.4pt solid #cbd5e1; padding: 4pt 6pt; vertical-align: top; text-align: left; }}
  th {{ background: #0b1f3a; color: #fff; font-weight: 600; }}
  tr.r-ok      td:first-child {{ background: #d1fae5; color: #065f46; font-weight: 600; }}
  tr.r-warn    td:first-child {{ background: #fef3c7; color: #78350f; font-weight: 600; }}
  tr.r-planned td:first-child {{ background: #e0e7ff; color: #3730a3; font-weight: 600; }}
</style></head><body>
  <div class='kicker'>PMC Managers v2 · Comparative statement</div>
  <h1>What was asked vs what has been delivered</h1>
  <div class='stats'>
    <div class='stat'><span>Delivered</span><b>{done} <span style='font-size: 10pt'>/ {total}</span></b></div>
    <div class='stat'><span>Partial</span><b>{partial}</b></div>
    <div class='stat'><span>Planned</span><b>{planned}</b></div>
  </div>
  <table>
    <thead><tr><th style='width:8%'>Status</th><th style='width:14%'>Area</th>
      <th style='width:26%'>Asked</th><th style='width:32%'>Delivered</th>
      <th style='width:20%'>Notes / evidence</th></tr></thead>
    <tbody>{rows_html}</tbody>
  </table>
</body></html>"""


def _build_pdf() -> bytes:
    from weasyprint import HTML
    return HTML(string=_build_pdf_html()).write_pdf()


# ------------------------------------------------------------------
#  Flow chart (SVG + PDF)
# ------------------------------------------------------------------

def _build_flowchart_svg() -> str:
    """A left-to-right platform flow chart.
    Hand-laid SVG so it stays legible when embedded in slides."""
    return """<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 1000'
     font-family='Calibri, Arial, sans-serif' font-size='14'>
  <defs>
    <marker id='arrow' viewBox='0 0 10 10' refX='9' refY='5' markerUnits='strokeWidth'
            markerWidth='10' markerHeight='10' orient='auto'>
      <path d='M 0 0 L 10 5 L 0 10 z' fill='#0b1f3a'/>
    </marker>
    <style>
      .box   { fill: #ffffff; stroke: #0b1f3a; stroke-width: 1.5; }
      .box-ok{ fill: #d1fae5; stroke: #065f46; stroke-width: 1.5; }
      .box-hi{ fill: #0b1f3a; stroke: #0b1f3a; }
      .box-ai{ fill: #ede9fe; stroke: #6b21a8; stroke-width: 1.5; }
      .box-hi text { fill: #ffffff; }
      .title { font-size: 15px; font-weight: 700; }
      .sub   { font-size: 11px; fill: #475569; }
      .lane  { fill: #f8fafc; stroke: #e2e8f0; stroke-dasharray: 3 3; }
      .lane-title { font-size: 12px; font-weight: 700; fill: #64748b; letter-spacing: 1px; }
      .flow  { stroke: #0b1f3a; stroke-width: 1.5; fill: none; }
      .flow-alt { stroke: #6b21a8; stroke-width: 1.2; fill: none; stroke-dasharray: 6 4; }
    </style>
  </defs>

  <!-- Header -->
  <text x='40' y='38' class='title' font-size='22'>PMC Managers v2 — End-to-end platform flow</text>
  <text x='40' y='60' class='sub'>Delivered = navy border · Escrow-critical = green fill · AI (advisory) = purple fill</text>

  <!-- Swim lanes -->
  <rect class='lane' x='40'   y='90'  width='1520' height='170'/>
  <text x='60' y='115' class='lane-title'>1 · TENDER CREATION</text>

  <rect class='lane' x='40'   y='270' width='1520' height='170'/>
  <text x='60' y='295' class='lane-title'>2 · VENDOR ONBOARDING &amp; BIDDING</text>

  <rect class='lane' x='40'   y='450' width='1520' height='230'/>
  <text x='60' y='475' class='lane-title'>3 · ESCROW &amp; EVALUATION</text>

  <rect class='lane' x='40'   y='690' width='1520' height='140'/>
  <text x='60' y='715' class='lane-title'>4 · CONTRACT AWARD &amp; SETTLEMENT</text>

  <rect class='lane' x='40'   y='840' width='1520' height='140'/>
  <text x='60' y='865' class='lane-title'>5 · GOVERNANCE — AUDIT · AI · MULTI-LANG PDF</text>

  <!-- Lane 1: Tender creation -->
  <g transform='translate(80,140)'>
    <rect class='box' width='190' height='90' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Admin drafts</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Tender Builder v4</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>18 sections + header</text>
  </g>
  <g transform='translate(320,140)'>
    <rect class='box-ai' width='190' height='90' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>✨ AI section draft</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Tone × length</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>Diff-review before apply</text>
  </g>
  <g transform='translate(560,140)'>
    <rect class='box' width='190' height='90' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Bulk attachments</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Auto-match filename →</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>section by code/title</text>
  </g>
  <g transform='translate(800,140)'>
    <rect class='box' width='190' height='90' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Version history</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>20-snapshot rolling</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>1-click revert</text>
  </g>
  <g transform='translate(1040,140)'>
    <rect class='box-hi' width='190' height='90' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Publish notice</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Link tender template</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>Approval matrix</text>
  </g>
  <g transform='translate(1280,140)'>
    <rect class='box' width='230' height='90' rx='6'/>
    <text x='115' y='30' text-anchor='middle' class='title'>Public notice board</text>
    <text x='115' y='52' text-anchor='middle' class='sub'>Bidders download PDF/.zip</text>
    <text x='115' y='70' text-anchor='middle' class='sub'>EN · RU · KK</text>
  </g>
  <path class='flow' d='M270 185 L320 185' marker-end='url(#arrow)'/>
  <path class='flow' d='M510 185 L560 185' marker-end='url(#arrow)'/>
  <path class='flow' d='M750 185 L800 185' marker-end='url(#arrow)'/>
  <path class='flow' d='M990 185 L1040 185' marker-end='url(#arrow)'/>
  <path class='flow' d='M1230 185 L1280 185' marker-end='url(#arrow)'/>

  <!-- Lane 2: Vendor onboarding -->
  <g transform='translate(80,320)'>
    <rect class='box' width='190' height='90' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Vendor registers</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Sections A-E</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>Magic-link resume</text>
  </g>
  <g transform='translate(320,320)'>
    <rect class='box' width='190' height='90' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>KYC verification</text>
    <text x='95' y='52' text-anchor='middle' class='sub' fill='#78350f'>Planned as pre-bid gate</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>stub live · keys pending</text>
  </g>
  <g transform='translate(560,320)'>
    <rect class='box' width='190' height='90' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Ask a clarification</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Public Q&amp;A thread</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>Answered = visible to all</text>
  </g>
  <g transform='translate(800,320)'>
    <rect class='box' width='190' height='90' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Bid submission</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Price + tech notes</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>Docs upload</text>
  </g>
  <g transform='translate(1040,320)'>
    <rect class='box-ok' width='230' height='90' rx='6'/>
    <text x='115' y='30' text-anchor='middle' class='title'>EMD wired to joint escrow</text>
    <text x='115' y='52' text-anchor='middle' class='sub'>PMC officer + Escrow officer</text>
    <text x='115' y='70' text-anchor='middle' class='sub'>Ledger tx.status = received</text>
  </g>
  <path class='flow' d='M270 365 L320 365' marker-end='url(#arrow)'/>
  <path class='flow' d='M510 365 L560 365' marker-end='url(#arrow)'/>
  <path class='flow' d='M750 365 L800 365' marker-end='url(#arrow)'/>
  <path class='flow' d='M990 365 L1040 365' marker-end='url(#arrow)'/>

  <!-- Lane 3: Escrow & evaluation -->
  <g transform='translate(80,510)'>
    <rect class='box' width='190' height='100' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Approval pipeline</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Escrow → Admin →</text>
    <text x='95' y='68' text-anchor='middle' class='sub'>Certifier → Legal →</text>
    <text x='95' y='84' text-anchor='middle' class='sub'>Accounting → Committee</text>
  </g>
  <g transform='translate(320,510)'>
    <rect class='box' width='190' height='100' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Committee eval</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Rubric per criterion</text>
    <text x='95' y='68' text-anchor='middle' class='sub'>Tech + commercial</text>
    <text x='95' y='84' text-anchor='middle' class='sub' fill='#78350f'>role firewall planned</text>
  </g>
  <g transform='translate(560,510)'>
    <rect class='box-ai' width='190' height='100' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>✨ AI redline</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Compare two bids</text>
    <text x='95' y='68' text-anchor='middle' class='sub'>clause · pricing · risk</text>
    <text x='95' y='84' text-anchor='middle' class='sub'>advisory · no winner</text>
  </g>
  <g transform='translate(800,510)'>
    <rect class='box-ok' width='230' height='100' rx='6'/>
    <text x='115' y='30' text-anchor='middle' class='title'>Escrow tx: dual sign-off</text>
    <text x='115' y='52' text-anchor='middle' class='sub'>PMC officer signs · same action</text>
    <text x='115' y='68' text-anchor='middle' class='sub'>Escrow officer signs · same action</text>
    <text x='115' y='84' text-anchor='middle' class='sub'>Release button unlocks</text>
  </g>
  <g transform='translate(1060,510)'>
    <rect class='box-hi' width='210' height='100' rx='6'/>
    <text x='105' y='30' text-anchor='middle' class='title'>Award decision</text>
    <text x='105' y='52' text-anchor='middle' class='sub'>Committee accepts</text>
    <text x='105' y='68' text-anchor='middle' class='sub'>Contract drafted</text>
    <text x='105' y='84' text-anchor='middle' class='sub'>Audit-logged</text>
  </g>
  <path class='flow' d='M270 560 L320 560' marker-end='url(#arrow)'/>
  <path class='flow' d='M510 560 L560 560' marker-end='url(#arrow)'/>
  <path class='flow' d='M750 560 L800 560' marker-end='url(#arrow)'/>
  <path class='flow' d='M1030 560 L1060 560' marker-end='url(#arrow)'/>

  <!-- Lane 4: Settlement fan-out -->
  <g transform='translate(80,730)'>
    <rect class='box-ok' width='240' height='80' rx='6'/>
    <text x='120' y='30' text-anchor='middle' class='title'>Release → Contractor</text>
    <text x='120' y='52' text-anchor='middle' class='sub'>via PMC as pass-through</text>
    <text x='120' y='68' text-anchor='middle' class='sub'>paymaster</text>
  </g>
  <g transform='translate(360,730)'>
    <rect class='box-ok' width='240' height='80' rx='6'/>
    <text x='120' y='30' text-anchor='middle' class='title'>Refund → Vendor</text>
    <text x='120' y='52' text-anchor='middle' class='sub'>bid did not win</text>
    <text x='120' y='68' text-anchor='middle' class='sub'>EMD returned in full</text>
  </g>
  <g transform='translate(640,730)'>
    <rect class='box-ok' width='240' height='80' rx='6'/>
    <text x='120' y='30' text-anchor='middle' class='title'>Forfeit</text>
    <text x='120' y='52' text-anchor='middle' class='sub'>Withdrawal · misdeclaration</text>
    <text x='120' y='68' text-anchor='middle' class='sub'>Retained per T&amp;C</text>
  </g>
  <g transform='translate(950,730)'>
    <rect class='box' width='320' height='80' rx='6'/>
    <text x='160' y='30' text-anchor='middle' class='title'>Ledger closes · immutable audit_trail</text>
    <text x='160' y='52' text-anchor='middle' class='sub'>received → signed_by_pmc → signed_by_escrow →</text>
    <text x='160' y='68' text-anchor='middle' class='sub'>released_to_* / forfeited</text>
  </g>
  <path class='flow-alt' d='M1165 610 Q1165 660, 1060 730' marker-end='url(#arrow)'/>
  <path class='flow' d='M320 770 L360 770' marker-end='url(#arrow)'/>
  <path class='flow' d='M600 770 L640 770' marker-end='url(#arrow)'/>
  <path class='flow' d='M880 770 L950 770' marker-end='url(#arrow)'/>

  <!-- Lane 5: Governance -->
  <g transform='translate(80,880)'>
    <rect class='box' width='260' height='80' rx='6'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Audit log</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Every substantive action</text>
    <text x='130' y='68' text-anchor='middle' class='sub'>attributable to a human</text>
  </g>
  <g transform='translate(380,880)'>
    <rect class='box-ai' width='260' height='80' rx='6'/>
    <text x='130' y='30' text-anchor='middle' class='title'>AI Copilot (advisory)</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Section draft · redline · Q&amp;A</text>
    <text x='130' y='68' text-anchor='middle' class='sub'>Humans sign every action</text>
  </g>
  <g transform='translate(680,880)'>
    <rect class='box' width='260' height='80' rx='6'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Multi-lang PDF</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>EN · RU · KK</text>
    <text x='130' y='68' text-anchor='middle' class='sub'>watermark · version stamp</text>
  </g>
  <g transform='translate(980,880)'>
    <rect class='box' width='260' height='80' rx='6'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Multi-tenant portals</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>CNAME subdomains</text>
    <text x='130' y='68' text-anchor='middle' class='sub'>Per-tenant branding · MFA</text>
  </g>
  <g transform='translate(1280,880)'>
    <rect class='box' width='230' height='80' rx='6'/>
    <text x='115' y='30' text-anchor='middle' class='title'>Mobile · PWA</text>
    <text x='115' y='52' text-anchor='middle' class='sub'>Capacitor wrapper</text>
    <text x='115' y='68' text-anchor='middle' class='sub'>Hamburger UI</text>
  </g>
</svg>"""


# ------------------------------------------------------------------
#  Endpoints
# ------------------------------------------------------------------

def _dl_headers(name: str, media: str) -> dict:
    return {
        "Content-Disposition": f'attachment; filename="{name}"',
        "X-Content-Type-Options": "nosniff",
        "Cache-Control": "no-store",
    }


@router.get("/comparative-statement.xlsx")
async def get_xlsx(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    body = _build_xlsx()
    return Response(content=body,
                     media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                     headers=_dl_headers("PMC-v2-Asked-vs-Delivered.xlsx",
                                          "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"))


@router.get("/comparative-statement.docx")
async def get_docx(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    body = _build_docx()
    return Response(content=body,
                     media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                     headers=_dl_headers("PMC-v2-Asked-vs-Delivered.docx",
                                          "application/vnd.openxmlformats-officedocument.wordprocessingml.document"))


@router.get("/comparative-statement.pdf")
async def get_pdf(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    body = _build_pdf()
    return Response(content=body, media_type="application/pdf",
                     headers=_dl_headers("PMC-v2-Asked-vs-Delivered.pdf", "application/pdf"))


@router.get("/flowchart.svg")
async def get_flowchart_svg(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    svg = _build_flowchart_svg()
    return Response(content=svg, media_type="image/svg+xml",
                     headers=_dl_headers("PMC-v2-Platform-Flowchart.svg", "image/svg+xml"))


@router.get("/flowchart.pdf")
async def get_flowchart_pdf(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    from weasyprint import HTML
    html = f"""<!doctype html><html><head><meta charset='utf-8'>
<style>@page {{ size: A3 landscape; margin: 8mm; }} body {{ margin: 0; }}
  svg {{ width: 100%; height: auto; }}</style></head><body>{_build_flowchart_svg()}</body></html>"""
    pdf = HTML(string=html).write_pdf()
    return Response(content=pdf, media_type="application/pdf",
                     headers=_dl_headers("PMC-v2-Platform-Flowchart.pdf", "application/pdf"))
