"""
Rebuild the trainee manual with real production screenshots embedded.
Overwrites /app/deliverables/PMC_Trainee_Manual.{docx,pdf}
"""
import os
from pathlib import Path
from datetime import datetime

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

from weasyprint import HTML, CSS

OUT = Path("/app/deliverables")
OUT.mkdir(parents=True, exist_ok=True)
SHOTS = Path("/tmp/pmc-shots")
LOGO = "/app/frontend/public/pmc-logo.png"
BRAND = RGBColor(0x0B, 0x2E, 0x4F)
ACCENT = RGBColor(0xC8, 0x9B, 0x3C)
TODAY = datetime.now().strftime("%B %Y")


# ---------- Chapter definition (single source of truth) ----------
# Each chapter: (title, intro_para, sub_headings[list of (heading, bullets[])], screenshot_file)
CHAPTERS = [
    # 1
    ("Chapter 1 — Before You Start",
     "A few essentials to have ready before you sign in for the first time.",
     [("Requirements", [
         "A modern browser (Chrome, Edge, or Firefox — latest version).",
         "A stable internet connection.",
         "Your login credentials (provided by your admin).",
         "This handbook open on a second screen or printed alongside you.",
       ]),
      ("Portal URL", [
         "https://www.pmcmanagers.com — bookmark this now.",
       ])],
     None),

    # 2
    ("Chapter 2 — Logging In",
     "PMC uses a dual-portal login. Employees on the left, vendors on the right.",
     [("Step-by-step (Employee)", [
         "Open https://www.pmcmanagers.com and click “Sign in”.",
         "You land on the “Choose your portal” screen.",
         "On the left card, enter your PMC email.",
         "Enter your temporary password.",
         "Pick your Employee Role from the dropdown (Admin, Escrow, Certifier, Legal, Accounting, Committee, Reviewer, Auditor, Support).",
         "Click “Sign in as Employee”.",
         "On first sign-in you will be forced to change your password — use at least 12 characters, mixed types.",
         "You land on the Admin Console dashboard.",
       ]),
      ("Step-by-step (Vendor)", [
         "Same URL, right-hand card.",
         "Enter your registered vendor email + password.",
         "Click “Sign in as Vendor”.",
         "New suppliers: use the “Register your company” link below the form.",
       ]),
      ("Troubleshooting", [
         "Forgot password → click the “Forgot password” link on the login screen.",
         "Locked out after too many attempts → wait 15 minutes or email adminsupport@pmcmanagers.com.",
         "Blank screen → hard refresh (Ctrl + Shift + R).",
         "Language: switch between EN / RU / KK via the top-right toggle.",
       ])],
     "02b-login-fresh.jpg"),

    # 3
    ("Chapter 3 — The Admin Console at a Glance",
     "Once signed in as an employee you land on the “Operations overview”. This is your control tower — 22 tabs, one screen.",
     [("Regions to memorise", [
         "Top bar: PMC logo, public menu (Notices / Register / Check status), language toggle, Sign out.",
         "Header card: kicker (‘PMC · Admin Console’), title, quick actions — Portal switch, Alerts, AI Copilot, Security · 2FA, and your signed-in email.",
         "Tab strip: 22 module tabs (Dashboard, Registrations, Vendors, Notices, Corrigenda, Tender Builder, Bidding Ops, Escrow (EMD), Evaluation, Awards & POs, DocuSign, Reverse Auctions, Meetings, L1 Comparison, BOQ & Contracts, Vendor Intel, Masters, Permissions, Packages, Audit, Product Catalog, Engagements, Stakeholder Reports).",
         "KPI cards: Published Notices, Vendors, Bids, Awarded, Pending EMD, EMD Collected, Active Contracts.",
         "Pipeline Funnel: counts at each pipeline stage (emd_pending → awarded).",
         "Top-Priced Bids table: quick ranking of the highest-value bids in the system.",
       ])],
     "06-analytics.jpg"),

    # 4
    ("Chapter 4 — Notice Board (Public + Admin)",
     "The Notice Board is the public face of every tender. Admins manage it from the “Notices” tab.",
     [("Public flow", [
         "Anyone can open /notices without logging in.",
         "Filter tenders by type (Tender / RFP / RFQ) and by country.",
         "Click any card to open the full brief and download the RFP PDF.",
         "Note the closing date and EMD amount before you start a bid.",
       ]),
      ("Admin flow (Notices tab)", [
         "Click “New Notice” at the top-right to publish a fresh tender.",
         "Attach the tender PDF (or link a template from Tender Builder).",
         "Use “Preview as Bidder” to see exactly what suppliers will see.",
         "Notices marked TEMPLATE LINKED reuse a saved template.",
       ])],
     "09-notices-admin.jpg"),

    # 5
    ("Chapter 5 — Vendor Registration",
     "Suppliers self-onboard through a three-section wizard. Admins approve them from the Registrations tab.",
     [("Vendor’s three sections", [
         "Section A — Company details: legal name, tax ID, HQ address, contact.",
         "Section B — Documents: certificate of incorporation, tax cert, bank letter (PDF/JPG, ≤ 10 MB).",
         "Section C — Categories: pick UNSPSC codes for the goods and services supplied.",
         "Submit → the vendor enters KYC review status.",
       ]),
      ("Admin action", [
         "Open the Registrations tab.",
         "Review submitted documents.",
         "Approve, request corrections, or reject.",
         "Approved vendors appear in the Vendors tab and can bid.",
       ])],
     "04-vendor-register.jpg"),

    # 6
    ("Chapter 6 — Package Tracker",
     "Every tender is a “package”. The Packages tab shows exactly where each package is in the lifecycle.",
     [("What to look for", [
         "Package status stepper: Draft → Published → Bidding → Evaluation → Award → Signed.",
         "Filter by tenant, status, or wave.",
         "Click any package to drill into its documents, bidders, and status history.",
       ])],
     "18-packages.jpg"),

    # 7
    ("Chapter 7 — Bidding Ops",
     "The heart of the platform. Vendors submit bids; admins open and manage the envelopes.",
     [("Vendor flow", [
         "Open a tender from the Notice Board.",
         "Click “Submit Bid”.",
         "Pay EMD via Stripe (sandbox card 4242 4242 4242 4242).",
         "Upload technical + commercial envelopes.",
         "Confirm submission — you receive a unique Bid ID (e.g. PMC-BID-2026-00005).",
       ]),
      ("Admin flow", [
         "Bidding Ops tab → select the tender.",
         "Wait until the closing time, then click “Open Envelopes”.",
         "Review each bid; forward scores to the Evaluation module.",
       ])],
     "11-bidding.jpg"),

    # 8
    ("Chapter 8 — Escrow (EMD)",
     "Earnest Money Deposits are held in escrow until the bid outcome. This tab is the escrow officer’s workspace.",
     [("Officer actions", [
         "See every EMD in flight, grouped by status.",
         "Accept / release / forfeit deposits in line with tender rules.",
         "Auto-audit every action into the Audit ledger.",
       ])],
     "12-escrow.jpg"),

    # 9
    ("Chapter 9 — Evaluation & L1 Comparison",
     "The Evaluation tab lets committees score bids. L1 Comparison shows the lowest technically-qualified price.",
     [("Steps", [
         "Open Evaluation → pick the tender.",
         "Enter technical scores per bidder (0–100).",
         "Enter commercial scores — the system computes the weighted total.",
         "The top-ranked bidder is highlighted.",
         "Click “Award” — Award Letter, PO, SLA, and Contract are drafted automatically.",
       ])],
     "13-evaluation.jpg"),

    # 10
    ("Chapter 10 — Awards & Purchase Orders",
     "The moment a bid is awarded, PMC auto-generates the full document set: Purchase Order, SLA, and Contract / LOA.",
     [("Card layout", [
         "Each award has three cards: Purchase Order, Service Level Agreement, Contract / LOA.",
         "Each card shows the document number, issue date, file size.",
         "Actions per card: Download PDF, Send for Signature.",
         "“Regenerate documents” rebuilds the entire pack in one click if a template changes.",
       ])],
     "14-awards.jpg"),

    # 11
    ("Chapter 11 — DocuSign eSignature",
     "PMC integrates DocuSign via JWT Grant + Connect Webhook. All award docs can be signed without leaving the portal.",
     [("Connection panel", [
         "Environment: sandbox (or live once switched).",
         "Credentials + User consent must show ✓ granted.",
         "Account ID is masked for security.",
       ]),
      ("Requesting a signature", [
         "Pick the delivery mode: Embedded (in-browser, recommended) or Email.",
         "Select the awarded bid + document (PO / SLA / Contract).",
         "Click “Send” — status flips to “sent”, then “delivered”, then “completed” via webhook.",
         "For the investor demo, always use Embedded — sandbox blocks external emails.",
       ])],
     "15-docusign.jpg"),

    # 12
    ("Chapter 12 — Reverse Auctions",
     "Live e-auctions let shortlisted vendors bid down in real time.",
     [("Steps", [
         "Open Reverse Auctions tab → schedule a new auction.",
         "Invite the shortlisted vendors.",
         "At the start time, vendors compete in a live price-drop.",
         "Winner is captured automatically at auction close.",
       ])],
     "22-auctions.jpg"),

    # 13
    ("Chapter 13 — Meetings",
     "Pre-bid conferences and clarification meetings — hosted via Zoom or Jitsi links from within the portal.",
     [("Steps", [
         "Meetings tab → “Schedule meeting”.",
         "Pick provider (Zoom / Jitsi), date/time, attendees.",
         "The system emails join links + posts to the Notice Board.",
         "Recordings and minutes attach back to the tender package.",
       ])],
     "21-meetings.jpg"),

    # 14
    ("Chapter 14 — BOQ & Contracts",
     "Bill-of-Quantities builder feeds the Contract module. Every line item can be tagged with a UNSPSC code.",
     [("Steps", [
         "Open BOQ & Contracts inside the tender you are drafting.",
         "Click “+ Add Line Item”.",
         "Enter description, unit, quantity, and rate.",
         "Attach the correct UNSPSC code from the picker.",
         "Save — totals auto-calculate.",
         "Export the BOQ as PDF or Excel from the top-right menu.",
       ])],
     "16-boq.jpg"),

    # 15
    ("Chapter 15 — Vendor Intelligence",
     "A 360° view of each supplier: performance history, risk flags, past awards.",
     [("What you see", [
         "Search by name or tax ID.",
         "Vendor performance score.",
         "Award / bid history.",
         "Risk flags — sanctions, blacklists, poor delivery scores.",
         "Use this before shortlisting on high-value tenders.",
       ])],
     "17-vintel.jpg"),

    # 16
    ("Chapter 16 — Product Catalog",
     "The commercial engine. Publish catalog items that vendors can subscribe to or purchase via Stripe.",
     [("Admin actions", [
         "Add / edit catalog items.",
         "Set price, tax code, description, imagery.",
         "Enable Stripe checkout per item.",
         "Track engagements and quotes.",
       ])],
     "19-catalog.jpg"),

    # 17
    ("Chapter 17 — Stakeholder Reports",
     "One-click exports of the portfolio for management, board packs, and investor updates.",
     [("What you can export", [
         "Tender pipeline snapshot.",
         "Awarded contracts by tenant / country / period.",
         "Vendor onboarding funnel.",
         "EMD collection ledger.",
       ])],
     "20-reports.jpg"),

    # 18
    ("Chapter 18 — Masters",
     "System-wide reference data: tenants, currencies, tax codes, notice templates. Keep this tidy.",
     [("Rules", [
         "Only Master Admins can edit masters.",
         "Every change writes to the Audit ledger.",
         "Deleting a master row is soft-delete — it is preserved for compliance.",
       ])],
     "23-masters.jpg"),

    # 19
    ("Chapter 19 — Registrations Queue",
     "The KYC officer’s daily inbox — every pending vendor registration lives here.",
     [("Daily rhythm", [
         "Open Registrations first thing every morning.",
         "Sort by submission date ascending — oldest first.",
         "Approve, return-for-correction, or reject with a reason (visible to the vendor).",
       ])],
     "07-registrations.jpg"),

    # 20
    ("Chapter 20 — Audit Trail",
     "Every action in PMC is written to a SHA-256 hash-chained ledger. Nothing can be quietly changed.",
     [("What to check weekly", [
         "Number of admin logins vs expected staff.",
         "Password change events.",
         "Any hash-chain gap → click “Verify chain” to reassure yourself.",
       ])],
     "24-audit.jpg"),

    # 21
    ("Chapter 21 — Vendors Directory",
     "The active supplier roster — approved and bid-ready.",
     [("What you can do", [
         "Search, sort, and filter suppliers.",
         "Open a vendor card to see documents, contacts, and history.",
         "Suspend or reactivate a vendor when needed.",
       ])],
     "08-vendors.jpg"),

    # 22
    ("Chapter 22 — Corrigenda & Tender Builder",
     "Corrigenda are corrections to published tenders. Tender Builder is where reusable templates live.",
     [("Corrigenda", [
         "Every correction after a notice is published must be issued as a corrigendum.",
         "The system versions the tender document and re-notifies bidders automatically.",
       ]),
      ("Tender Builder", [
         "Reusable templates for Tender / RFP / RFQ.",
         "Link a template when creating a new notice to inherit clauses, evaluation criteria, and BOQ skeleton.",
       ])],
     "10-tender-builder.jpg"),

    # 23
    ("Chapter 23 — Your Profile & Security",
     "Owning your account security is not optional.",
     [("Daily hygiene", [
         "Never share credentials.",
         "Enable 2FA under “Security · 2FA” in the top bar.",
         "Change your password every 90 days.",
         "Sign out on shared computers.",
       ])],
     "25-topbar-profile.jpg"),

    # 24 — closing
    ("Chapter 24 — Trainee Daily Checklist",
     "Run this checklist every day for your first two weeks.",
     [("Every morning", [
         "Log in and skim the Dashboard KPI cards.",
         "Open Registrations — clear anything pending > 24 hours.",
         "Review tenders closing within 48 hours (Notices → filter by closing date).",
         "Bidding Ops — confirm no bids are stuck in “Awaiting Envelope Open”.",
         "DocuSign — verify envelope statuses have refreshed.",
         "Audit — glance at yesterday’s activity for anomalies.",
         "Log any anomaly in the internal ticket tool before leaving.",
       ])],
     None),
]

GLOSSARY = [
    ["Tender", "A formal invitation to submit an offer"],
    ["RFP", "Request for Proposal"],
    ["RFQ", "Request for Quotation"],
    ["EMD", "Earnest Money Deposit"],
    ["BOQ", "Bill of Quantities"],
    ["UNSPSC", "United Nations Standard Products & Services Code"],
    ["KYC", "Know Your Customer verification"],
    ["PO", "Purchase Order"],
    ["SLA", "Service Level Agreement"],
    ["LOA", "Letter of Award"],
    ["L1", "Lowest technically-qualified price"],
    ["Envelope", "Sealed set of bid documents (technical / commercial)"],
    ["Corrigendum", "Amendment to a published tender"],
    ["Escrow", "Neutral holding of EMD until the tender concludes"],
]


# ============================================================
#                        DOCX BUILDER
# ============================================================
def _hdr(doc, text, level, color=BRAND):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt({0: 26, 1: 18, 2: 13}.get(level, 12))
    r.font.color.rgb = color
    if level == 0:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER


def _p(doc, text, italic=False, bold=False, align=None, size=11, color=None):
    p = doc.add_paragraph()
    if align:
        p.alignment = align
    r = p.add_run(text)
    r.italic = italic
    r.bold = bold
    r.font.size = Pt(size)
    if color:
        r.font.color.rgb = color


def _bullets(doc, items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(it).font.size = Pt(11)


def _table(doc, headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    for i, h in enumerate(headers):
        cell = t.rows[0].cells[i]
        cell.text = ""
        r = cell.paragraphs[0].add_run(h)
        r.bold = True
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        r.font.size = Pt(11)
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "0B2E4F")
        cell._tc.get_or_add_tcPr().append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, v in enumerate(row):
            cells[i].text = str(v)
            for para in cells[i].paragraphs:
                for r in para.runs:
                    r.font.size = Pt(10)
    doc.add_paragraph()


def _screenshot(doc, filename, caption):
    path = SHOTS / filename
    if not path.exists():
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(str(path), width=Inches(6.3))
    cap = doc.add_paragraph()
    cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cap.add_run(f"Figure — {caption}")
    r.italic = True
    r.font.size = Pt(9)
    r.font.color.rgb = RGBColor(0x66, 0x66, 0x66)
    doc.add_paragraph()


def build_docx():
    doc = Document()
    for s in doc.sections:
        s.top_margin = Inches(0.7)
        s.bottom_margin = Inches(0.7)
        s.left_margin = Inches(0.8)
        s.right_margin = Inches(0.8)

    # ---- Cover
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run().add_picture(LOGO, width=Inches(2.0))
    for _ in range(2):
        doc.add_paragraph()
    _hdr(doc, "PMC Managers Portal", 0)
    _p(doc, "Trainee Handbook — Illustrated Edition",
       italic=True, align=WD_ALIGN_PARAGRAPH.CENTER, size=14, color=ACCENT)
    for _ in range(2):
        doc.add_paragraph()
    _p(doc, "Every module, every screen, captured from the live portal.",
       align=WD_ALIGN_PARAGRAPH.CENTER, size=12)
    for _ in range(6):
        doc.add_paragraph()
    _p(doc, f"PMC Managers Limited  ·  {TODAY}",
       italic=True, color=BRAND, align=WD_ALIGN_PARAGRAPH.CENTER)
    _p(doc, "www.pmcmanagers.com",
       align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_page_break()

    # ---- Welcome
    _hdr(doc, "Welcome!", 1)
    _p(doc,
       "This is the illustrated version of the PMC Managers trainee "
       "handbook. Every chapter includes a real screenshot from the live "
       "portal so you can match the words in front of you to the screen in "
       "front of you.")
    _p(doc, "Estimated self-training time: 4–6 hours across 2 days.",
       italic=True)
    _p(doc,
       "Chapters 1–11 are essential. Chapters 12–22 give you full command "
       "of every module. Chapters 23–24 are your ongoing hygiene routine.")
    doc.add_page_break()

    # ---- Chapters
    for title, intro, sections, shot in CHAPTERS:
        _hdr(doc, title, 1)
        if intro:
            _p(doc, intro)
        for sub_title, bullets in sections:
            _hdr(doc, sub_title, 2)
            _bullets(doc, bullets)
        if shot:
            _screenshot(doc, shot, title.split("—", 1)[-1].strip())
        doc.add_paragraph()

    # ---- Glossary
    _hdr(doc, "Chapter 25 — Glossary", 1)
    _table(doc, ["Term", "Meaning"], GLOSSARY)

    # ---- Closing
    _hdr(doc, "You Are Ready!", 1)
    _p(doc,
       "Complete Chapters 1–11 in your first sitting. Practise Chapters "
       "12–22 in the sandbox environment before touching production data. "
       "When in doubt — ask, don't guess.", italic=True)
    _p(doc, "Welcome to the PMC Managers team.",
       bold=True, color=BRAND, align=WD_ALIGN_PARAGRAPH.CENTER)

    path = OUT / "PMC_Trainee_Manual.docx"
    doc.save(path)
    return path


# ============================================================
#                        PDF BUILDER
# ============================================================
CSS_STYLE = """
@page { size: A4; margin: 20mm 18mm; @bottom-right { content: "Page " counter(page) " / " counter(pages); font-size: 9pt; color: #666; } }
body { font-family: 'Helvetica','Arial',sans-serif; color: #1a2233; font-size: 11pt; line-height: 1.5; }
h1.cover-title { font-size: 34pt; color: #0B2E4F; text-align:center; margin-top: 40mm; }
h2.cover-sub { font-size: 16pt; color: #C89B3C; text-align:center; font-style: italic; font-weight: 400; }
p.cover-tag { text-align:center; font-size: 12pt; margin-top: 24mm; }
p.cover-foot { text-align:center; font-size: 10pt; color: #0B2E4F; margin-top: 60mm; font-style: italic; }
img.logo { display:block; margin: 0 auto 8mm auto; width: 130px; }
h1 { color: #0B2E4F; font-size: 20pt; border-bottom: 2px solid #C89B3C; padding-bottom: 4px; margin-top: 14mm; page-break-after: avoid; }
h2 { color: #0B2E4F; font-size: 13pt; margin-top: 6mm; page-break-after: avoid; }
ul { padding-left: 20px; }
li { margin-bottom: 4px; }
table { border-collapse: collapse; width: 100%; margin: 6mm 0; font-size: 10pt; }
th { background: #0B2E4F; color: #fff; text-align: left; padding: 6px 8px; }
td { padding: 5px 8px; border: 1px solid #d0d0d0; vertical-align: top; }
tr:nth-child(even) td { background: #f7f7f9; }
.pagebreak { page-break-before: always; }
.callout { background: #f4f0e3; border-left: 4px solid #C89B3C; padding: 8px 12px; margin: 6mm 0; font-style: italic; }
figure { margin: 6mm 0; page-break-inside: avoid; text-align:center; }
figure img { width: 100%; border: 1px solid #d5d8de; box-shadow: 0 1px 4px rgba(0,0,0,0.08); }
figcaption { font-size: 9pt; color: #666; font-style: italic; margin-top: 3mm; }
"""


def _ul(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def _tbl(headers, rows):
    h = "".join(f"<th>{c}</th>" for c in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows
    )
    return f"<table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>"


def _fig(filename, caption):
    path = SHOTS / filename
    if not path.exists():
        return ""
    return (f"<figure><img src='file://{path}' />"
            f"<figcaption>Figure — {caption}</figcaption></figure>")


def build_pdf():
    html = (
        f"<img class='logo' src='file://{LOGO}' />"
        f"<h1 class='cover-title'>PMC Managers Portal</h1>"
        f"<h2 class='cover-sub'>Trainee Handbook — Illustrated Edition</h2>"
        f"<p class='cover-tag'>Every module, every screen, captured from the live portal.</p>"
        f"<p class='cover-foot'>PMC Managers Limited &middot; {TODAY}<br/>www.pmcmanagers.com</p>"
        f"<div class='pagebreak'></div>"
    )

    html += "<h1>Welcome!</h1>"
    html += ("<p>This is the illustrated version of the PMC Managers trainee "
             "handbook. Every chapter includes a real screenshot from the "
             "live portal so you can match the words in front of you to the "
             "screen in front of you.</p>"
             "<div class='callout'>Estimated self-training time: 4–6 hours "
             "across 2 days.</div>"
             "<p>Chapters 1–11 are essential. Chapters 12–22 give you full "
             "command of every module. Chapters 23–24 are your ongoing "
             "hygiene routine.</p>")
    html += "<div class='pagebreak'></div>"

    for title, intro, sections, shot in CHAPTERS:
        html += f"<h1>{title}</h1>"
        if intro:
            html += f"<p>{intro}</p>"
        for sub_title, bullets in sections:
            html += f"<h2>{sub_title}</h2>"
            html += _ul(bullets)
        if shot:
            html += _fig(shot, title.split("—", 1)[-1].strip())

    html += "<h1>Chapter 25 — Glossary</h1>" + _tbl(
        ["Term", "Meaning"], GLOSSARY)

    html += "<h1>You Are Ready!</h1>"
    html += ("<p><em>Complete Chapters 1–11 in your first sitting. Practise "
             "Chapters 12–22 in the sandbox environment before touching "
             "production data. When in doubt — ask, don't guess.</em></p>"
             "<p style='text-align:center;font-weight:bold;color:#0B2E4F;"
             "font-size:14pt;margin-top:12mm;'>"
             "Welcome to the PMC Managers team.</p>")

    path = OUT / "PMC_Trainee_Manual.pdf"
    HTML(string=f"<html><head><meta charset='utf-8'></head><body>{html}</body></html>") \
        .write_pdf(str(path), stylesheets=[CSS(string=CSS_STYLE)])
    return path


if __name__ == "__main__":
    for p in (build_docx(), build_pdf()):
        size_kb = os.path.getsize(p) / 1024
        print(f"OK {p}  ({size_kb:.1f} KB)")
