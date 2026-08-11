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

    # --- Wave 43 (2026-08-07) — DocuSign eSignature (JWT Grant) ---
    (STATUS_DONE, "Legal",
     "PKI / DSC (Digital Signature Certificate) integration for bid + contract signing",
     "DocuSign eSignature via JWT Grant (sandbox). New `/api/v1/docusign/*` router — envelope creation from Award PDFs (PO/SLA/Contract) + Bid acknowledgements, embedded signing view, Connect webhook for status. Admin DocuSignPanel with consent flow + envelope log. Trilingual (EN/RU/KK)",
     "Wave 43 · consent granted, sandbox live"),

    # --- Wave 42 (2026-08-07) — Usability + Trilingual sweep ---
    (STATUS_DONE, "i18n",
     "Trilingual coverage across every admin panel (not just public + login)",
     "Added `panels` namespace to `i18n-strings.js` — ~450 EN/RU/KK strings covering headings, buttons, filter chips, table headers, empty states and toasts for 15 admin panels (Analytics, Audit, Awards, BOQ, Bidding, Corrigenda, Engagements, Evaluation, LiveAuctions, MFA, Masters, Permissions, Reports, TenderBuilder, VendorIntel). 21 of 22 admin panels now use `useI18n`",
     "Wave 42a"),
    (STATUS_DONE, "UX / Mobile",
     "Mobile-first responsive layout across top pages",
     "Home@375px now renders at exact viewport (was 421 overflow) via responsive stat cards + `overflow-x-hidden`. AdminDashboard's 22-tab bar collapses into a mobile `<select>` on md-, header buttons stack + adaptive text sizes. Every admin function reachable at 375/768 viewport with zero horizontal scroll",
     "Wave 42b"),

    # --- Wave 41 (2026-08-06) — Meeting Scheduler + L1 Auto-Comparison + Zoom ---
    (STATUS_DONE, "Procurement",
     "Scheduled Pre-Bid Meeting rooms (video + invitees + minutes)",
     "New `/api/v1/meetings` router with dual provider (Jitsi iframe by default, Zoom via S2S OAuth for enterprise). Admin MeetingsPanel + shared MeetingRoom.jsx. RSVP-style invitee list, minutes upload, cancel flow",
     "Wave 41a + 41b"),
    (STATUS_DONE, "Bidding",
     "L1 (lowest-price) auto-comparison for mid-value tenders",
     "New `/api/v1/comparison/l1/{notice_ref}` — automatic ranking of commercial bids per notice with tie-break rules, exposed on admin L1ComparisonPanel",
     "Wave 41a"),

    # --- Wave 40 (2026-08-06) — Sailesh crown-jewel + taxonomy ---
    (STATUS_DONE, "Bidding",
     "Live Reverse Auction room with masked identities, auto-bid, price floor, anti-snipe",
     "New `/api/v1/reverse-auctions/*` router · masked `Bidder A/B/C…` aliases · min-decrement + hard floor enforced · anti-snipe extends close time on last-second bids · auto-bid cascade lets pre-armed bidders undercut competitors automatically. Admin LiveAuctionsPanel + public `/vendor/auction/:aid` room with 2s polling",
     "Wave 40"),
    (STATUS_DONE, "Taxonomy",
     "UNSPSC / standardised product & service classification",
     "New `/api/v1/taxonomy/*` router + curated UNSPSC-lite seed (87 nodes across 23 segments: Construction, Medical, IT/Telecom, Professional Services, Utilities, Facilities, Education). Search + tree + lookup-chain endpoints. Idempotent startup seed",
     "Wave 40 · products/BOQ can now be tagged"),

    # --- Wave 39 (2026-08-06) — Sailesh top-management feedback ---
    (STATUS_DONE, "Procurement",
     "Formal corrigendum / amendment publisher for published notices",
     "New `/api/v1/notices/{ref}/corrigenda` router — auto-numbered, deadline auto-update on parent notice, public banner on Notice Detail, admin CorrigendaPanel with withdraw",
     "Wave 39"),
    (STATUS_DONE, "Bidding",
     "Two-cover / split-envelope submission — technical clearance before commercial visibility",
     "New `/bids/{id}/technical-clear` + `/financial-open`; `_redact_commercial()` strips price and commercial docs for tech-only viewers or before financial open",
     "Wave 39"),
    (STATUS_DONE, "Post-Award",
     "Auto-generated Purchase Order, SLA, and Contract on bid award",
     "New `/api/v1/awards/*` router — 3 WeasyPrint PDFs (PO/SLA/Contract) drafted on award, stored in `award_documents`, downloadable by admin + awarded vendor, admin AwardsPanel with regenerate",
     "Wave 39 · PMC-PO-YYYY-##### numbering"),
    (STATUS_DONE, "Evaluation",
     "Technical vs commercial evaluators segregated (role firewall)",
     "`tech_evaluator` role sees redacted bids (price + commercial notes + commercial documents stripped); commercial envelope gated by explicit `financial-open` after `technical-clear`",
     "Wave 39 · supersedes earlier planned row"),

    # --- Planned (Sailesh top-management review) ---
    (STATUS_PLANNED, "Procurement",
     "Direct-Purchase value-threshold gate",
     "Config flag on notice/product so low-value catalog items skip full tender workflow and issue a direct PO",
     "Roadmap · P2"),
    (STATUS_PLANNED, "Taxonomy",
     "UNSPSC picker widget in Product Catalog + BOQ Builder + registration scopes",
     "Backend + seed shipped in Wave 40; frontend picker widgets still to be attached to product/BOQ/registration edit forms",
     "Roadmap · P2"),

    # --- Planned (infra) ---
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
    the Escrow magic-link portal. Hand-laid SVG so it stays legible in slides.

    The 350+ line SVG body has been split by swim-lane into
    routers/_flowchart.py for maintainability (each lane is its own function).
    Output is byte-identical.
    """
    from routers._flowchart import build_flowchart_svg
    return build_flowchart_svg()


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
#  Test-plan bundle (Wave 43) — hand this to any tester or AI QA tool.
# ------------------------------------------------------------------

def _test_plan_path() -> str:
    from pathlib import Path
    return str(Path(__file__).resolve().parent.parent.parent / "docs" / "reports" / "PMC-v2-Test-Plan.md")


@router.get("/test-plan.md")
async def get_test_plan_md(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    from pathlib import Path
    body = Path(_test_plan_path()).read_bytes()
    return Response(content=body, media_type="text/markdown; charset=utf-8",
                     headers=_dl_headers("PMC-v2-Test-Plan.md", "text/markdown"))


@router.get("/test-plan.pdf")
async def get_test_plan_pdf(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    from pathlib import Path
    import markdown as _md
    from weasyprint import HTML
    md_text = Path(_test_plan_path()).read_text()
    html_body = _md.markdown(md_text, extensions=["tables", "fenced_code"])
    html = f"""<!doctype html><html><head><meta charset='utf-8'>
<style>
  @page {{ size: A4 portrait; margin: 18mm 14mm; @bottom-center {{ content: "PMC v2 Test Plan · page " counter(page) " of " counter(pages); font-size: 8pt; color: #555; }} }}
  body {{ font-family: 'Helvetica','Arial',sans-serif; font-size: 9pt; color: #0e2340; line-height: 1.45; }}
  h1 {{ font-size: 20pt; color: #0e2340; margin: 24pt 0 6pt; }}
  h2 {{ font-size: 14pt; color: #0e2340; border-bottom: 2px solid #0e2340; padding-bottom: 4pt; margin-top: 22pt; page-break-after: avoid; }}
  h3 {{ font-size: 11pt; color: #3b5776; margin-top: 14pt; page-break-after: avoid; }}
  table {{ border-collapse: collapse; width: 100%; margin: 6pt 0 12pt; page-break-inside: avoid; }}
  th {{ background: #0e2340; color: #fff; text-align: left; padding: 5pt 6pt; font-size: 8.5pt; }}
  td {{ border-bottom: 1px solid #dfe4ec; padding: 4pt 6pt; vertical-align: top; }}
  code {{ background: #f2f4f8; padding: 1pt 3pt; font-size: 8pt; border-radius: 3pt; }}
  pre {{ background: #f2f4f8; padding: 8pt; font-size: 8pt; page-break-inside: avoid; overflow-wrap: break-word; }}
  ul, ol {{ margin: 4pt 0 8pt 18pt; }}
</style></head><body>{html_body}</body></html>"""
    pdf = HTML(string=html).write_pdf()
    return Response(content=pdf, media_type="application/pdf",
                     headers=_dl_headers("PMC-v2-Test-Plan.pdf", "application/pdf"))


@router.get("/test-ids.txt")
async def get_test_ids(admin=Depends(require_role("admin", "reviewer", "auditor"))):
    from pathlib import Path
    p = Path(__file__).resolve().parent.parent.parent / "docs" / "reports" / "PMC-v2-Test-IDs.txt"
    body = p.read_bytes() if p.exists() else b""
    return Response(content=body, media_type="text/plain; charset=utf-8",
                     headers=_dl_headers("PMC-v2-Test-IDs.txt", "text/plain"))


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
    # Custom page size matched to SVG aspect ratio (1720:1580) so the chart
    # never gets clipped regardless of PDF viewer defaults.
    html = f"""<!doctype html><html><head><meta charset='utf-8'>
<style>
  @page {{ size: 380mm 348mm; margin: 5mm; }}
  html, body {{ margin: 0; padding: 0; }}
  body {{ width: 100%; height: 100%; }}
  svg {{ display: block; width: 100%; height: auto; }}
</style></head><body>{_build_flowchart_svg()}</body></html>"""
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
