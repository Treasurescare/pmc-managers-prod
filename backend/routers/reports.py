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
    (STATUS_DONE, "Compliance",
     "KYC as a pre-bid gate — verify before allowing bid submission",
     "`bids.create_bid()` returns HTTP 412 unless vendor has a passing KYC decision; `kyc_bypass` override on notices",
     "Wave 35d"),
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
    (STATUS_DONE, "Escrow (EMD)",
     "Non-PMC escrow officer signs without a full staff account",
     "`POST /escrow/magic-tokens` admin-issued token → `/escrow/officer/:token` public portal signs the same transactions",
     "Wave 35b"),

    # --- Revenue streams (new) ---
    (STATUS_DONE, "Revenue Catalog",
     "Admin-editable master of every revenue line (client + supplier)",
     "55 products seeded from CA-02/CA-03; 9 pricing models; multi-currency; live CRUD via Admin → Product Catalog",
     "Wave 35 · `products.py`"),
    (STATUS_DONE, "Revenue Catalog",
     "Client purchase surface — packages + services",
     "Public `/services` with 34 products, 5 category filters, quote-vs-subscribe CTAs driven by pricing_model",
     "Wave 36 · `ClientPurchase`"),
    (STATUS_DONE, "Revenue Catalog",
     "Quote pipeline — Request quote → engagement → admin quote → invoice → paid",
     "New `engagements.py` router + `EngagementsPanel.jsx` admin UI. Quote requests from purchase pages land in a persistent pipeline; admin sets amount, generates Stripe pay-link in one click; end-to-end tested $40k USD.",
     "Wave 38"),
    (STATUS_DONE, "Revenue Catalog",
     "Supplier purchase surface — Supplier Success + tender-stage + add-ons",
     "Public `/vendor/services` with 21 products, GBP pricing, SME/Mid/Tier-1 subscription tiers",
     "Wave 37 · `VendorPurchase`"),
    (STATUS_DONE, "Payments",
     "Stripe Checkout for one-off + subscription products from the catalog",
     "`POST /api/v1/billing/checkout` (admin, vendor OR anon) creates `cs_test_...` session with server-authoritative amount; `/api/webhook/stripe` idempotent",
     "Wave 35 · `emergentintegrations`"),
    (STATUS_PARTIAL, "Payments",
     "PayPal, Kaspi Pay",
     "In sandbox mock — waiting for merchant credentials",
     "P2 · blocked"),

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
    (STATUS_DONE, "Governance",
     "Live public roadmap page so vendors can see what's built vs coming",
     "Public `/roadmap` reads `/api/v1/reports/public/roadmap` — 20 areas, status pills, stat-card filters",
     "Wave 35c"),
    (STATUS_DONE, "Governance",
     "Stakeholder reports auto-regenerate on every deploy",
     "`_refresh_reports_snapshot()` runs at startup — `/app/docs/reports/*.{xlsx,docx,pdf,svg}` never drifts",
     "Wave 35e"),

    # --- Mobile ---
    (STATUS_DONE, "Mobile",
     "Mobile-friendly app for staff and vendors",
     "PWA + Capacitor mobile wrapper, unified `/m` login, mobile hamburger menu",
     "Waves 13, 22"),

    # --- Planned ---
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
    (STATUS_PLANNED, "Compliance",
     "Live KYC provider integration",
     "Stubbed logic in place + pre-bid gate wired; awaiting `KYC_BASE_URL` and `KYC_API_KEY`",
     "Blocked · P1"),
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
    """Wave-35 refresh — left-to-right platform flow chart including the new
    Revenue lane (Product Catalog · Client & Supplier services · Stripe) and
    the Escrow magic-link portal. Hand-laid SVG so it stays legible in slides."""
    return """<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1720 1280'
     font-family='Calibri, Arial, sans-serif' font-size='14'>
  <defs>
    <marker id='arrow' viewBox='0 0 10 10' refX='9' refY='5' markerUnits='strokeWidth'
            markerWidth='10' markerHeight='10' orient='auto'>
      <path d='M 0 0 L 10 5 L 0 10 z' fill='#0b1f3a'/>
    </marker>
    <marker id='arrow-rev' viewBox='0 0 10 10' refX='9' refY='5' markerUnits='strokeWidth'
            markerWidth='10' markerHeight='10' orient='auto'>
      <path d='M 0 0 L 10 5 L 0 10 z' fill='#065f46'/>
    </marker>
    <style>
      .box     { fill: #ffffff; stroke: #0b1f3a; stroke-width: 1.5; }
      .box-ok  { fill: #d1fae5; stroke: #065f46; stroke-width: 1.5; }
      .box-hi  { fill: #0b1f3a; stroke: #0b1f3a; }
      .box-ai  { fill: #ede9fe; stroke: #6b21a8; stroke-width: 1.5; }
      .box-rev { fill: #fef3c7; stroke: #92400e; stroke-width: 1.5; }
      .box-hi text { fill: #ffffff; }
      .title   { font-size: 15px; font-weight: 700; }
      .sub     { font-size: 11px; fill: #475569; }
      .lane    { fill: #f8fafc; stroke: #e2e8f0; stroke-dasharray: 3 3; }
      .lane-title { font-size: 12px; font-weight: 700; fill: #64748b; letter-spacing: 1px; }
      .flow    { stroke: #0b1f3a; stroke-width: 1.5; fill: none; }
      .flow-rev{ stroke: #92400e; stroke-width: 1.4; fill: none; stroke-dasharray: 4 3; }
      .flow-alt{ stroke: #6b21a8; stroke-width: 1.2; fill: none; stroke-dasharray: 6 4; }
      .legend text { font-size: 11px; fill: #334155; }
    </style>
  </defs>

  <!-- Header -->
  <text x='40' y='38' class='title' font-size='22'>PMC Managers v2 — End-to-end platform flow (rev. 2026-08-05 · Wave 38)</text>
  <text x='40' y='60' class='sub'>Six operating lanes · Revenue lane now includes the live Quote → Invoice pipeline · Escrow lane retains dual-officer magic-link</text>

  <!-- Legend -->
  <g class='legend' transform='translate(40, 76)'>
    <rect x='0'   y='0' width='16' height='12' class='box'/>       <text x='22' y='10'>Standard step</text>
    <rect x='140' y='0' width='16' height='12' class='box-ok'/>    <text x='162' y='10'>Escrow-critical (green)</text>
    <rect x='320' y='0' width='16' height='12' class='box-hi'/>    <text x='342' y='10'>Publish / award decision</text>
    <rect x='500' y='0' width='16' height='12' class='box-ai'/>    <text x='522' y='10'>AI (advisory only)</text>
    <rect x='680' y='0' width='16' height='12' class='box-rev'/>   <text x='702' y='10'>Revenue (Stripe / catalog)</text>
  </g>

  <!-- Swim lanes -->
  <rect class='lane' x='40'   y='108' width='1640' height='160'/>
  <text x='60' y='128' class='lane-title'>1 · TENDER CREATION</text>

  <rect class='lane' x='40'   y='278' width='1640' height='200'/>
  <text x='60' y='298' class='lane-title'>2 · VENDOR ONBOARDING · KYC GATE · BIDDING</text>

  <rect class='lane' x='40'   y='488' width='1640' height='260'/>
  <text x='60' y='508' class='lane-title'>3 · JOINT ESCROW (dual-signature + magic-link)</text>

  <rect class='lane' x='40'   y='758' width='1640' height='150'/>
  <text x='60' y='778' class='lane-title'>4 · CONTRACT AWARD &amp; SETTLEMENT</text>

  <rect class='lane' x='40'   y='918' width='1640' height='200'/>
  <text x='60' y='938' class='lane-title'>5 · REVENUE STREAMS — CATALOG · CLIENT + SUPPLIER · STRIPE</text>

  <rect class='lane' x='40'   y='1128' width='1640' height='130'/>
  <text x='60' y='1148' class='lane-title'>6 · GOVERNANCE — AUDIT · AI · LIVE ROADMAP · AUTO-SNAPSHOT · MULTI-TENANT</text>

  <!-- ============ Lane 1: Tender creation ============ -->
  <g transform='translate(80,150)'>
    <rect class='box' width='190' height='95' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Admin drafts</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Tender Builder v4</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>18 sections + header</text>
  </g>
  <g transform='translate(320,150)'>
    <rect class='box-ai' width='190' height='95' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>✨ AI section draft</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Tone × length</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>Diff-review before apply</text>
  </g>
  <g transform='translate(560,150)'>
    <rect class='box' width='190' height='95' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Bulk attachments</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Auto-match filename →</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>section by code/title</text>
  </g>
  <g transform='translate(800,150)'>
    <rect class='box' width='190' height='95' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Version history</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>20-snapshot rolling</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>1-click revert</text>
  </g>
  <g transform='translate(1040,150)'>
    <rect class='box-hi' width='190' height='95' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Publish notice</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Link tender template</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>Approval matrix</text>
  </g>
  <g transform='translate(1280,150)'>
    <rect class='box' width='260' height='95' rx='6'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Public notice board</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>Bidders download PDF/.zip</text>
    <text x='130' y='70' text-anchor='middle' class='sub'>EN · RU · KK · magic-byte checked</text>
  </g>
  <path class='flow' d='M270 197 L320 197' marker-end='url(#arrow)'/>
  <path class='flow' d='M510 197 L560 197' marker-end='url(#arrow)'/>
  <path class='flow' d='M750 197 L800 197' marker-end='url(#arrow)'/>
  <path class='flow' d='M990 197 L1040 197' marker-end='url(#arrow)'/>
  <path class='flow' d='M1230 197 L1280 197' marker-end='url(#arrow)'/>

  <!-- ============ Lane 2: Vendor onboarding & bidding ============ -->
  <g transform='translate(80,320)'>
    <rect class='box' width='190' height='100' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Vendor registers</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Sections A-E</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>Magic-link resume</text>
    <text x='95' y='88' text-anchor='middle' class='sub'>Registration = free</text>
  </g>
  <g transform='translate(320,320)'>
    <rect class='box-ok' width='190' height='100' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>🔒 KYC verification</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Pre-bid gate ACTIVE</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>HTTP 412 if not passed</text>
    <text x='95' y='88' text-anchor='middle' class='sub'>kyc_bypass admin escape</text>
  </g>
  <g transform='translate(560,320)'>
    <rect class='box' width='190' height='100' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Ask a clarification</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Public Q&amp;A thread</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>Email masked · admin reply</text>
  </g>
  <g transform='translate(800,320)'>
    <rect class='box' width='190' height='100' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Bid submission</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Price + tech notes</text>
    <text x='95' y='70' text-anchor='middle' class='sub'>Docs upload</text>
  </g>
  <g transform='translate(1040,320)'>
    <rect class='box-ok' width='250' height='100' rx='6'/>
    <text x='125' y='30' text-anchor='middle' class='title'>EMD wired to joint escrow</text>
    <text x='125' y='52' text-anchor='middle' class='sub'>PMC officer + Escrow officer</text>
    <text x='125' y='70' text-anchor='middle' class='sub'>Stripe / PayPal / Kaspi rail</text>
    <text x='125' y='88' text-anchor='middle' class='sub'>tx.status = received</text>
  </g>
  <path class='flow' d='M270 370 L320 370' marker-end='url(#arrow)'/>
  <path class='flow' d='M510 370 L560 370' marker-end='url(#arrow)'/>
  <path class='flow' d='M750 370 L800 370' marker-end='url(#arrow)'/>
  <path class='flow' d='M990 370 L1040 370' marker-end='url(#arrow)'/>

  <!-- ============ Lane 3: Joint Escrow (expanded) ============ -->
  <g transform='translate(80,540)'>
    <rect class='box' width='190' height='110' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Approval pipeline</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Escrow → Admin →</text>
    <text x='95' y='68' text-anchor='middle' class='sub'>Certifier → Legal →</text>
    <text x='95' y='84' text-anchor='middle' class='sub'>Accounting → Committee</text>
  </g>
  <g transform='translate(320,540)'>
    <rect class='box' width='190' height='110' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>Committee eval</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Rubric per criterion</text>
    <text x='95' y='68' text-anchor='middle' class='sub'>Tech + commercial</text>
    <text x='95' y='88' text-anchor='middle' class='sub' fill='#78350f'>role firewall planned</text>
  </g>
  <g transform='translate(560,540)'>
    <rect class='box-ai' width='190' height='110' rx='6'/>
    <text x='95' y='30' text-anchor='middle' class='title'>✨ AI redline</text>
    <text x='95' y='52' text-anchor='middle' class='sub'>Compare two bids</text>
    <text x='95' y='68' text-anchor='middle' class='sub'>clause · pricing · risk</text>
    <text x='95' y='88' text-anchor='middle' class='sub'>advisory · no winner</text>
  </g>
  <g transform='translate(800,540)'>
    <rect class='box-ok' width='260' height='110' rx='6'/>
    <text x='130' y='30' text-anchor='middle' class='title'>Escrow tx: dual sign-off</text>
    <text x='130' y='52' text-anchor='middle' class='sub'>PMC officer signs · same action</text>
    <text x='130' y='68' text-anchor='middle' class='sub'>Escrow officer signs · same action</text>
    <text x='130' y='88' text-anchor='middle' class='sub'>Release button unlocks (409 otherwise)</text>
  </g>
  <g transform='translate(1090,540)'>
    <rect class='box-ok' width='250' height='110' rx='6'/>
    <text x='125' y='30' text-anchor='middle' class='title'>🔗 Magic-link portal</text>
    <text x='125' y='52' text-anchor='middle' class='sub'>Non-PMC officer signs via</text>
    <text x='125' y='68' text-anchor='middle' class='sub'>/escrow/officer/{token}</text>
    <text x='125' y='88' text-anchor='middle' class='sub'>no full staff account needed</text>
  </g>
  <g transform='translate(1370,540)'>
    <rect class='box-hi' width='230' height='110' rx='6'/>
    <text x='115' y='30' text-anchor='middle' class='title'>Award decision</text>
    <text x='115' y='52' text-anchor='middle' class='sub'>Committee accepts</text>
    <text x='115' y='68' text-anchor='middle' class='sub'>Contract drafted</text>
    <text x='115' y='88' text-anchor='middle' class='sub'>Audit-logged</text>
  </g>
  <path class='flow' d='M270 595 L320 595' marker-end='url(#arrow)'/>
  <path class='flow' d='M510 595 L560 595' marker-end='url(#arrow)'/>
  <path class='flow' d='M750 595 L800 595' marker-end='url(#arrow)'/>
  <path class='flow-alt' d='M1090 595 L1060 595' marker-end='url(#arrow)'/>
  <path class='flow' d='M1340 595 L1370 595' marker-end='url(#arrow)'/>

  <!-- ============ Lane 4: Settlement fan-out ============ -->
  <g transform='translate(80,800)'>
    <rect class='box-ok' width='240' height='80' rx='6'/>
    <text x='120' y='30' text-anchor='middle' class='title'>Release → Contractor</text>
    <text x='120' y='52' text-anchor='middle' class='sub'>via PMC as pass-through</text>
    <text x='120' y='68' text-anchor='middle' class='sub'>paymaster</text>
  </g>
  <g transform='translate(360,800)'>
    <rect class='box-ok' width='240' height='80' rx='6'/>
    <text x='120' y='30' text-anchor='middle' class='title'>Refund → Vendor</text>
    <text x='120' y='52' text-anchor='middle' class='sub'>bid did not win</text>
    <text x='120' y='68' text-anchor='middle' class='sub'>EMD returned in full</text>
  </g>
  <g transform='translate(640,800)'>
    <rect class='box-ok' width='240' height='80' rx='6'/>
    <text x='120' y='30' text-anchor='middle' class='title'>Forfeit</text>
    <text x='120' y='52' text-anchor='middle' class='sub'>Withdrawal · misdeclaration</text>
    <text x='120' y='68' text-anchor='middle' class='sub'>Retained per T&amp;C</text>
  </g>
  <g transform='translate(950,800)'>
    <rect class='box' width='400' height='80' rx='6'/>
    <text x='200' y='30' text-anchor='middle' class='title'>Ledger closes · immutable audit_trail</text>
    <text x='200' y='52' text-anchor='middle' class='sub'>received → signed_by_pmc → signed_by_escrow →</text>
    <text x='200' y='68' text-anchor='middle' class='sub'>released_to_* / forfeited</text>
  </g>
  <path class='flow-alt' d='M1495 650 Q1495 730, 1350 800' marker-end='url(#arrow)'/>
  <path class='flow' d='M320 840 L360 840' marker-end='url(#arrow)'/>
  <path class='flow' d='M600 840 L640 840' marker-end='url(#arrow)'/>
  <path class='flow' d='M880 840 L950 840' marker-end='url(#arrow)'/>

  <!-- ============ Lane 5: REVENUE STREAMS (new) ============ -->
  <g transform='translate(80,960)'>
    <rect class='box-rev' width='210' height='140' rx='6'/>
    <text x='105' y='30' text-anchor='middle' class='title'>Product Catalog</text>
    <text x='105' y='52' text-anchor='middle' class='sub'>Admin-editable master</text>
    <text x='105' y='68' text-anchor='middle' class='sub'>55 rows (CA-02 + CA-03)</text>
    <text x='105' y='86' text-anchor='middle' class='sub'>9 pricing models</text>
    <text x='105' y='104' text-anchor='middle' class='sub'>Multi-currency</text>
    <text x='105' y='122' text-anchor='middle' class='sub'>USD · GBP · EUR · KZT</text>
  </g>
  <g transform='translate(320,960)'>
    <rect class='box-rev' width='210' height='140' rx='6'/>
    <text x='105' y='30' text-anchor='middle' class='title'>Client purchase</text>
    <text x='105' y='52' text-anchor='middle' class='sub'>/services</text>
    <text x='105' y='68' text-anchor='middle' class='sub'>34 client products</text>
    <text x='105' y='86' text-anchor='middle' class='sub'>Bronze · Silver · Gold ·</text>
    <text x='105' y='104' text-anchor='middle' class='sub'>Platinum + 22 advisory</text>
    <text x='105' y='122' text-anchor='middle' class='sub'>quote-vs-subscribe CTAs</text>
  </g>
  <g transform='translate(560,960)'>
    <rect class='box-rev' width='210' height='140' rx='6'/>
    <text x='105' y='30' text-anchor='middle' class='title'>Supplier purchase</text>
    <text x='105' y='52' text-anchor='middle' class='sub'>/vendor/services</text>
    <text x='105' y='68' text-anchor='middle' class='sub'>21 supplier products</text>
    <text x='105' y='86' text-anchor='middle' class='sub'>SME · Mid · Tier-1</text>
    <text x='105' y='104' text-anchor='middle' class='sub'>+ 13 monthly add-ons</text>
    <text x='105' y='122' text-anchor='middle' class='sub'>+ project-setup fees</text>
  </g>
  <g transform='translate(800,960)'>
    <rect class='box-rev' width='210' height='140' rx='6'/>
    <text x='105' y='30' text-anchor='middle' class='title'>Stripe Checkout</text>
    <text x='105' y='52' text-anchor='middle' class='sub'>POST /billing/checkout</text>
    <text x='105' y='68' text-anchor='middle' class='sub'>admin · vendor · anon</text>
    <text x='105' y='86' text-anchor='middle' class='sub'>server-authoritative price</text>
    <text x='105' y='104' text-anchor='middle' class='sub'>one-off + subscription</text>
    <text x='105' y='122' text-anchor='middle' class='sub'>cs_test_... session</text>
  </g>
  <g transform='translate(1040,960)'>
    <rect class='box-rev' width='210' height='140' rx='6'/>
    <text x='105' y='30' text-anchor='middle' class='title'>Webhook · ledger</text>
    <text x='105' y='52' text-anchor='middle' class='sub'>/api/webhook/stripe</text>
    <text x='105' y='68' text-anchor='middle' class='sub'>idempotent on paid</text>
    <text x='105' y='86' text-anchor='middle' class='sub'>payment_transactions</text>
    <text x='105' y='104' text-anchor='middle' class='sub'>row updated</text>
  </g>
  <g transform='translate(1280,960)'>
    <rect class='box-rev' width='250' height='140' rx='6'/>
    <text x='125' y='30' text-anchor='middle' class='title'>Quote → Invoice pipeline</text>
    <text x='125' y='52' text-anchor='middle' class='sub'>Range / % / cost-recovery</text>
    <text x='125' y='68' text-anchor='middle' class='sub'>engagement · admin sets amt</text>
    <text x='125' y='86' text-anchor='middle' class='sub'>1-click Stripe pay-link</text>
    <text x='125' y='104' text-anchor='middle' class='sub'>audit trail per transition</text>
    <text x='125' y='122' text-anchor='middle' class='sub'>Wave 38 · engagements.py</text>
  </g>
  <path class='flow-rev' d='M290 1030 L320 1030' marker-end='url(#arrow-rev)'/>
  <path class='flow-rev' d='M530 1030 L560 1030' marker-end='url(#arrow-rev)'/>
  <path class='flow-rev' d='M770 1030 L800 1030' marker-end='url(#arrow-rev)'/>
  <path class='flow-rev' d='M1010 1030 L1040 1030' marker-end='url(#arrow-rev)'/>
  <path class='flow-rev' d='M1250 1030 L1280 1030' marker-end='url(#arrow-rev)'/>

  <!-- ============ Lane 6: Governance ============ -->
  <g transform='translate(80,1165)'>
    <rect class='box' width='230' height='75' rx='6'/>
    <text x='115' y='28' text-anchor='middle' class='title'>Audit log</text>
    <text x='115' y='50' text-anchor='middle' class='sub'>Every substantive action</text>
    <text x='115' y='66' text-anchor='middle' class='sub'>attributable to a human</text>
  </g>
  <g transform='translate(340,1165)'>
    <rect class='box-ai' width='230' height='75' rx='6'/>
    <text x='115' y='28' text-anchor='middle' class='title'>AI Copilot (advisory)</text>
    <text x='115' y='50' text-anchor='middle' class='sub'>Section draft · redline · Q&amp;A</text>
    <text x='115' y='66' text-anchor='middle' class='sub'>Humans sign every action</text>
  </g>
  <g transform='translate(600,1165)'>
    <rect class='box' width='230' height='75' rx='6'/>
    <text x='115' y='28' text-anchor='middle' class='title'>Live Roadmap /roadmap</text>
    <text x='115' y='50' text-anchor='middle' class='sub'>Public shareable URL</text>
    <text x='115' y='66' text-anchor='middle' class='sub'>Delivered · Partial · Planned</text>
  </g>
  <g transform='translate(860,1165)'>
    <rect class='box' width='230' height='75' rx='6'/>
    <text x='115' y='28' text-anchor='middle' class='title'>Auto-snapshot</text>
    <text x='115' y='50' text-anchor='middle' class='sub'>Startup regenerates 5 files</text>
    <text x='115' y='66' text-anchor='middle' class='sub'>docs/reports · git-tracked</text>
  </g>
  <g transform='translate(1120,1165)'>
    <rect class='box' width='230' height='75' rx='6'/>
    <text x='115' y='28' text-anchor='middle' class='title'>Multi-lang PDF</text>
    <text x='115' y='50' text-anchor='middle' class='sub'>EN · RU · KK</text>
    <text x='115' y='66' text-anchor='middle' class='sub'>watermark · version stamp</text>
  </g>
  <g transform='translate(1380,1165)'>
    <rect class='box' width='230' height='75' rx='6'/>
    <text x='115' y='28' text-anchor='middle' class='title'>Multi-tenant · Mobile</text>
    <text x='115' y='50' text-anchor='middle' class='sub'>CNAME subdomains</text>
    <text x='115' y='66' text-anchor='middle' class='sub'>Capacitor · MFA · i18n</text>
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


# ------------------------------------------------------------------
#  Public roadmap JSON — no auth. Powers the shareable /roadmap page.
# ------------------------------------------------------------------

@router.get("/public/roadmap")
async def public_roadmap():
    total = len(ROWS)
    stats = {STATUS_DONE: 0, STATUS_PARTIAL: 0, STATUS_PLANNED: 0}
    grouped: dict = {}
    for status, area, asked, delivered, note in ROWS:
        stats[status] = stats.get(status, 0) + 1
        grouped.setdefault(area, []).append({
            "status": status, "asked": asked,
            "delivered": delivered, "note": note,
        })
    return {
        "generated_at": now_iso(),
        "total_items": total,
        "delivered": stats[STATUS_DONE],
        "partial": stats[STATUS_PARTIAL],
        "planned": stats[STATUS_PLANNED],
        "areas": [{"area": a, "items": items} for a, items in grouped.items()],
    }


# ------------------------------------------------------------------
#  Snapshot to disk (git-tracked so files show up in the next push)
# ------------------------------------------------------------------
import os as _os
from pathlib import Path as _Path

SNAPSHOT_DIR = _Path(_os.environ.get("REPORTS_SNAPSHOT_DIR", "/app/docs/reports"))


def _flowchart_pdf_bytes() -> bytes:
    from weasyprint import HTML
    html = f"""<!doctype html><html><head><meta charset='utf-8'>
<style>@page {{ size: A3 landscape; margin: 8mm; }} body {{ margin: 0; }}
  svg {{ width: 100%; height: auto; }}</style></head><body>{_build_flowchart_svg()}</body></html>"""
    return HTML(string=html).write_pdf()


def snapshot_to_disk() -> dict:
    """Write all five artefacts into SNAPSHOT_DIR so Git can track them.

    Returns a small manifest the caller can render for the user.
    """
    SNAPSHOT_DIR.mkdir(parents=True, exist_ok=True)
    files = {
        "PMC-v2-Asked-vs-Delivered.xlsx": _build_xlsx(),
        "PMC-v2-Asked-vs-Delivered.docx": _build_docx(),
        "PMC-v2-Asked-vs-Delivered.pdf":  _build_pdf(),
        "PMC-v2-Platform-Flowchart.svg":  _build_flowchart_svg().encode("utf-8"),
        "PMC-v2-Platform-Flowchart.pdf":  _flowchart_pdf_bytes(),
    }
    manifest = []
    for name, body in files.items():
        p = SNAPSHOT_DIR / name
        p.write_bytes(body if isinstance(body, (bytes, bytearray)) else body.encode("utf-8"))
        manifest.append({"file": name, "bytes": p.stat().st_size,
                          "path": str(p.relative_to(_Path("/app")))})
    (SNAPSHOT_DIR / "GENERATED_AT.txt").write_text(
        f"Snapshot generated at {now_iso()}\n"
        f"Source: /api/v1/reports/snapshot (POST) — see backend/routers/reports.py\n"
    )
    return {"generated_at": now_iso(),
             "dir": str(SNAPSHOT_DIR.relative_to(_Path("/app"))),
             "files": manifest}


@router.post("/snapshot")
async def post_snapshot(admin=Depends(require_role("admin"))):
    """Persist the five artefacts into /app/docs/reports so they land in Git."""
    return snapshot_to_disk()
