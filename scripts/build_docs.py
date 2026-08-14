"""
Build investor deck + trainee manual in .docx and .pdf.
Outputs land in /app/deliverables/
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
LOGO = "/app/frontend/public/pmc-logo.png"
BRAND = RGBColor(0x0B, 0x2E, 0x4F)   # deep navy
ACCENT = RGBColor(0xC8, 0x9B, 0x3C)  # gold
TODAY = datetime.now().strftime("%B %Y")


# ---------------------------- DOCX HELPERS ----------------------------
def add_heading(doc, text, level=1, color=BRAND):
    p = doc.add_paragraph()
    run = p.add_run(text)
    run.bold = True
    sizes = {0: 26, 1: 18, 2: 14, 3: 12}
    run.font.size = Pt(sizes.get(level, 12))
    run.font.color.rgb = color
    if level == 0:
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    return p


def add_para(doc, text, bold=False, italic=False, size=11, color=None, align=None):
    p = doc.add_paragraph()
    if align:
        p.alignment = align
    run = p.add_run(text)
    run.font.size = Pt(size)
    run.bold = bold
    run.italic = italic
    if color:
        run.font.color.rgb = color
    return p


def add_bullets(doc, items):
    for it in items:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(it).font.size = Pt(11)


def add_table(doc, headers, rows):
    t = doc.add_table(rows=1, cols=len(headers))
    t.style = "Light Grid Accent 1"
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ""
        p = hdr[i].paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        r.font.size = Pt(11)
        tc_pr = hdr[i]._tc.get_or_add_tcPr()
        shd = OxmlElement("w:shd")
        shd.set(qn("w:fill"), "0B2E4F")
        tc_pr.append(shd)
    for row in rows:
        cells = t.add_row().cells
        for i, val in enumerate(row):
            cells[i].text = str(val)
            for para in cells[i].paragraphs:
                for run in para.runs:
                    run.font.size = Pt(10)
    doc.add_paragraph()


def cover(doc, title, subtitle, tagline):
    if os.path.exists(LOGO):
        p = doc.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        p.add_run().add_picture(LOGO, width=Inches(2.0))
    for _ in range(2):
        doc.add_paragraph()
    add_heading(doc, title, level=0)
    add_para(doc, subtitle, size=14, italic=True, color=ACCENT,
             align=WD_ALIGN_PARAGRAPH.CENTER)
    for _ in range(3):
        doc.add_paragraph()
    add_para(doc, tagline, size=12, align=WD_ALIGN_PARAGRAPH.CENTER)
    for _ in range(6):
        doc.add_paragraph()
    add_para(doc, f"PMC Managers Limited  ·  {TODAY}",
             size=11, italic=True, color=BRAND,
             align=WD_ALIGN_PARAGRAPH.CENTER)
    add_para(doc, "www.pmcmanagers.com", size=11,
             align=WD_ALIGN_PARAGRAPH.CENTER)
    doc.add_page_break()


# ============================================================
#                   INVESTOR DECK CONTENT
# ============================================================
def build_investor_docx():
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    cover(
        doc,
        "PMC Managers v2",
        "Enterprise CRM & e-Tender Platform",
        "A global tender management ecosystem — built, secured, deployed."
    )

    # ---- Executive Summary
    add_heading(doc, "1. Executive Summary", level=1)
    add_para(doc,
        "PMC Managers v2 is a production-grade, multi-tenant e-Tender and "
        "procurement management platform mirroring a 39-page Enterprise CRM "
        "specification. It orchestrates the complete tender lifecycle — from "
        "notice publication and vendor onboarding to bidding, evaluation, "
        "contract award, and digital signature — under a single white-labeled "
        "product live at www.pmcmanagers.com.")
    add_para(doc,
        "The system is deployed on AWS with a hardened security posture, "
        "integrates DocuSign for legally binding eSignature, Stripe for "
        "payments, and an AI Audit Copilot for real-time compliance review.",
        italic=True)

    # ---- The Problem
    add_heading(doc, "2. The Problem We Solve", level=1)
    add_bullets(doc, [
        "Public and private tenders are fragmented across PDFs, emails, "
        "and spreadsheets — driving cycle times of 60–120 days.",
        "Vendor onboarding is manual and paper-heavy, blocking access for "
        "SMEs and slowing procurement.",
        "Bid evaluation lacks auditability, exposing organizations to "
        "compliance risk and legal disputes.",
        "Cross-border tenders demand multi-currency payments, KYC, and "
        "digital signatures — capabilities no single incumbent bundles.",
    ])

    # ---- The Solution
    add_heading(doc, "3. Our Solution", level=1)
    add_para(doc,
        "PMC Managers v2 collapses the entire tender pipeline into one "
        "role-aware portal with dynamic Approval Matrices, joint-signature "
        "escrow, and an AI compliance copilot.")
    add_bullets(doc, [
        "Three distinct role experiences: Admin, Vendor, Staff.",
        "Full lifecycle: Notice Board → Registration → Bidding → BOQ → "
        "Evaluation → Award → eSignature.",
        "Revenue built in: Product Catalog, Stripe checkout, Quote "
        "pipeline, Subscriptions.",
        "White-labeled, multi-tenant — ready for franchise and reseller "
        "deployment.",
    ])

    # ---- Core Modules
    add_heading(doc, "4. Core Modules", level=1)
    add_table(doc,
        ["Module", "Function"],
        [
            ["Notice Board", "Publish public tenders, RFPs, and RFQs"],
            ["Vendor Registration", "KYC-driven onboarding with document upload"],
            ["Package Tracker", "Real-time status of every tender package"],
            ["Bidding Management", "EMD payment, bid submission, envelope opening"],
            ["BOQ Builder", "Bill-of-Quantities with UNSPSC classification"],
            ["Evaluation & Contracts", "Committee scoring, award, PO issuance"],
            ["Vendor Intelligence", "Performance scoring and risk analytics"],
            ["Template Builder", "Reusable Tender / RFP / RFQ templates"],
            ["Joint-Signature Escrow", "Multi-party sign-off for high-value awards"],
            ["AI Audit Copilot", "LLM-powered clause and compliance review"],
        ])

    # ---- Technology & Architecture
    add_heading(doc, "5. Technology & Architecture", level=1)
    add_para(doc,
        "The platform is built on a modern, cloud-native stack chosen for "
        "scalability, security, and rapid iteration.")
    add_table(doc,
        ["Layer", "Technology"],
        [
            ["Frontend", "React (SPA), Tailwind, Shadcn UI"],
            ["Backend", "FastAPI (Python), async I/O"],
            ["Database", "MongoDB Atlas (managed, multi-region ready)"],
            ["Compute", "AWS Elastic Beanstalk (Docker)"],
            ["CDN & Static", "AWS S3 + CloudFront"],
            ["DNS & SSL", "Route 53 + ACM"],
            ["AI Layer", "LLM Copilot for audit and clause extraction"],
            ["Auth", "JWT + CSRF double-submit cookies"],
        ])

    # ---- Integrations
    add_heading(doc, "6. Third-Party Integrations", level=1)
    add_table(doc,
        ["Service", "Purpose", "Status"],
        [
            ["DocuSign", "eSignature (JWT Grant + Connect Webhook, HMAC)", "Live"],
            ["Stripe", "Payments, subscriptions, product catalog", "Live"],
            ["AI Copilot", "Tender audit + clause analysis", "Live"],
            ["KYC provider", "Vendor identity verification", "Ready (pluggable)"],
            ["Resend", "Transactional email", "Configured"],
            ["Firebase / APNs", "Push notifications", "Ready (pluggable)"],
            ["Zoom / Jitsi", "Pre-bid meetings", "Ready"],
            ["PayPal / Kaspi", "Regional payments", "Ready (pluggable)"],
        ])

    # ---- Security
    add_heading(doc, "7. Security & Compliance", level=1)
    add_bullets(doc, [
        "HTTPS end-to-end via ACM certificates on CloudFront and EB.",
        "CSRF double-submit cookie protection on every state-changing route.",
        "DocuSign Connect webhooks verified with HMAC signatures.",
        "Password rotation flow and admin change-password API in place.",
        "MongoDB Atlas with IP allow-lists, TLS, and encrypted-at-rest storage.",
        "Fully white-labeled — Git history purged of vendor branding for "
        "IP-clean investor review.",
    ])

    # ---- Deployment
    add_heading(doc, "8. Production Deployment", level=1)
    add_para(doc,
        "The platform is live at https://www.pmcmanagers.com on a fully "
        "owned AWS footprint under the pmcmanagers.com domain. Every "
        "layer — compute, storage, DNS, and certificates — is under direct "
        "customer control.")
    add_table(doc,
        ["Component", "Value"],
        [
            ["Live URL", "https://www.pmcmanagers.com"],
            ["Frontend", "AWS S3 + CloudFront (SPA)"],
            ["Backend", "AWS Elastic Beanstalk (Docker)"],
            ["Database", "MongoDB Atlas (managed)"],
            ["Domain / SSL", "Route 53 + ACM (auto-renew)"],
        ])

    # ---- Engineering Effort
    add_heading(doc, "9. Engineering Effort Snapshot", level=1)
    add_para(doc,
        "The scope delivered represents a substantial engineering investment "
        "across full-stack development, DevOps, and third-party integration.")
    add_table(doc,
        ["Dimension", "Delivered"],
        [
            ["Distinct modules", "10+ core enterprise modules"],
            ["User roles", "3 (Admin, Vendor, Staff) with granular RBAC"],
            ["Backend API surface", "60+ REST endpoints under /api/v1"],
            ["Frontend components", "80+ React components + Shadcn UI kit"],
            ["Third-party integrations", "8 live or plug-ready"],
            ["Deployment environments", "Preview + Production (AWS)"],
            ["Documentation pages", "39-page spec + PRD + Anchor + Manuals"],
            ["Security controls", "CSRF, JWT, HMAC webhooks, TLS, IP allow-list"],
        ])

    # ---- Monetization
    add_heading(doc, "10. Monetization Model", level=1)
    add_bullets(doc, [
        "Vendor subscriptions (tiered) — recurring MRR via Stripe.",
        "Transaction fee on EMD deposits and awarded contracts.",
        "Enterprise white-label licenses for government and franchisees.",
        "Value-added services: KYC packs, AI audit reports, template library.",
    ])

    # ---- Roadmap
    add_heading(doc, "11. Roadmap", level=1)
    add_table(doc,
        ["Priority", "Item"],
        [
            ["P1", "UNSPSC picker in BOQ Builder & Vendor Registration"],
            ["P2", "Investor Analytics Dashboard (live KPI board)"],
            ["P2", "PayPal & Kaspi Pay live-mode activation"],
            ["P2", "Firebase / APNs push notifications"],
            ["P2", "Live KYC provider onboarding"],
            ["P3", "Mobile companion app (React Native)"],
        ])

    # ---- Ask
    add_heading(doc, "12. The Ask", level=1)
    add_para(doc,
        "We invite investment to accelerate go-to-market, activate live "
        "regional payment rails, and scale sales into government and "
        "enterprise procurement. The product is built, deployed, and "
        "revenue-ready — the runway ahead is distribution.",
        bold=True)

    add_para(doc, "")
    add_para(doc, "Contact: PMC Managers Limited  ·  www.pmcmanagers.com",
             italic=True, align=WD_ALIGN_PARAGRAPH.CENTER)

    path = OUT / "PMC_Investor_Deck.docx"
    doc.save(path)
    return path


# ============================================================
#                   TRAINEE MANUAL CONTENT
# ============================================================
def build_trainee_docx():
    doc = Document()
    for section in doc.sections:
        section.top_margin = Inches(0.7)
        section.bottom_margin = Inches(0.7)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    cover(
        doc,
        "PMC Managers Portal",
        "Trainee Handbook — From Zero to Confident User",
        "A step-by-step, screen-by-screen walkthrough of the entire portal."
    )

    # ---- Welcome
    add_heading(doc, "Welcome!", level=1)
    add_para(doc,
        "This handbook takes you through the PMC Managers portal exactly as "
        "you will see it. Read each chapter in order — by the end you will "
        "be able to log in, navigate every module, publish a tender, review "
        "a bid, and send an award for signature.")
    add_para(doc,
        "Estimated self-training time: 4–6 hours across 2 days.",
        italic=True)

    # ---- Prerequisites
    add_heading(doc, "Chapter 1 — Before You Start", level=1)
    add_bullets(doc, [
        "A modern browser (Chrome, Edge, or Firefox — latest version).",
        "A stable internet connection.",
        "Your login credentials (provided by your admin).",
        "This handbook open on a second screen or printed alongside you.",
    ])
    add_para(doc, "Portal URL: https://www.pmcmanagers.com", bold=True)

    # ---- Login
    add_heading(doc, "Chapter 2 — Logging In", level=1)
    add_para(doc, "Step-by-step:")
    add_bullets(doc, [
        "Open https://www.pmcmanagers.com in your browser.",
        "Click the “Login” button at the top-right of the landing page.",
        "You will land on the unified /login screen.",
        "Enter the email address given to you (all lowercase).",
        "Enter your temporary password.",
        "Click “Sign in”.",
        "On first login you will be prompted to change your password — "
        "use at least 12 characters, mix of upper, lower, numbers, symbols.",
        "After a successful login you land on the dashboard matching your "
        "role (Admin / Staff / Vendor).",
    ])
    add_para(doc, "Troubleshooting:", bold=True)
    add_bullets(doc, [
        "Forgot password → click “Forgot password” on the login screen.",
        "Locked out after 5 failed attempts → wait 15 minutes or contact "
        "adminsupport@pmcmanagers.com.",
        "Blank screen → hard refresh (Ctrl + Shift + R).",
    ])

    # ---- Dashboard tour
    add_heading(doc, "Chapter 3 — The Dashboard at a Glance", level=1)
    add_para(doc,
        "The dashboard is your control tower. Every trainee should be able "
        "to name each region before moving on.")
    add_table(doc,
        ["Region", "What it shows"],
        [
            ["Top navigation bar", "Logo, module tabs, notifications, profile"],
            ["Left sidebar", "Quick links to modules (collapses on mobile)"],
            ["Main panel", "The active module's content"],
            ["KPI cards (top)", "Live tenders, open bids, pending approvals"],
            ["Activity feed", "Recent actions across your organization"],
            ["Profile menu (top-right)", "Change password, log out, switch tenant"],
        ])

    # ---- Notice Board
    add_heading(doc, "Chapter 4 — Notice Board", level=1)
    add_para(doc, "The Notice Board is the public face of every tender.")
    add_para(doc, "As a trainee, practise these tasks:", bold=True)
    add_bullets(doc, [
        "Open the Notice Board tab.",
        "Filter tenders by status: Open, Closing Soon, Closed, Awarded.",
        "Click any tender card to see its full brief.",
        "Locate the “Download RFP” button.",
        "Note the closing date and EMD amount.",
    ])

    # ---- Vendor Registration
    add_heading(doc, "Chapter 5 — Vendor Registration", level=1)
    add_para(doc,
        "This is how new suppliers onboard. Walk through each of the three "
        "sections so you can guide a vendor over the phone.")
    add_bullets(doc, [
        "Section A — Company details: legal name, tax ID, address.",
        "Section B — Documents: certificate of incorporation, tax cert, "
        "bank letter. Files must be PDF or JPG under 10 MB.",
        "Section C — Categories: pick UNSPSC codes for the goods/services "
        "the vendor supplies.",
        "Submit — the vendor moves into KYC review status.",
    ])
    add_para(doc, "Admin action: approve or return-for-correction from the "
             "Vendor Management panel.", italic=True)

    # ---- Package Tracker
    add_heading(doc, "Chapter 6 — Package Tracker", level=1)
    add_para(doc,
        "Every tender is a “package”. The tracker shows exactly which "
        "stage each package is in.")
    add_bullets(doc, [
        "Open Package Tracker.",
        "Read the horizontal stepper: Draft → Published → Bidding → "
        "Evaluation → Award → Signed.",
        "Click a package to drill into its documents, bidders, and status "
        "history.",
    ])

    # ---- Bidding
    add_heading(doc, "Chapter 7 — Bidding Management", level=1)
    add_para(doc, "The heart of the platform. Trainees must master this.")
    add_para(doc, "Vendor flow:", bold=True)
    add_bullets(doc, [
        "Open a tender from the Notice Board.",
        "Click “Submit Bid”.",
        "Pay EMD via Stripe (test card 4242 4242 4242 4242 in sandbox).",
        "Upload technical + commercial envelopes.",
        "Confirm submission — you receive a unique Bid ID.",
    ])
    add_para(doc, "Admin flow:", bold=True)
    add_bullets(doc, [
        "Open Bidding Management → select the tender.",
        "Wait until the closing time, then click “Open Envelopes”.",
        "Review each bid; scores are entered in the Evaluation module.",
    ])

    # ---- BOQ Builder
    add_heading(doc, "Chapter 8 — BOQ Builder", level=1)
    add_bullets(doc, [
        "Open BOQ Builder inside the tender you are drafting.",
        "Click “+ Add Line Item”.",
        "Enter description, unit, quantity, and rate.",
        "Attach the correct UNSPSC code from the picker.",
        "Save — totals auto-calculate.",
        "Export the BOQ as PDF or Excel using the top-right menu.",
    ])

    # ---- Evaluation & Contracts
    add_heading(doc, "Chapter 9 — Evaluation & Contracts", level=1)
    add_bullets(doc, [
        "Open Evaluation → pick the tender.",
        "Enter technical scores for each bidder (0–100).",
        "Enter commercial scores — the system computes the weighted total.",
        "The top-ranked bidder is highlighted.",
        "Click “Award” — a draft Award Letter and PO are generated.",
    ])

    # ---- Awards & Signatures
    add_heading(doc, "Chapter 10 — Awards & Digital Signature", level=1)
    add_para(doc,
        "This is where PMC differentiates itself — award documents can be "
        "sent for legally binding e-signature directly from the portal.")
    add_bullets(doc, [
        "Open Awards → pick the awarded tender.",
        "Preview the Award Letter and Purchase Order documents.",
        "Click “Send for Signature” on the document card.",
        "Choose delivery method: Embedded (in-browser) or Email.",
        "For the investor demo, always use Embedded — sandbox blocks "
        "external emails.",
        "The recipient signs; the status auto-updates via DocuSign webhook.",
    ])

    # ---- AI Audit Copilot
    add_heading(doc, "Chapter 11 — AI Audit Copilot", level=1)
    add_bullets(doc, [
        "Open any tender document.",
        "Click the “AI Audit” button on the toolbar.",
        "The copilot summarises the document, flags risky clauses, and "
        "suggests improvements.",
        "Copy the suggestions into your evaluation notes.",
    ])

    # ---- Vendor Intelligence
    add_heading(doc, "Chapter 12 — Vendor Intelligence", level=1)
    add_bullets(doc, [
        "Open Vendor Intelligence.",
        "Search a vendor by name or tax ID.",
        "Review their performance score, past awards, and risk flags.",
        "Use this before shortlisting on high-value tenders.",
    ])

    # ---- Profile & Security
    add_heading(doc, "Chapter 13 — Profile & Security", level=1)
    add_bullets(doc, [
        "Click your avatar in the top-right corner.",
        "Choose “Change Password” — enter old + new password.",
        "Enable “Notification Preferences” to control email alerts.",
        "Always log out on shared computers.",
    ])

    # ---- Daily checklist
    add_heading(doc, "Chapter 14 — Trainee Daily Checklist", level=1)
    add_bullets(doc, [
        "Log in and skim the KPI cards.",
        "Check pending vendor approvals.",
        "Review tenders closing within 48 hours.",
        "Confirm no bids are stuck in “Awaiting Envelope Open”.",
        "Verify DocuSign envelopes have refreshed status.",
        "Log any anomaly in the internal ticket tool before leaving.",
    ])

    # ---- Glossary
    add_heading(doc, "Chapter 15 — Glossary", level=1)
    add_table(doc,
        ["Term", "Meaning"],
        [
            ["Tender", "A formal invitation to submit an offer"],
            ["RFP", "Request for Proposal"],
            ["RFQ", "Request for Quotation"],
            ["EMD", "Earnest Money Deposit"],
            ["BOQ", "Bill of Quantities"],
            ["UNSPSC", "United Nations Standard Products & Services Code"],
            ["KYC", "Know Your Customer verification"],
            ["PO", "Purchase Order"],
            ["Envelope", "Sealed set of bid documents (technical / commercial)"],
        ])

    add_heading(doc, "You Are Ready!", level=1)
    add_para(doc,
        "Complete Chapters 1–10 in your first sitting. Practise Chapters "
        "11–14 in the sandbox environment before touching production data. "
        "When in doubt — ask, don't guess.",
        italic=True)
    add_para(doc, "Welcome to the PMC Managers team.",
             bold=True, color=BRAND, align=WD_ALIGN_PARAGRAPH.CENTER)

    path = OUT / "PMC_Trainee_Manual.docx"
    doc.save(path)
    return path


# ============================================================
#                   PDF (parallel HTML render)
# ============================================================
CSS_STYLE = """
@page { size: A4; margin: 20mm 18mm; @bottom-right { content: "Page " counter(page) " / " counter(pages); font-size: 9pt; color: #666; } }
body { font-family: 'Helvetica','Arial',sans-serif; color: #1a2233; font-size: 11pt; line-height: 1.5; }
h1.cover-title { font-size: 34pt; color: #0B2E4F; text-align:center; margin-top: 40mm; }
h2.cover-sub { font-size: 16pt; color: #C89B3C; text-align:center; font-style: italic; font-weight: 400; }
p.cover-tag { text-align:center; font-size: 12pt; margin-top: 30mm; }
p.cover-foot { text-align:center; font-size: 10pt; color: #0B2E4F; margin-top: 60mm; font-style: italic; }
.logo { display:block; margin: 0 auto 8mm auto; width: 130px; }
h1 { color: #0B2E4F; font-size: 20pt; border-bottom: 2px solid #C89B3C; padding-bottom: 4px; margin-top: 14mm; }
h2 { color: #0B2E4F; font-size: 14pt; margin-top: 8mm; }
h3 { color: #0B2E4F; font-size: 12pt; }
ul { padding-left: 20px; }
li { margin-bottom: 4px; }
table { border-collapse: collapse; width: 100%; margin: 6mm 0; font-size: 10pt; }
th { background: #0B2E4F; color: #fff; text-align: left; padding: 6px 8px; }
td { padding: 5px 8px; border: 1px solid #d0d0d0; vertical-align: top; }
tr:nth-child(even) td { background: #f7f7f9; }
.pagebreak { page-break-before: always; }
strong { color: #0B2E4F; }
.callout { background: #f4f0e3; border-left: 4px solid #C89B3C; padding: 8px 12px; margin: 6mm 0; font-style: italic; }
"""


def _cover_html(title, subtitle, tagline):
    return f"""
    <img class="logo" src="file://{LOGO}" />
    <h1 class="cover-title">{title}</h1>
    <h2 class="cover-sub">{subtitle}</h2>
    <p class="cover-tag">{tagline}</p>
    <p class="cover-foot">PMC Managers Limited &middot; {TODAY}<br/>www.pmcmanagers.com</p>
    <div class="pagebreak"></div>
    """


def _table(headers, rows):
    h = "".join(f"<th>{c}</th>" for c in headers)
    body = "".join(
        "<tr>" + "".join(f"<td>{c}</td>" for c in r) + "</tr>" for r in rows
    )
    return f"<table><thead><tr>{h}</tr></thead><tbody>{body}</tbody></table>"


def _ul(items):
    return "<ul>" + "".join(f"<li>{i}</li>" for i in items) + "</ul>"


def build_investor_pdf():
    html = _cover_html(
        "PMC Managers v2",
        "Enterprise CRM &amp; e-Tender Platform",
        "A global tender management ecosystem — built, secured, deployed."
    )
    html += "<h1>1. Executive Summary</h1>"
    html += ("<p>PMC Managers v2 is a production-grade, multi-tenant e-Tender "
             "and procurement platform mirroring a 39-page Enterprise CRM "
             "specification. It orchestrates the complete tender lifecycle — "
             "from notice publication and vendor onboarding to bidding, "
             "evaluation, contract award, and digital signature — under a "
             "single white-labeled product live at "
             "<strong>www.pmcmanagers.com</strong>.</p>")
    html += ("<div class='callout'>Deployed on AWS with hardened security, "
             "DocuSign eSignature, Stripe payments, and an AI Audit Copilot "
             "for real-time compliance review.</div>")

    html += "<h1>2. The Problem We Solve</h1>" + _ul([
        "Public and private tenders are fragmented across PDFs, emails, and "
        "spreadsheets — cycle times of 60–120 days.",
        "Vendor onboarding is manual and paper-heavy, blocking SME access.",
        "Bid evaluation lacks auditability — compliance and legal risk.",
        "Cross-border tenders need multi-currency payments, KYC, and digital "
        "signatures — no incumbent bundles all three.",
    ])

    html += "<h1>3. Our Solution</h1>"
    html += ("<p>PMC Managers v2 collapses the entire tender pipeline into "
             "one role-aware portal with dynamic Approval Matrices, "
             "joint-signature escrow, and an AI compliance copilot.</p>")
    html += _ul([
        "Three role experiences: Admin, Vendor, Staff.",
        "Full lifecycle: Notice Board → Registration → Bidding → BOQ → "
        "Evaluation → Award → eSignature.",
        "Revenue built in: Product Catalog, Stripe checkout, Quote pipeline, "
        "Subscriptions.",
        "White-labeled, multi-tenant — ready for franchise deployment.",
    ])

    html += "<h1>4. Core Modules</h1>" + _table(
        ["Module", "Function"],
        [
            ["Notice Board", "Publish public tenders, RFPs, and RFQs"],
            ["Vendor Registration", "KYC-driven onboarding with document upload"],
            ["Package Tracker", "Real-time status of every tender package"],
            ["Bidding Management", "EMD payment, bid submission, envelope opening"],
            ["BOQ Builder", "Bill-of-Quantities with UNSPSC classification"],
            ["Evaluation &amp; Contracts", "Committee scoring, award, PO"],
            ["Vendor Intelligence", "Performance scoring and risk analytics"],
            ["Template Builder", "Reusable Tender / RFP / RFQ templates"],
            ["Joint-Signature Escrow", "Multi-party sign-off for high-value awards"],
            ["AI Audit Copilot", "LLM-powered clause and compliance review"],
        ])

    html += "<h1>5. Technology &amp; Architecture</h1>" + _table(
        ["Layer", "Technology"],
        [
            ["Frontend", "React (SPA), Tailwind, Shadcn UI"],
            ["Backend", "FastAPI (Python), async I/O"],
            ["Database", "MongoDB Atlas (managed)"],
            ["Compute", "AWS Elastic Beanstalk (Docker)"],
            ["CDN &amp; Static", "AWS S3 + CloudFront"],
            ["DNS &amp; SSL", "Route 53 + ACM"],
            ["AI Layer", "LLM Copilot for audit &amp; clause extraction"],
            ["Auth", "JWT + CSRF double-submit cookies"],
        ])

    html += "<h1>6. Third-Party Integrations</h1>" + _table(
        ["Service", "Purpose", "Status"],
        [
            ["DocuSign", "eSignature (JWT + Connect Webhook, HMAC)", "Live"],
            ["Stripe", "Payments, subscriptions, catalog", "Live"],
            ["AI Copilot", "Tender audit &amp; clause analysis", "Live"],
            ["KYC provider", "Vendor identity verification", "Pluggable"],
            ["Resend", "Transactional email", "Configured"],
            ["Firebase / APNs", "Push notifications", "Pluggable"],
            ["Zoom / Jitsi", "Pre-bid meetings", "Ready"],
            ["PayPal / Kaspi", "Regional payments", "Pluggable"],
        ])

    html += "<h1>7. Security &amp; Compliance</h1>" + _ul([
        "HTTPS end-to-end via ACM certificates on CloudFront and EB.",
        "CSRF double-submit cookie on every state-changing route.",
        "DocuSign Connect webhooks verified with HMAC signatures.",
        "Password rotation flow and admin change-password API in place.",
        "MongoDB Atlas with IP allow-lists, TLS, and encryption-at-rest.",
        "Git history purged of vendor branding for IP-clean investor review.",
    ])

    html += "<h1>8. Production Deployment</h1>"
    html += ("<p>The platform is live at "
             "<strong>https://www.pmcmanagers.com</strong> on a fully owned "
             "AWS footprint under the pmcmanagers.com domain. Every layer — "
             "compute, storage, DNS, and certificates — is under direct "
             "customer control.</p>")
    html += _table(["Component", "Value"], [
        ["Live URL", "https://www.pmcmanagers.com"],
        ["Frontend", "AWS S3 + CloudFront (SPA)"],
        ["Backend", "AWS Elastic Beanstalk (Docker)"],
        ["Database", "MongoDB Atlas (managed)"],
        ["Domain / SSL", "Route 53 + ACM (auto-renew)"],
    ])

    html += "<h1>9. Engineering Effort Snapshot</h1>" + _table(
        ["Dimension", "Delivered"],
        [
            ["Distinct modules", "10+ core enterprise modules"],
            ["User roles", "3 (Admin, Vendor, Staff) with granular RBAC"],
            ["Backend API surface", "60+ REST endpoints under /api/v1"],
            ["Frontend components", "80+ React components + Shadcn UI kit"],
            ["Third-party integrations", "8 live or plug-ready"],
            ["Deployment environments", "Preview + Production (AWS)"],
            ["Documentation", "39-page spec + PRD + Anchor + Manuals"],
            ["Security controls", "CSRF, JWT, HMAC webhooks, TLS, IP allow-list"],
        ])

    html += "<h1>10. Monetization Model</h1>" + _ul([
        "Vendor subscriptions (tiered) — recurring MRR via Stripe.",
        "Transaction fee on EMD deposits and awarded contracts.",
        "Enterprise white-label licenses for governments and franchisees.",
        "Value-added services: KYC packs, AI audit reports, template library.",
    ])

    html += "<h1>11. Roadmap</h1>" + _table(["Priority", "Item"], [
        ["P1", "UNSPSC picker in BOQ Builder &amp; Vendor Registration"],
        ["P2", "Investor Analytics Dashboard (live KPI board)"],
        ["P2", "PayPal &amp; Kaspi Pay live-mode activation"],
        ["P2", "Firebase / APNs push notifications"],
        ["P2", "Live KYC provider onboarding"],
        ["P3", "Mobile companion app (React Native)"],
    ])

    html += "<h1>12. The Ask</h1>"
    html += ("<p><strong>We invite investment to accelerate go-to-market, "
             "activate live regional payment rails, and scale into government "
             "and enterprise procurement. The product is built, deployed, and "
             "revenue-ready — the runway ahead is distribution.</strong></p>")
    html += ("<p style='text-align:center;font-style:italic;margin-top:20mm;'>"
             "Contact: PMC Managers Limited &middot; www.pmcmanagers.com</p>")

    path = OUT / "PMC_Investor_Deck.pdf"
    HTML(string=f"<html><head><meta charset='utf-8'></head><body>{html}</body></html>") \
        .write_pdf(str(path), stylesheets=[CSS(string=CSS_STYLE)])
    return path


def build_trainee_pdf():
    html = _cover_html(
        "PMC Managers Portal",
        "Trainee Handbook — From Zero to Confident User",
        "A step-by-step, screen-by-screen walkthrough of the entire portal."
    )
    html += "<h1>Welcome!</h1>"
    html += ("<p>This handbook takes you through the PMC Managers portal "
             "exactly as you will see it. Read each chapter in order — by "
             "the end you will be able to log in, navigate every module, "
             "publish a tender, review a bid, and send an award for "
             "signature.</p>"
             "<div class='callout'>Estimated self-training time: "
             "4–6 hours across 2 days.</div>")

    html += "<h1>Chapter 1 — Before You Start</h1>" + _ul([
        "A modern browser (Chrome, Edge, or Firefox — latest version).",
        "A stable internet connection.",
        "Your login credentials (provided by your admin).",
        "This handbook open on a second screen or printed alongside you.",
    ])
    html += "<p><strong>Portal URL: https://www.pmcmanagers.com</strong></p>"

    html += "<h1>Chapter 2 — Logging In</h1>"
    html += "<p><strong>Step-by-step:</strong></p>" + _ul([
        "Open https://www.pmcmanagers.com in your browser.",
        "Click the “Login” button at the top-right of the landing page.",
        "You will land on the unified <code>/login</code> screen.",
        "Enter the email address given to you (all lowercase).",
        "Enter your temporary password.",
        "Click “Sign in”.",
        "On first login you will be prompted to change your password — "
        "use at least 12 characters with mixed types.",
        "You land on the dashboard matching your role (Admin / Staff / Vendor).",
    ])
    html += "<p><strong>Troubleshooting:</strong></p>" + _ul([
        "Forgot password → click “Forgot password” on the login screen.",
        "Locked out after 5 failed attempts → wait 15 minutes or contact "
        "adminsupport@pmcmanagers.com.",
        "Blank screen → hard refresh (Ctrl + Shift + R).",
    ])

    html += "<h1>Chapter 3 — The Dashboard at a Glance</h1>"
    html += ("<p>The dashboard is your control tower. Every trainee should "
             "be able to name each region before moving on.</p>")
    html += _table(["Region", "What it shows"], [
        ["Top navigation bar", "Logo, module tabs, notifications, profile"],
        ["Left sidebar", "Quick links to modules (collapses on mobile)"],
        ["Main panel", "The active module's content"],
        ["KPI cards", "Live tenders, open bids, pending approvals"],
        ["Activity feed", "Recent actions across your organization"],
        ["Profile menu", "Change password, log out, switch tenant"],
    ])

    html += "<h1>Chapter 4 — Notice Board</h1>"
    html += "<p>The Notice Board is the public face of every tender.</p>"
    html += "<p><strong>Practise these tasks:</strong></p>" + _ul([
        "Open the Notice Board tab.",
        "Filter tenders by status: Open, Closing Soon, Closed, Awarded.",
        "Click any tender card to see its full brief.",
        "Locate the “Download RFP” button.",
        "Note the closing date and EMD amount.",
    ])

    html += "<h1>Chapter 5 — Vendor Registration</h1>"
    html += ("<p>This is how new suppliers onboard. Walk through each of "
             "the three sections so you can guide a vendor over the phone.</p>")
    html += _ul([
        "<strong>Section A</strong> — Company details: legal name, tax ID, address.",
        "<strong>Section B</strong> — Documents: incorporation, tax, bank letter (PDF/JPG &lt; 10 MB).",
        "<strong>Section C</strong> — UNSPSC categories for goods/services supplied.",
        "Submit — the vendor moves into KYC review status.",
    ])
    html += ("<div class='callout'>Admin action: approve or return-for-"
             "correction from the Vendor Management panel.</div>")

    html += "<h1>Chapter 6 — Package Tracker</h1>"
    html += "<p>Every tender is a “package”. The tracker shows exactly which stage each package is in.</p>"
    html += _ul([
        "Open Package Tracker.",
        "Read the horizontal stepper: Draft → Published → Bidding → Evaluation → Award → Signed.",
        "Click a package to drill into documents, bidders, and status history.",
    ])

    html += "<h1>Chapter 7 — Bidding Management</h1>"
    html += "<p><strong>Vendor flow:</strong></p>" + _ul([
        "Open a tender from the Notice Board.",
        "Click “Submit Bid”.",
        "Pay EMD via Stripe (sandbox card 4242 4242 4242 4242).",
        "Upload technical + commercial envelopes.",
        "Confirm submission — you receive a unique Bid ID.",
    ])
    html += "<p><strong>Admin flow:</strong></p>" + _ul([
        "Open Bidding Management → select the tender.",
        "Wait until the closing time, then click “Open Envelopes”.",
        "Review each bid; scores are entered in the Evaluation module.",
    ])

    html += "<h1>Chapter 8 — BOQ Builder</h1>" + _ul([
        "Open BOQ Builder inside the tender you are drafting.",
        "Click “+ Add Line Item”.",
        "Enter description, unit, quantity, and rate.",
        "Attach the correct UNSPSC code from the picker.",
        "Save — totals auto-calculate.",
        "Export the BOQ as PDF or Excel using the top-right menu.",
    ])

    html += "<h1>Chapter 9 — Evaluation &amp; Contracts</h1>" + _ul([
        "Open Evaluation → pick the tender.",
        "Enter technical scores for each bidder (0–100).",
        "Enter commercial scores — the system computes the weighted total.",
        "The top-ranked bidder is highlighted.",
        "Click “Award” — a draft Award Letter and PO are generated.",
    ])

    html += "<h1>Chapter 10 — Awards &amp; Digital Signature</h1>"
    html += ("<p>This is where PMC differentiates itself — award documents "
             "can be sent for legally binding e-signature directly from "
             "the portal.</p>")
    html += _ul([
        "Open Awards → pick the awarded tender.",
        "Preview the Award Letter and Purchase Order documents.",
        "Click “Send for Signature” on the document card.",
        "Choose delivery method: <strong>Embedded</strong> (in-browser) or Email.",
        "For the investor demo, always use Embedded — sandbox blocks external emails.",
        "Recipient signs; status auto-updates via DocuSign webhook.",
    ])

    html += "<h1>Chapter 11 — AI Audit Copilot</h1>" + _ul([
        "Open any tender document.",
        "Click the “AI Audit” button on the toolbar.",
        "The copilot summarises the document, flags risky clauses, and suggests improvements.",
        "Copy the suggestions into your evaluation notes.",
    ])

    html += "<h1>Chapter 12 — Vendor Intelligence</h1>" + _ul([
        "Open Vendor Intelligence.",
        "Search a vendor by name or tax ID.",
        "Review their performance score, past awards, and risk flags.",
        "Use this before shortlisting on high-value tenders.",
    ])

    html += "<h1>Chapter 13 — Profile &amp; Security</h1>" + _ul([
        "Click your avatar in the top-right corner.",
        "Choose “Change Password” — enter old + new password.",
        "Enable “Notification Preferences” to control email alerts.",
        "Always log out on shared computers.",
    ])

    html += "<h1>Chapter 14 — Trainee Daily Checklist</h1>" + _ul([
        "Log in and skim the KPI cards.",
        "Check pending vendor approvals.",
        "Review tenders closing within 48 hours.",
        "Confirm no bids are stuck in “Awaiting Envelope Open”.",
        "Verify DocuSign envelopes have refreshed status.",
        "Log any anomaly in the internal ticket tool before leaving.",
    ])

    html += "<h1>Chapter 15 — Glossary</h1>" + _table(
        ["Term", "Meaning"],
        [
            ["Tender", "A formal invitation to submit an offer"],
            ["RFP", "Request for Proposal"],
            ["RFQ", "Request for Quotation"],
            ["EMD", "Earnest Money Deposit"],
            ["BOQ", "Bill of Quantities"],
            ["UNSPSC", "United Nations Standard Products &amp; Services Code"],
            ["KYC", "Know Your Customer verification"],
            ["PO", "Purchase Order"],
            ["Envelope", "Sealed set of bid documents (technical / commercial)"],
        ])

    html += "<h1>You Are Ready!</h1>"
    html += ("<p><em>Complete Chapters 1–10 in your first sitting. Practise "
             "Chapters 11–14 in the sandbox environment before touching "
             "production data. When in doubt — ask, don't guess.</em></p>"
             "<p style='text-align:center;font-weight:bold;color:#0B2E4F;"
             "font-size:14pt;margin-top:12mm;'>"
             "Welcome to the PMC Managers team.</p>")

    path = OUT / "PMC_Trainee_Manual.pdf"
    HTML(string=f"<html><head><meta charset='utf-8'></head><body>{html}</body></html>") \
        .write_pdf(str(path), stylesheets=[CSS(string=CSS_STYLE)])
    return path


if __name__ == "__main__":
    results = [
        build_investor_docx(),
        build_investor_pdf(),
        build_trainee_docx(),
        build_trainee_pdf(),
    ]
    for r in results:
        size = os.path.getsize(r) / 1024
        print(f"✓ {r}  ({size:.1f} KB)")
