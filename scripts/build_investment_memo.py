"""
PMC Managers Limited — Investment Memorandum generator.

Produces four deliverables in one run:
  1. PMC_Investment_Memorandum_v1.pdf   (~20-page long-form IM)
  2. PMC_Investment_Memorandum_v1.docx  (editable Word version of #1)
  3. PMC_Pitch_Deck_v1.pdf              (landscape, 14 slides)
  4. PMC_Public_Snapshot_v1.pdf         (5-page public summary)

Numbers (financials, projections, cap table) are intentionally left as
clearly-marked "[TO BE FILLED]" placeholders — PMC will send figures.

Legal entity: THE PMC MANAGERS LTD · Company No. 17031540
Incorporated 13 Feb 2026, London UK.
"""
import os
from datetime import date
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.colors import HexColor
from reportlab.lib.units import mm
from docx import Document
from docx.shared import Pt, RGBColor, Inches, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

# ---------- Brand ----------
NAVY  = HexColor("#0F3B2E")   # forest-green primary
INK   = HexColor("#14261F")   # near-black navy
GOLD  = HexColor("#7A5F1E")   # brass accent
CREAM = HexColor("#F3EFE4")   # paper tone
MUTED = HexColor("#4F5C55")
LINE  = HexColor("#C9C1AA")

DOCX_NAVY  = RGBColor(0x0F, 0x3B, 0x2E)
DOCX_GOLD  = RGBColor(0x7A, 0x5F, 0x1E)
DOCX_INK   = RGBColor(0x14, 0x26, 0x1F)
DOCX_MUTED = RGBColor(0x4F, 0x5C, 0x55)

OUT_DIR = "/app/frontend/public/downloads"
os.makedirs(OUT_DIR, exist_ok=True)

TODAY = date.today().strftime("%d %b %Y")

LEGAL_HEADER = ("THE PMC MANAGERS LTD · Company No. 17031540 · "
                "Incorporated 13 February 2026")
REG_ADDR     = ("Office Gold, Building 7, Floor 5, Chiswick Park, "
                "566 Chiswick High Road, London, United Kingdom, W4 5YG")
TAGLINE      = "The procurement operating system for the next decade."

# ================================================================
# CORE CONTENT — single source of truth, reused across all 4 docs.
# ================================================================

ONE_LINER = (
    "PMC Managers is a full-stack procurement operating system that gives "
    "buyers, suppliers and auditors one trusted place to run tenders — from "
    "notice to award to escrow release — with every click on the audit ledger."
)

EXECUTIVE_SUMMARY = [
    ("Who we are",
     "THE PMC MANAGERS LTD (UK, Co. No. 17031540) operates PMC Managers — a "
     "cloud-native procurement platform that replaces fragmented email, "
     "spreadsheet and PDF-based tendering with a single auditable workflow. "
     "The platform is live, with vendor registrations, tender notices, bid "
     "submissions, EMD escrow, reverse auctions, DocuSign-based award "
     "signing and multi-role approvals all operating end-to-end."),
    ("What we solve",
     "Global public and private procurement runs on brittle processes: PDF "
     "RFPs mailed around, EMDs lost in bank reconciliations, bid comparison "
     "done on spreadsheets, and audit trails recreated after the fact. The "
     "result is a well-documented set of failures — unqualified vendors, "
     "price collusion, EMD float opacity, award disputes, and a procurement "
     "cycle that is 3–6× longer than it needs to be."),
    ("What we built",
     "A unified portal with four role surfaces (public notice board, vendor "
     "portal, staff portal, admin console), each wired into a single event "
     "ledger. Every notice, bid, payment, decision and signature is captured "
     "immutably. The platform ships with a reverse-auction engine, joint-"
     "signature escrow accounts, AI tender drafting, document builder, "
     "sanctions/KYC checks, and a role-based approval matrix."),
    ("Why now",
     "Three forces converge in 2026: (i) procurement digitisation mandates "
     "across OECD and emerging economies, (ii) demand for auditable supply "
     "chains after post-2024 compliance scandals, and (iii) buyers finally "
     "willing to pay SaaS prices for workflows historically bought as "
     "one-off IT projects. We are building the Shopify of regulated "
     "procurement — one platform, every tender, every geography."),
    ("The ask",
     "We are raising across pre-seed, seed, Series A and strategic tracks "
     "concurrently. See the Investment Ask section for stage-appropriate "
     "tickets, use-of-funds, milestones and expected returns."),
]

PROBLEM_POINTS = [
    ("Fragmentation",
     "A single tender today touches 7–12 disconnected systems: email, bank "
     "wires, Excel comparison, DocuSign, PDF bid docs, physical lockers for "
     "sealed envelopes, WhatsApp with vendors, and an auditor spreadsheet "
     "built after the award."),
    ("Opacity",
     "EMD and performance guarantees sit in idle accounts with no "
     "transparency to either side. Public buyers cannot prove compliance; "
     "private vendors cannot predict refunds. In our pilot buyer "
     "conversations, every single one had an open EMD dispute."),
    ("Trust gap",
     "Collusion, bid rigging and favouritism are reputational time-bombs. "
     "There is no credible neutral platform where every action — a notice "
     "tweak, an envelope open, a bid rejection — is logged with the "
     "operator's identity and timestamp."),
    ("Cycle time",
     "Comparable tenders close in 90–180 days in the current manual world. "
     "Benchmarks from digitised peers (BrazilCompras, SF City Hall) suggest "
     "40–60 days is achievable with the right workflow. That compression "
     "alone is tens of millions of USD saved per large buyer per year."),
    ("Compliance drift",
     "Approval matrices live in HR policies and spreadsheets, not systems. "
     "When auditors arrive, teams reconstruct who-approved-what from email "
     "threads. Every quarter one tender fails this test — and the next "
     "procurement officer bears the blame."),
]

SOLUTION_PILLARS = [
    ("One platform, four portals",
     "Public notice board for citizens and bidders. Vendor portal for "
     "registration, bidding and tracking. Staff portal for Legal, Escrow, "
     "Certifier, Accounting, Committee. Admin console for the procurement "
     "team. All reading from the same event log."),
    ("The audit ledger is the product",
     "Every state transition — notice drafted, published, bid submitted, "
     "EMD paid, envelope opened, award signed — writes to an immutable "
     "ledger with user id, role, timestamp, IP, and before/after diff. "
     "Exportable to auditors and regulators in one click."),
    ("Joint-signature escrow for EMDs",
     "Instead of trusting a bank reconciliation after the fact, EMDs land "
     "in joint escrow accounts operated by a PMC officer and the escrow-"
     "institution officer. Both must sign every release. The ledger makes "
     "disputes a 60-second investigation, not a 60-day one."),
    ("Reverse auctions, built in",
     "Live descending-price auctions with anti-sniping, floor prices and "
     "role-based observer seats. Admins invite bidders by email with "
     "unique join tokens; vendors register in two clicks; the auction "
     "closes when the floor is met or the clock runs out."),
    ("AI where it matters",
     "AI drafts tender notices from a brief, extracts BOQs from supplier "
     "quotes, screens bids against the spec, and highlights anomalies "
     "(e.g. a price 1.5× the budget estimate). Humans decide; AI removes "
     "the drudgery."),
    ("Rights are a first-class citizen",
     "A role-based permissions matrix governs every screen. Vendors see "
     "their own bids; committee members see sealed envelopes only after "
     "the deadline; auditors read the ledger but cannot write to it. "
     "Multi-tenant from day one — each buyer gets a logical slice of "
     "the platform."),
]

PRODUCT_MODULES = [
    ("Notice Board",
     "Public, mobile-first, SEO-indexed listing of every tender. Filter by "
     "category, country, buyer, deadline. Downloadable PDFs and "
     "machine-readable JSON feeds for aggregators."),
    ("Vendor Portal",
     "Five-section registration (Identity, Contact, Banking, Business "
     "Profile, Declarations) with document upload, KYC check and "
     "tenant-scoped admin approval. Bid tracker, My Bids, EMD history, "
     "Award letters, DocuSign signing in-portal."),
    ("Tender Builder",
     "AI-assisted draft of the full tender dossier — scope, BOQ, "
     "eligibility, EMD rules, approval matrix. Templates library. "
     "Corrigendum workflow with mandatory audit trail."),
    ("Bidding Ops",
     "Live pipeline of every bid moving through EMD → Escrow → Admin "
     "approval → Certifier → Legal → Accounting → Committee. Bulk EMD "
     "reminders, hold / resume, flag to certifier."),
    ("Escrow & EMD",
     "Joint escrow accounts with dual-signature releases. Inbound-receipt "
     "ledger, mandatory countersign on every withdrawal, printable "
     "statements for auditors."),
    ("Reverse Auctions",
     "Admin configures starting price, floor, duration, bid decrement. "
     "Invites vendors by email with unique join tokens. Live countdown, "
     "anti-sniping extension, winner-takes-all or shortlist modes."),
    ("Awards & DocuSign",
     "L1 comparison engine, award recommendation, Letter-of-Intent and "
     "contract generation, DocuSign envelope orchestration end-to-end. "
     "Awarded vendor sees the contract in their portal."),
    ("Reports & Audit",
     "Role-scoped dashboards, exportable audit ledger (CSV, JSON, PDF), "
     "SLA compliance reports, EMD float snapshots, vendor performance "
     "scorecards."),
    ("Masters & Governance",
     "Approval matrices, legal-entity types, categories, countries, "
     "currencies, document templates — all editable without redeploying."),
]

MARKET = [
    ("TAM",
     "Global B2G and large-enterprise procurement spend is approximately "
     "USD 13 trillion annually. Procurement software spend is approximately "
     "USD 9 billion annually and growing at approximately 11% CAGR. "
     "[Sources: McKinsey, Gartner, EBRD; final figures to be verified by "
     "PMC's analyst]."),
    ("SAM",
     "Mid-size public buyers and large enterprises running >50 tenders a "
     "year across emerging markets, EU and ANZ — approximately USD 1.6 "
     "billion of annual procurement-SaaS budget addressable in the next "
     "five years."),
    ("SOM (Year 1–3)",
     "Kazakhstan and 4 adjacent CIS/MENA markets with 300+ qualifying "
     "buyers, a landed-average contract value of USD 36K/year — a "
     "beachhead of USD 10M+ ARR achievable at ~25% penetration."),
    ("Market timing",
     "Public-procurement digitisation mandates are in force in 60+ "
     "countries (UN SDG 16.6 reporting). Enterprises are post-ERP: they "
     "have SAP/Oracle for finance but no system of record for tenders. "
     "Audit regulators are now rejecting PDF-and-email evidence."),
]

BUSINESS_MODEL = [
    ("Platform subscription",
     "Buyer SaaS seats, billed annually. Tiered by number of concurrent "
     "tenders, users and modules enabled."),
    ("Transaction fees",
     "Fixed percentage on EMD transit (payable by the vendor, included "
     "in bid price) and on award value above a threshold."),
    ("Escrow float",
     "Interest on the pooled EMD held in joint accounts (regulated, "
     "jurisdiction-dependent; disclosed up-front in Terms)."),
    ("Vendor premium",
     "Verified-vendor badge, auto-matched tender alerts, priority "
     "support — SaaS billed to vendors who derive measurable value "
     "from the matching."),
    ("Professional services",
     "Buyer onboarding, bespoke approval-matrix setup, auditor training. "
     "Capped at approximately 15% of total revenue so SaaS economics "
     "stay dominant."),
    ("Compliance exports",
     "White-labelled regulator feeds (court-admissible ledger extracts) "
     "sold on API usage to oversight bodies."),
]

MOAT = [
    ("Audit ledger as single source of truth",
     "Not a feature — the architectural core. Competitors retrofit "
     "logs onto CRUD apps; our write path is log-first. Switching "
     "cost for a buyer who has run 200 tenders through our ledger "
     "is enormous."),
    ("Multi-tenant from day one",
     "Every record carries a tenant_id. Buyers never share rows. "
     "Lets us land one tender authority and expand across its "
     "departments without re-architecting."),
    ("Role matrix × approval matrix",
     "Six staff roles × bid pipeline × approval rules = a "
     "combinatorial space most procurement products never fully "
     "model. We have."),
    ("Document rendering pipeline",
     "WeasyPrint + reportlab + DocuSign — same stack produces the "
     "public notice PDF, the LoA, the escrow statement, and the "
     "audit export. One rendering layer, dozens of document types."),
    ("Live reverse-auction engine",
     "Non-trivial engineering — anti-sniping, dual-side timers, "
     "integrity under tab close. A fast-follower would need 6+ "
     "months of game-day hardening to catch up."),
    ("Regulated-escrow design",
     "Joint-signature account model is bank-friendly and auditor-"
     "friendly. We can plug into local banks per market without "
     "becoming a payment institution ourselves."),
]

TRACTION = [
    "Platform live end-to-end: notice drafting → publication → bid "
    "intake → EMD escrow → award → DocuSign signing — all in production.",
    "4 role surfaces (Public / Vendor / Staff / Admin) and 20+ admin "
    "console modules shipped.",
    "Reverse-auction engine shipped, with vendor invites via Resend, "
    "live rooms, aliased bidding, and anti-sniping.",
    "Audit ledger covers every state transition across notices, bids, "
    "approvals, escrow signatures, awards and user admin events.",
    "AI tender drafting + document extraction integrated via Emergent "
    "LLM gateway (model-portable: Claude Sonnet, Gemini, GPT families).",
    "Multi-tenant architecture live; every record is tenant-scoped.",
    "Deployment pipeline: S3 + CloudFront frontend, Elastic Beanstalk "
    "backend, MongoDB Atlas — zero-downtime releases shipping on a "
    "~weekly cadence.",
    "Operational for user adminsupport@pmcmanagers.com and pilot "
    "vendors on the live www.pmcmanagers.com environment.",
]

ROADMAP = [
    ("Next 90 days",
     "First 3 paying buyers in Kazakhstan. Mobile vendor app. "
     "Direct bank-API escrow (Halyk, Sberbank-KZ). Published public "
     "notice-board SEO."),
    ("Months 4–9",
     "Expand to UAE and Georgia. Add ESG & sustainability scoring "
     "module. Second-generation reverse auction (sealed-bid + "
     "price-only variants). SOC2 Type I."),
    ("Months 10–18",
     "EU / UK expansion with GDPR-DPIA pack and ISO 27001. White-label "
     "offering for tender authorities. Vendor-financing marketplace "
     "with regulated partners."),
    ("Months 19–36",
     "LATAM beachhead (Brazil / Mexico). Procurement data product "
     "(aggregated, anonymised market-price index). Reach USD 10M ARR."),
]

RISKS = [
    ("Regulatory",
     "Procurement laws vary by jurisdiction. Mitigation: launch in "
     "one jurisdiction fully licensed; expand with local counsel; "
     "escrow partners carry the regulated license."),
    ("Buyer sales cycle",
     "Public buyers can take 9–12 months to procure a procurement "
     "system. Mitigation: pilot-to-paid conversion motion; private-"
     "enterprise buyers as faster-close counterweight."),
    ("Vendor adoption",
     "Suppliers resist new portals. Mitigation: bulk CSV invite + "
     "pre-filled profile + no vendor-paid SaaS at entry (vendor "
     "premium is strictly opt-in)."),
    ("Trust & security",
     "A platform that writes to a legal-grade ledger must never "
     "lose data. Mitigation: append-only write path, daily snapshot "
     "to immutable storage, SOC2 roadmap, bug-bounty from day one."),
    ("Competition",
     "SAP Ariba, Coupa, Jaggaer, local Govt-Tech incumbents. "
     "Mitigation: our verticalised depth (escrow + reverse auction + "
     "audit ledger) is deeper than horizontal procurement suites; "
     "our SMB price point is below theirs; our emerging-markets "
     "focus is where they are weakest."),
]

TEAM = [
    ("Legal entity",
     "THE PMC MANAGERS LTD · Company No. 17031540 · "
     "Incorporated 13 February 2026 under the Companies Act 2006."),
    ("Registered office",
     "Office Gold, Building 7, Floor 5, Chiswick Park, "
     "566 Chiswick High Road, London, United Kingdom, W4 5YG."),
    ("Jurisdiction & governance",
     "English law; board governance per the Articles of Association. "
     "Investor rights documented in SHA on first priced round."),
    ("Founders & team",
     "[TO BE FILLED] — founder bios, titles and 1–2 line backgrounds "
     "to be inserted on finalisation."),
    ("Advisors",
     "[TO BE FILLED] — advisory board and specialist advisors."),
    ("Current headcount",
     "[TO BE FILLED] — core team, engineering, GTM, operations."),
]

ASK_BY_STAGE = [
    ("Pre-seed / Angel",
     "USD 250K – 750K · SAFE or priced convertible · "
     "Use of funds: first 3 enterprise buyers in Kazakhstan, mobile "
     "vendor app, Resend-based transactional email at scale, 2 GTM hires. "
     "Target milestones in 12 months: 10 buyers · USD 300K ARR · SOC2 "
     "readiness."),
    ("Seed",
     "USD 1M – 3M · Priced round · "
     "Use of funds: 8-person engineering team, 3-person GTM, ISO 27001 "
     "and SOC2 Type I, direct-bank escrow partnerships in 3 markets, "
     "expansion to UAE and Georgia. Target milestones in 18 months: "
     "40 buyers · USD 1.5M ARR · 500 verified vendors."),
    ("Series A",
     "USD 3M – 10M · Preferred shares · "
     "Use of funds: multi-geography GTM, EU/UK regulated launch, "
     "white-label offering for tender authorities, data-product "
     "spin-up, 25-person team. Target milestones in 24 months: "
     "120 buyers · USD 6M ARR · profitable unit economics at the "
     "contribution-margin level."),
    ("Strategic / corporate partner",
     "Partnership + minority investment · "
     "For banks (escrow), accounting firms (audit distribution), "
     "ERP vendors (procurement module OEM) and government-tech "
     "integrators. Shape: equity + revenue-share on co-sold "
     "deployments."),
]

FINANCIALS_PLACEHOLDER = [
    ("Revenue model (3-year)",
     "[TO BE FILLED] — Buyer SaaS seats, transaction fees, escrow "
     "float, vendor premium, services. Monthly cohort build."),
    ("Cost model",
     "[TO BE FILLED] — Payroll, infra (AWS + MongoDB Atlas + "
     "Resend + DocuSign), compliance, GTM."),
    ("Unit economics",
     "[TO BE FILLED] — CAC, Payback, ACV, LTV:CAC, Gross margin."),
    ("Cash runway",
     "[TO BE FILLED] — Opening balance, burn, runway at each "
     "stage of the raise."),
    ("Projections",
     "[TO BE FILLED] — Y1 ARR, Y2 ARR, Y3 ARR; Y3 EBITDA margin."),
]

CONTACT_LINES = [
    "THE PMC MANAGERS LTD · Company No. 17031540",
    "Office Gold, Building 7, Floor 5, Chiswick Park",
    "566 Chiswick High Road, London, United Kingdom, W4 5YG",
    "Web: www.pmcmanagers.com",
    "Email: adminsupport@pmcmanagers.com",
    "Investor relations: [TO BE FILLED]",
    "Document rev. " + TODAY,
]

# ================================================================
# PDF HELPERS
# ================================================================

def letterhead(c, w, h, title_small, title_big):
    c.setFillColor(NAVY); c.rect(0, h - 90, w, 90, stroke=0, fill=1)
    c.setFillColor(CREAM); c.setFont("Helvetica-Bold", 20)
    c.drawString(50, h - 45, "PMC Managers")
    c.setFont("Helvetica", 10)
    c.drawString(50, h - 62, title_small)
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8)
    c.drawString(50, h - 78, title_big)

def footer(c, w, h, pageno, total=None):
    c.setFillColor(GOLD); c.setFont("Helvetica", 7)
    c.drawString(50, 25, "THE PMC MANAGERS LTD · 17031540 · Strictly "
                 "confidential — do not reproduce without written consent.")
    c.setFillColor(MUTED)
    pg = f"Page {pageno}" + (f" of {total}" if total else "")
    c.drawRightString(w - 50, 25, pg)

def wrap_lines(text, max_chars):
    out = []
    for para in text.split("\n"):
        words = para.split()
        line = ""
        for wd in words:
            trial = (line + " " + wd).strip()
            if len(trial) <= max_chars:
                line = trial
            else:
                out.append(line); line = wd
        if line: out.append(line)
    return out

def wrap_block(c, x, y, text, max_chars, leading=14, font="Helvetica", size=10):
    c.setFont(font, size)
    for line in wrap_lines(text, max_chars):
        c.drawString(x, y, line); y -= leading
    return y

def h2(c, x, y, label, w, color=NAVY):
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 7)
    c.drawString(x, y, "SECTION")
    c.setFillColor(color); c.setFont("Helvetica-Bold", 14)
    c.drawString(x + 50, y, label)
    c.setStrokeColor(GOLD); c.setLineWidth(0.4); c.line(x, y - 4, w - 50, y - 4)
    return y - 22

def h3(c, x, y, label, color=NAVY):
    c.setFillColor(color); c.setFont("Helvetica-Bold", 11)
    c.drawString(x, y, label); return y - 14

# ================================================================
# 1 · LONG-FORM INVESTMENT MEMORANDUM (PDF)
# ================================================================

def build_memo_pdf(path):
    c = canvas.Canvas(path, pagesize=A4)
    w, h = A4
    c.setTitle("PMC Managers — Investment Memorandum"); c.setAuthor("THE PMC MANAGERS LTD")
    page = 1
    def next_page():
        nonlocal page
        footer(c, w, h, page); c.showPage(); page += 1

    # --- Cover ---
    c.setFillColor(NAVY); c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setFillColor(CREAM); c.setFont("Helvetica-Bold", 36)
    c.drawString(50, h - 160, "PMC Managers")
    c.setFont("Helvetica", 16); c.drawString(50, h - 190, TAGLINE)
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 10)
    c.drawString(50, h - 240, "INVESTMENT MEMORANDUM · " + TODAY.upper())
    c.setFillColor(CREAM); c.setFont("Helvetica", 10)
    y = 240
    for ln in CONTACT_LINES:
        c.drawString(50, y, ln); y -= 14
    c.setFillColor(GOLD); c.setFont("Helvetica", 7)
    c.drawString(50, 60, "Strictly private and confidential · for the exclusive use of the recipient.")
    c.showPage(); page += 1

    # --- Executive summary ---
    letterhead(c, w, h, "Executive summary", "INVESTMENT MEMORANDUM")
    y = h - 120
    c.setFillColor(INK); c.setFont("Helvetica-Oblique", 11)
    for ln in wrap_lines(ONE_LINER, 95): c.drawString(50, y, ln); y -= 14
    y -= 10
    for lbl, body in EXECUTIVE_SUMMARY:
        y = h3(c, 50, y, lbl)
        c.setFillColor(INK)
        y = wrap_block(c, 50, y, body, 95)
        y -= 8
        if y < 110: next_page(); letterhead(c, w, h, "Executive summary (cont.)", "INVESTMENT MEMORANDUM"); y = h - 120
    next_page()

    def section_page(title_small, chapter_label, items, is_bullet=False):
        nonlocal y
        letterhead(c, w, h, title_small, "INVESTMENT MEMORANDUM")
        y = h - 120
        y = h2(c, 50, y, chapter_label, w)
        for item in items:
            if is_bullet:
                c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 10); c.drawString(50, y, "•")
                c.setFillColor(INK)
                y = wrap_block(c, 65, y, item, 92)
                y -= 4
            else:
                lbl, body = item
                y = h3(c, 50, y, lbl)
                c.setFillColor(INK)
                y = wrap_block(c, 50, y, body, 95)
                y -= 8
            if y < 110:
                next_page()
                letterhead(c, w, h, title_small + " (cont.)", "INVESTMENT MEMORANDUM")
                y = h - 120
        next_page()

    y = 0  # reset
    section_page("The problem",        "01 · THE PROBLEM",        PROBLEM_POINTS)
    section_page("The solution",       "02 · THE SOLUTION",       SOLUTION_PILLARS)
    section_page("Product modules",    "03 · PRODUCT",            PRODUCT_MODULES)
    section_page("Market opportunity", "04 · MARKET",             MARKET)
    section_page("Business model",     "05 · BUSINESS MODEL",     BUSINESS_MODEL)
    section_page("Why we win",         "06 · MOAT",               MOAT)
    section_page("Traction",           "07 · TRACTION",           TRACTION, is_bullet=True)
    section_page("Roadmap",            "08 · ROADMAP",            ROADMAP)
    section_page("Team & governance",  "09 · TEAM",               TEAM)
    section_page("Investment ask",     "10 · THE ASK",            ASK_BY_STAGE)
    section_page("Financial outlook",  "11 · FINANCIALS",         FINANCIALS_PLACEHOLDER)
    section_page("Risks & mitigation", "12 · RISKS",              RISKS)

    # Contact page
    letterhead(c, w, h, "Contact & disclaimers", "INVESTMENT MEMORANDUM")
    y = h - 130
    y = h2(c, 50, y, "13 · CONTACT", w)
    c.setFillColor(INK); c.setFont("Helvetica", 11)
    for ln in CONTACT_LINES: c.drawString(50, y, ln); y -= 16
    y -= 20
    y = h3(c, 50, y, "Important notice")
    c.setFillColor(MUTED); c.setFont("Helvetica-Oblique", 9)
    disclaimer = (
        "This Investment Memorandum has been prepared by THE PMC MANAGERS "
        "LTD (the Company) for information purposes only. It does not "
        "constitute an offer or solicitation to purchase or subscribe for "
        "any securities. The information contained herein is proprietary "
        "and confidential; recipients agree, by accepting delivery of this "
        "document, not to copy, distribute or disclose any part of it "
        "without the prior written consent of the Company. Forward-looking "
        "statements are subject to risks and uncertainties and actual "
        "results may differ materially. Prospective investors should "
        "conduct their own due diligence and seek independent professional "
        "advice before making any investment decision."
    )
    y = wrap_block(c, 50, y, disclaimer, 95, leading=13, font="Helvetica-Oblique", size=9)
    footer(c, w, h, page)
    c.save()

# ================================================================
# 2 · PITCH DECK (PDF, landscape, 14 slides)
# ================================================================

def build_deck_pdf(path):
    c = canvas.Canvas(path, pagesize=landscape(A4))
    w, h = landscape(A4)
    c.setTitle("PMC Managers — Pitch Deck"); c.setAuthor("THE PMC MANAGERS LTD")

    def slide_bg():
        c.setFillColor(CREAM); c.rect(0, 0, w, h, stroke=0, fill=1)
        c.setFillColor(NAVY); c.rect(0, h - 30, w, 30, stroke=0, fill=1)
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 8)
        c.drawString(40, h - 20, "PMC MANAGERS · PITCH DECK")
        c.drawRightString(w - 40, h - 20, TODAY.upper())
        c.setFillColor(GOLD); c.setFont("Helvetica", 7)
        c.drawString(40, 20, "THE PMC MANAGERS LTD · 17031540 · Confidential")

    def title(x, y, big, small=""):
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 32)
        c.drawString(x, y, big)
        if small:
            c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 10)
            c.drawString(x, y + 36, small)

    def body_block(x, y, text, max_chars=70, size=14, leading=20):
        c.setFillColor(INK); c.setFont("Helvetica", size)
        for ln in wrap_lines(text, max_chars):
            c.drawString(x, y, ln); y -= leading
        return y

    def two_col_bullets(items):
        n = len(items)
        half = (n + 1) // 2
        for i, (lbl, body) in enumerate(items[:half]):
            y = h - 170 - i * 90
            c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 11)
            c.drawString(60, y, lbl.upper())
            body_block(60, y - 16, body, max_chars=55, size=10, leading=13)
        for i, (lbl, body) in enumerate(items[half:]):
            y = h - 170 - i * 90
            c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 11)
            c.drawString(w / 2 + 20, y, lbl.upper())
            body_block(w / 2 + 20, y - 16, body, max_chars=55, size=10, leading=13)

    def slide_num(n):
        c.setFillColor(MUTED); c.setFont("Helvetica", 8)
        c.drawRightString(w - 40, 20, f"{n:02d}")

    # 1 · Cover
    c.setFillColor(NAVY); c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setFillColor(CREAM); c.setFont("Helvetica-Bold", 56); c.drawString(60, h/2 + 20, "PMC Managers")
    c.setFont("Helvetica", 18); c.drawString(60, h/2 - 20, TAGLINE)
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 10)
    c.drawString(60, 80, "INVESTMENT & PARTNERSHIP DECK · " + TODAY.upper())
    c.setFillColor(CREAM); c.setFont("Helvetica", 9)
    c.drawString(60, 60, LEGAL_HEADER)
    c.showPage()

    # 2 · The one-liner
    slide_bg(); title(60, h - 110, "What we are")
    body_block(60, h - 160, ONE_LINER, max_chars=80, size=16, leading=24)
    slide_num(2); c.showPage()

    # 3 · The problem
    slide_bg(); title(60, h - 110, "The problem", "WHY PROCUREMENT IS BROKEN")
    two_col_bullets(PROBLEM_POINTS); slide_num(3); c.showPage()

    # 4 · The solution
    slide_bg(); title(60, h - 110, "Our solution", "ONE PLATFORM · ONE LEDGER")
    two_col_bullets(SOLUTION_PILLARS); slide_num(4); c.showPage()

    # 5 · Product modules
    slide_bg(); title(60, h - 110, "The product", "NINE MODULES · ONE EVENT LOG")
    cols = 3; rows = 3
    for i, (lbl, body) in enumerate(PRODUCT_MODULES[:9]):
        col = i % cols; row = i // cols
        x = 60 + col * ((w - 120) / cols); y = h - 170 - row * 150
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 10); c.drawString(x, y, lbl.upper())
        body_block(x, y - 16, body, max_chars=38, size=9, leading=12)
    slide_num(5); c.showPage()

    # 6 · Market
    slide_bg(); title(60, h - 110, "Market", "LARGE · UNDER-SERVED · DIGITISING NOW")
    for i, (lbl, body) in enumerate(MARKET):
        y = h - 170 - i * 110
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 11); c.drawString(60, y, lbl.upper())
        body_block(60, y - 16, body, max_chars=100, size=10, leading=13)
    slide_num(6); c.showPage()

    # 7 · Business model
    slide_bg(); title(60, h - 110, "Business model", "SIX REVENUE LINES")
    two_col_bullets(BUSINESS_MODEL); slide_num(7); c.showPage()

    # 8 · Moat
    slide_bg(); title(60, h - 110, "Why we win", "THE AUDIT LEDGER IS THE MOAT")
    two_col_bullets(MOAT); slide_num(8); c.showPage()

    # 9 · Traction
    slide_bg(); title(60, h - 110, "Traction today", "PLATFORM LIVE · WEEKLY RELEASES")
    for i, bp in enumerate(TRACTION):
        y = h - 170 - i * 44
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 14); c.drawString(60, y, "•")
        body_block(80, y, bp, max_chars=95, size=11, leading=15)
    slide_num(9); c.showPage()

    # 10 · Roadmap
    slide_bg(); title(60, h - 110, "Roadmap", "FROM BEACHHEAD TO USD 10M ARR")
    for i, (lbl, body) in enumerate(ROADMAP):
        y = h - 170 - i * 90
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 11); c.drawString(60, y, lbl.upper())
        body_block(60, y - 16, body, max_chars=100, size=10, leading=13)
    slide_num(10); c.showPage()

    # 11 · Team
    slide_bg(); title(60, h - 110, "Team & entity", "UK PLC · BUILT TO SCALE")
    for i, (lbl, body) in enumerate(TEAM):
        y = h - 170 - i * 70
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 11); c.drawString(60, y, lbl.upper())
        body_block(60, y - 16, body, max_chars=100, size=10, leading=13)
    slide_num(11); c.showPage()

    # 12 · Ask
    slide_bg(); title(60, h - 110, "The ask", "MULTI-TRACK · STAGE-APPROPRIATE")
    for i, (lbl, body) in enumerate(ASK_BY_STAGE):
        y = h - 170 - i * 100
        c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 11); c.drawString(60, y, lbl.upper())
        body_block(60, y - 16, body, max_chars=100, size=10, leading=13)
    slide_num(12); c.showPage()

    # 13 · Financials placeholder
    slide_bg(); title(60, h - 110, "Financials", "3-YEAR PLAN · NUMBERS INCOMING")
    body_block(60, h - 180,
               "This slide will hold the 3-year revenue build, cost model, "
               "unit economics (CAC, Payback, LTV:CAC), gross margin and "
               "cash-flow bridge. PMC team to send the figures.",
               max_chars=85, size=13, leading=18)
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 11)
    c.drawString(60, h - 300, "PLACEHOLDERS · TO BE FILLED")
    for i, (lbl, body) in enumerate(FINANCIALS_PLACEHOLDER):
        y = h - 320 - i * 36
        c.setFillColor(INK); c.setFont("Helvetica", 10)
        c.drawString(60, y, "• " + lbl + ": " + body)
    slide_num(13); c.showPage()

    # 14 · Contact
    slide_bg(); title(60, h - 110, "Let's talk", "")
    y = h - 180
    for ln in CONTACT_LINES:
        c.setFillColor(INK); c.setFont("Helvetica", 13)
        c.drawString(60, y, ln); y -= 22
    slide_num(14); c.showPage()
    c.save()

# ================================================================
# 3 · PUBLIC 5-PAGE SNAPSHOT (PDF)
# ================================================================

PUBLIC_INTRO = (
    "PMC Managers is a cloud platform that modernises how organisations run "
    "tenders. Instead of email threads, PDFs and spreadsheets, every notice, "
    "bid, payment and signature happens in one place — and everything is "
    "recorded on an audit trail that regulators, boards and auditors can "
    "trust. Operated by THE PMC MANAGERS LTD (UK, Co. No. 17031540)."
)

PUBLIC_SECTIONS = [
    ("What we do",
     "We run the end-to-end procurement workflow: publish the tender, "
     "collect vendor registrations, accept bids with sealed envelopes, "
     "hold the earnest money in joint escrow accounts, run reverse "
     "auctions where appropriate, and sign the award letter with "
     "DocuSign — all without leaving the platform."),
    ("Who we help",
     "Public authorities, state-owned enterprises, large private buyers, "
     "and the vendors who sell to them. The platform scales from a single "
     "department running 20 tenders a year to a national procurement "
     "authority running thousands."),
    ("What is different",
     "The audit ledger. Every click is permanently recorded. Buyers prove "
     "compliance in minutes, not weeks. Vendors see exactly where their "
     "bid is in the review pipeline. Auditors export the trail with a "
     "single click."),
    ("Where we are today",
     "The platform is live end-to-end with four role surfaces — public "
     "notice board, vendor portal, staff portal, and admin console. "
     "Reverse auctions, EMD escrow and DocuSign-based award signing all "
     "work in production. We ship improvements on a roughly weekly cadence."),
    ("How to engage",
     "Buyers can request a demo and pilot. Vendors can register for "
     "free and start receiving matched tender alerts. Partners (banks, "
     "accounting firms, ERP integrators) can co-sell or integrate via "
     "our APIs. See the contact details below."),
]

def build_snapshot_pdf(path):
    c = canvas.Canvas(path, pagesize=A4); w, h = A4
    c.setTitle("PMC Managers — 5-page Snapshot"); c.setAuthor("THE PMC MANAGERS LTD")

    # Page 1 — cover
    c.setFillColor(NAVY); c.rect(0, 0, w, h, stroke=0, fill=1)
    c.setFillColor(CREAM); c.setFont("Helvetica-Bold", 42)
    c.drawString(50, h - 180, "PMC Managers")
    c.setFont("Helvetica", 15); c.drawString(50, h - 215, TAGLINE)
    c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 10)
    c.drawString(50, h - 260, "PUBLIC SNAPSHOT · " + TODAY.upper())
    c.setFillColor(CREAM); c.setFont("Helvetica", 10)
    y = 200
    for ln in CONTACT_LINES[:5]: c.drawString(50, y, ln); y -= 14
    c.setFillColor(GOLD); c.setFont("Helvetica", 7)
    c.drawString(50, 50, "A plain-language snapshot — details for buyers, vendors and partners.")
    c.showPage()

    # Page 2–5: intro + four sections, one per page = 5 total
    pages = [("What we are", PUBLIC_INTRO, None)] + \
            [(lbl, body, None) for lbl, body in PUBLIC_SECTIONS]
    for i, (title_label, body, _) in enumerate(pages):
        letterhead(c, w, h, title_label, "PUBLIC SNAPSHOT · " + ("Page " + str(i + 2)))
        y = h - 130
        c.setFillColor(NAVY); c.setFont("Helvetica-Bold", 20); c.drawString(50, y, title_label)
        y -= 30
        c.setFillColor(INK); c.setFont("Helvetica", 12)
        for ln in wrap_lines(body, 85): c.drawString(50, y, ln); y -= 18
        y -= 10
        if i == 0:
            # Add a mini-features band under the intro
            c.setFillColor(GOLD); c.setFont("Helvetica-Bold", 9)
            c.drawString(50, y, "AT A GLANCE"); y -= 16
            glance = [
                "Public notice board + vendor portal + staff + admin — one platform",
                "Joint-signature EMD escrow with dual-sign releases",
                "Live reverse auctions with anti-sniping",
                "DocuSign-based award letters and contracts",
                "Full audit ledger — every action, every user, exportable",
                "Multi-tenant, multi-country, multi-currency from day one",
            ]
            c.setFillColor(INK); c.setFont("Helvetica", 11)
            for g in glance: c.drawString(60, y, "·  " + g); y -= 15
        footer(c, w, h, i + 2)
        c.showPage()

    c.save()

# ================================================================
# 4 · EDITABLE WORD VERSION OF THE MEMO (DOCX)
# ================================================================

def _shade(cell, hex_color):
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear"); shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tc_pr.append(shd)

def _style_runs(para, size, bold=False, italic=False, color=None, align=None):
    for r in para.runs:
        r.font.name = "Calibri"
        r.font.size = Pt(size); r.bold = bold; r.italic = italic
        if color: r.font.color.rgb = color
    if align is not None: para.alignment = align

def build_memo_docx(path):
    doc = Document()
    # Page margins
    for s in doc.sections:
        s.top_margin = Cm(2); s.bottom_margin = Cm(2)
        s.left_margin = Cm(2.2); s.right_margin = Cm(2.2)

    # Cover
    p = doc.add_paragraph("PMC MANAGERS")
    _style_runs(p, 36, bold=True, color=DOCX_NAVY, align=WD_ALIGN_PARAGRAPH.LEFT)
    p = doc.add_paragraph(TAGLINE); _style_runs(p, 16, italic=True, color=DOCX_INK)
    p = doc.add_paragraph("INVESTMENT MEMORANDUM · " + TODAY.upper())
    _style_runs(p, 10, bold=True, color=DOCX_GOLD)
    doc.add_paragraph("")
    for ln in CONTACT_LINES:
        p = doc.add_paragraph(ln); _style_runs(p, 10, color=DOCX_INK)
    p = doc.add_paragraph("Strictly private and confidential — for the exclusive use of the recipient.")
    _style_runs(p, 8, italic=True, color=DOCX_GOLD)
    doc.add_page_break()

    def section(title_label, chapter_number, items, is_bullet=False):
        p = doc.add_paragraph(f"{chapter_number} · {title_label.upper()}")
        _style_runs(p, 16, bold=True, color=DOCX_NAVY)
        if is_bullet:
            for body in items:
                p = doc.add_paragraph(body, style="List Bullet"); _style_runs(p, 11, color=DOCX_INK)
        else:
            for lbl, body in items:
                p = doc.add_paragraph(lbl); _style_runs(p, 12, bold=True, color=DOCX_GOLD)
                p = doc.add_paragraph(body); _style_runs(p, 11, color=DOCX_INK)
        doc.add_paragraph("")

    p = doc.add_paragraph("Executive summary")
    _style_runs(p, 18, bold=True, color=DOCX_NAVY)
    p = doc.add_paragraph(ONE_LINER); _style_runs(p, 11, italic=True, color=DOCX_INK)
    for lbl, body in EXECUTIVE_SUMMARY:
        p = doc.add_paragraph(lbl); _style_runs(p, 12, bold=True, color=DOCX_GOLD)
        p = doc.add_paragraph(body); _style_runs(p, 11, color=DOCX_INK)
    doc.add_page_break()

    section("The problem",        "01", PROBLEM_POINTS)
    section("The solution",       "02", SOLUTION_PILLARS)
    section("Product modules",    "03", PRODUCT_MODULES)
    section("Market opportunity", "04", MARKET)
    section("Business model",     "05", BUSINESS_MODEL)
    section("Why we win",         "06", MOAT)
    section("Traction",           "07", TRACTION, is_bullet=True)
    section("Roadmap",            "08", ROADMAP)
    section("Team & governance",  "09", TEAM)
    section("Investment ask",     "10", ASK_BY_STAGE)
    section("Financial outlook",  "11", FINANCIALS_PLACEHOLDER)
    section("Risks & mitigation", "12", RISKS)

    p = doc.add_paragraph("13 · CONTACT"); _style_runs(p, 16, bold=True, color=DOCX_NAVY)
    for ln in CONTACT_LINES:
        p = doc.add_paragraph(ln); _style_runs(p, 11, color=DOCX_INK)
    doc.add_paragraph("")
    p = doc.add_paragraph("Important notice"); _style_runs(p, 12, bold=True, color=DOCX_GOLD)
    disclaimer = (
        "This Investment Memorandum has been prepared by THE PMC MANAGERS "
        "LTD (the Company) for information purposes only. It does not "
        "constitute an offer or solicitation to purchase or subscribe for "
        "any securities. The information contained herein is proprietary "
        "and confidential; recipients agree, by accepting delivery of this "
        "document, not to copy, distribute or disclose any part of it "
        "without the prior written consent of the Company. Forward-looking "
        "statements are subject to risks and uncertainties and actual "
        "results may differ materially. Prospective investors should "
        "conduct their own due diligence and seek independent professional "
        "advice before making any investment decision."
    )
    p = doc.add_paragraph(disclaimer); _style_runs(p, 10, italic=True, color=DOCX_MUTED)
    doc.save(path)

# ================================================================
# MAIN
# ================================================================

if __name__ == "__main__":
    memo_pdf = os.path.join(OUT_DIR, "PMC_Investment_Memorandum_v1.pdf")
    memo_doc = os.path.join(OUT_DIR, "PMC_Investment_Memorandum_v1.docx")
    deck_pdf = os.path.join(OUT_DIR, "PMC_Pitch_Deck_v1.pdf")
    snap_pdf = os.path.join(OUT_DIR, "PMC_Public_Snapshot_v1.pdf")
    build_memo_pdf(memo_pdf); print("wrote", memo_pdf)
    build_memo_docx(memo_doc); print("wrote", memo_doc)
    build_deck_pdf(deck_pdf); print("wrote", deck_pdf)
    build_snapshot_pdf(snap_pdf); print("wrote", snap_pdf)
