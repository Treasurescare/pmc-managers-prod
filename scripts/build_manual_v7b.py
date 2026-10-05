"""PMC Managers v2 — Master Training Manual v3 builder.

Novice-grade companion to /app/scripts/capture_manual_v3.py.

Structure:
  Front matter
    · Title page + acknowledgment + revision history
    · How to use this manual (novice reader path)
    · Glossary of terms
    · Acronym & jargon index
    · Day-1 quick-start (URL → login → first action)
    · Portal anatomy (top bar, tabs, cards, error toasts)
  Body (auto-generated from capture_manual_v3 spec + manifest)
    · One chapter per screen: heading, screenshot (fit page),
      purpose, anatomy (fields), step-by-step tutorial, API refs,
      error states, pitfalls
  Back matter
    · Troubleshooting cookbook
    · Full API reference index
    · Version history

Output:
  /app/deliverables/PMC_Master_Training_Manual_v3.docx
  /app/deliverables/PMC_Master_Training_Manual_v3.pdf   (LibreOffice CLI)
"""
from __future__ import annotations

import json
import subprocess
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.enum.section import WD_SECTION
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor, Cm

SHOTS = Path("/app/deliverables/manual_v7_shots")
OUT_DOCX = Path("/app/deliverables/PMC_Master_Training_Manual_v7.docx")
OUT_PDF = Path("/app/deliverables/PMC_Master_Training_Manual_v7.pdf")

NAVY = RGBColor(0x0B, 0x1F, 0x3A)
NAVY_SOFT = RGBColor(0x5B, 0x7B, 0xA1)
GREY = RGBColor(0x60, 0x6E, 0x82)
BAND = RGBColor(0xF0, 0xF3, 0xF8)

TITLE = "PMC Managers v2 · Master Training Manual"
SUBTITLE = "Novice edition · v7 · Every screen · Every field · Every action · current forest-navy theme"
GENERATED = datetime.utcnow().strftime("%B %d, %Y")


# =============================================================
# STYLE HELPERS
# =============================================================
def _style(doc: Document):
    st = doc.styles["Normal"]
    st.font.name = "Calibri"
    st.font.size = Pt(10.5)
    st.font.color.rgb = NAVY
    st.paragraph_format.space_after = Pt(4)
    # Wider page margins for a technical manual (feels less cramped than default 1.25")
    for s in doc.sections:
        s.left_margin = Cm(2.0)
        s.right_margin = Cm(2.0)
        s.top_margin = Cm(1.8)
        s.bottom_margin = Cm(1.8)


def _title(p, text, size=28, color=NAVY, bold=True):
    p.paragraph_format.space_after = Pt(4)
    r = p.add_run(text)
    r.bold = bold
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.name = "Calibri"


def _kicker(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text.upper())
    r.font.size = Pt(9)
    r.font.color.rgb = GREY
    r.bold = True
    r.font.name = "Calibri"
    p.paragraph_format.space_after = Pt(2)


def _h1(doc, text):
    p = doc.add_paragraph()
    _title(p, text, size=22, color=NAVY, bold=True)


def _h2(doc, text):
    p = doc.add_paragraph()
    _title(p, text, size=15, color=NAVY, bold=True)


def _h3(doc, text):
    p = doc.add_paragraph()
    r = p.add_run(text.upper())
    r.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = NAVY_SOFT
    r.font.name = "Calibri"
    p.paragraph_format.space_before = Pt(6)
    p.paragraph_format.space_after = Pt(3)


def _p(doc, text, size=10.5, color=NAVY):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.font.size = Pt(size)
    r.font.color.rgb = color
    r.font.name = "Calibri"
    return p


def _bullet(doc, text):
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(text)
    r.font.size = Pt(10)
    r.font.color.rgb = NAVY
    r.font.name = "Calibri"


def _shade(cell, hex_color: str):
    tcPr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement("w:shd")
    shd.set(qn("w:val"), "clear")
    shd.set(qn("w:color"), "auto")
    shd.set(qn("w:fill"), hex_color)
    tcPr.append(shd)


def _band(doc, text):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.autofit = False
    c = tbl.rows[0].cells[0]
    _shade(c, "0B1F3A")
    p = c.paragraphs[0]
    r = p.add_run(text.upper())
    r.bold = True
    r.font.size = Pt(10)
    r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    r.font.name = "Calibri"


def _kv_table(doc, rows, col_widths=(2.2, 4.5)):
    if not rows:
        return
    tbl = doc.add_table(rows=len(rows), cols=2)
    tbl.autofit = False
    for i, (k, v) in enumerate(rows):
        rc = tbl.rows[i].cells
        rc[0].width = Inches(col_widths[0])
        rc[1].width = Inches(col_widths[1])
        _shade(rc[0], "F0F3F8")
        p1 = rc[0].paragraphs[0]
        r1 = p1.add_run(k)
        r1.bold = True
        r1.font.size = Pt(9.5)
        r1.font.color.rgb = NAVY
        r1.font.name = "Calibri"
        p2 = rc[1].paragraphs[0]
        r2 = p2.add_run(v)
        r2.font.size = Pt(9.5)
        r2.font.color.rgb = NAVY
        r2.font.name = "Calibri"


def _api_table(doc, rows):
    if not rows:
        return
    tbl = doc.add_table(rows=len(rows) + 1, cols=3)
    tbl.autofit = False
    for i, txt in enumerate(("Verb", "Path", "Notes")):
        c = tbl.rows[0].cells[i]
        _shade(c, "0B1F3A")
        p = c.paragraphs[0]
        r = p.add_run(txt)
        r.bold = True
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        r.font.size = Pt(9.5)
        r.font.name = "Calibri"
    for i, (v, path, note) in enumerate(rows, start=1):
        c = tbl.rows[i].cells
        for j, txt in enumerate((v, path, note)):
            pg = c[j].paragraphs[0]
            rn = pg.add_run(txt)
            rn.font.size = Pt(9)
            rn.font.color.rgb = NAVY
            rn.font.name = "Consolas" if j < 2 else "Calibri"


def _image(doc, image_path: Path, width_in=6.7):
    if not image_path.exists():
        _p(doc, f"[image missing: {image_path.name}]", color=GREY)
        return
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    try:
        p.add_run().add_picture(str(image_path), width=Inches(width_in))
    except Exception as exc:
        _p(doc, f"[image error: {image_path.name} · {exc}]", color=GREY)


def _pagebreak(doc):
    doc.add_page_break()


# =============================================================
# CONTENT: hard-coded front matter (novice-grade)
# =============================================================
GLOSSARY = [
    ("Approval Matrix", "Ordered list of role stamps required to publish a notice / award. Editable per tenant in Masters."),
    ("BOQ", "Bill Of Quantities — line-item cost sheet attached to a tender or contract."),
    ("Bid", "A vendor's response to a published notice — includes technical + commercial envelopes."),
    ("Corrigendum", "Formal amendment to an already-published notice. Auto-numbered PMC-COR-YYYY-####."),
    ("Committee", "Group of reviewers assigned to a notice — chair + members with quorum rules."),
    ("COI", "Conflict of Interest declaration — mandatory for evaluators."),
    ("Council", "Governing body. Owner tenant that authors master rules for sub-tenants."),
    ("EMD", "Earnest Money Deposit — refundable amount held in joint-signature escrow."),
    ("Envelope (DocuSign)", "A DocuSign package of documents sent for signature. Authoritative flag marks the legal version."),
    ("Escrow", "Neutral holding account. In PMC, always joint-signature: two officers must sign to move money."),
    ("G2 Access", "Merged view combining Permissions Matrix + Hierarchy Level — the effective access map."),
    ("Hierarchy Level", "0 = Admin (root), 1 = Reviewer, 2 = Committee/Staff, 3 = Support/Auditor (read-only)."),
    ("KYC", "Know-Your-Customer — country-scoped identity + doc verification bundle."),
    ("L1", "'Lowest 1' — the lowest-priced compliant bid, i.e. the price winner."),
    ("Notice", "The umbrella object for a Tender / RFP / RFQ. Every notice has a unique PMC-NOT-YYYY-####."),
    ("PO", "Purchase Order — issued to a vendor after award."),
    ("QCBS", "Quality-Cost Based Selection — hybrid technical + commercial score, e.g. 70/30."),
    ("Reverse Auction", "Timed downward-bid event held after technical qualification."),
    ("RFP", "Request For Proposal — structured tender with technical + commercial envelopes."),
    ("RFQ", "Request For Quotation — simple price-only quote request."),
    ("Sub-tenant", "Child tenant under an owner. Inherits masters and theme."),
    ("Tender", "The most formal procurement — full technical + commercial + legal cycle."),
    ("Tender Builder", "In-app template designer for tender / RFP / RFQ. Sections + annexures + AI drafter."),
    ("Tenant", "A branded portal. PMC is multi-tenant: same DB, tenant-scoped data + skin."),
    ("Vendor Intel", "Blacklist / whitelist / grey-list registry + KPI scoring."),
]

ACRONYMS = [
    ("BOT", "Build-Operate-Transfer (infra concession model)"),
    ("BOQ", "Bill Of Quantities"),
    ("COI", "Conflict Of Interest"),
    ("EMD", "Earnest Money Deposit"),
    ("GFR", "General Financial Rules (India)"),
    ("KPI", "Key Performance Indicator"),
    ("KYC", "Know Your Customer"),
    ("L1", "Lowest Compliant Bid (Level 1)"),
    ("PO", "Purchase Order"),
    ("QCBS", "Quality-Cost Based Selection"),
    ("RFP", "Request For Proposal"),
    ("RFQ", "Request For Quotation"),
    ("RBAC", "Role-Based Access Control"),
    ("SLA", "Service Level Agreement"),
    ("SME", "Small / Medium Enterprise"),
    ("TOTP", "Time-based One-Time Password (2FA)"),
]

DAY1_STEPS = [
    ("Step 1 · Open your welcome email",
     "Your admin or IT team will send you a welcome email from noreply@pmcmanagers.com. It contains the portal URL (usually https://www.pmcmanagers.com or your tenant-specific sub-domain), your email login, and a one-time password."),
    ("Step 2 · Reach the sign-in page",
     "Paste the URL into any modern browser (Chrome/Edge/Safari/Firefox). You will land on the public home page. In the top-right, click 'Sign in'. On the /login card, pick the tile that matches your role — 'I'm an admin', 'I'm a vendor', or 'I'm staff'. If you are the master admin, you may also open /admin/login directly."),
    ("Step 3 · Sign in",
     "Type your email → your password → Sign in. On success you will be redirected to your dashboard within one second. If you see a red toast, the message will tell you exactly why (wrong password, account locked, wrong role tab)."),
    ("Step 4 · Change the temporary password",
     "As soon as you land, click the avatar circle top-right → 'Change password'. Enter the temp password and a new one that is at least 12 characters, has an upper-case, a digit, and a symbol. Save. You are now signed in with your permanent password."),
    ("Step 5 · Take the tour",
     "Read the 'Portal Anatomy' chapter next. It explains the top-bar buttons, the tab strip, and the drawer/modal patterns that repeat across every screen. Once you have those three concepts, every panel in this manual will feel familiar."),
    ("Step 6 · Do your first action",
     "The fastest way to feel comfortable is to complete one real task on Day 1. For admins, that is publishing a draft notice in the Notices tab. For vendors, that is completing Section A of registration. For staff, that is opening the first task assigned to your role. Each chapter of this manual walks you through that first task with screenshots."),
    ("Step 7 · Sign out safely",
     "Every day, close your session by clicking the avatar top-right → 'Sign out'. The button clears your session cookie so nobody can resume it on a shared machine. If you close the tab without signing out, your cookie is still valid for 12 hours."),
]

ANATOMY_ITEMS = [
    ("Top bar",
     "Every logged-in screen shows the same top bar. Left: PMC brand + tenant chip (which portal you are inside). Right: notification bell (counts unread alerts), Audit Copilot (opens an AI Q&A drawer), Security button (opens the MFA setup modal), avatar (your account menu), Sign out."),
    ("Tab strip",
     "Directly under the top bar, admins see a chip-style tab strip with 26 tabs. On mobile (<768 px) the strip collapses into a single dropdown. Tabs never navigate — they swap the panel below without leaving the /admin URL. The URL query updates to ?tab=<key> so refresh keeps you in place."),
    ("Panel header",
     "Each panel starts with a small navy label (the panel kicker) and a big display heading. The kicker is the module family, the heading is the specific screen. Underneath, a filter/action bar carries the primary CTA + filters. Always look here first."),
    ("List rows",
     "Every listing panel uses a slim horizontal row per record. Rows expose a right-side chevron or a drawer button. Click the row (not the buttons) to open the drawer with full details."),
    ("Modals & drawers",
     "Modals slide in from the centre (dim overlay). Drawers slide in from the right (no overlay). Both close on ESC. Both use the same three-button footer: Cancel · Secondary · Primary."),
    ("Toasts",
     "Every backend action shows a toast in the bottom-right for 4s. Green = success, amber = warning, red = error. Errors always name the field + the reason (e.g. 'notice.budget_amount must be ≥ 0')."),
    ("Empty states",
     "A panel with no rows never shows a spinner forever. Instead it prints a friendly empty state with the exact next action. E.g. 'No committees yet — click New committee to seed one.'"),
    ("Loading states",
     "Skeleton bars (grey rectangles pulsing) while data is fetched. If a fetch exceeds 8s, a retry banner appears. Never a blank screen."),
    ("Language switcher",
     "In the public top-bar and inside the admin profile modal you can flip EN / RU / KK. The choice is stored in localStorage and applied on next paint."),
    ("Keyboard shortcuts",
     "ESC closes any open modal/drawer. Enter submits the currently-focused form. Tab moves between fields. Shift+Tab reverses. No mouse required for any core flow."),
]

TROUBLESHOOT = [
    ("I get 'Invalid credentials'",
     "Copy-paste the password from your email; it is case-sensitive. If it still fails, use 'Forgot password' on the login card. Token TTL is 30 min. If your account is locked, wait 15 min or ask admin to unlock in Masters → Staff."),
    ("The page is blank",
     "Hard-refresh (Ctrl+F5 / Cmd+Shift+R). If still blank, open browser dev-tools Console. A 401 error means your session expired — sign in again. A 500 error means the server had a problem — file a Help request with the request-id shown in the toast."),
    ("A tab is greyed out / says 'Access denied'",
     "Your role is not in the Permissions Matrix for that tab. Ask admin to open Masters → Permissions Matrix and tick the (role, tab) intersection. Or verify Hierarchy Level — Level 3 is read-only."),
    ("I can't publish a notice",
     "Only Master Admin (Level 0) can publish. Sub-admins/reviewers must submit for approval; the publish checkbox is grey for them. Also: a notice cannot publish if a required Tender Builder template is missing an approval stamp."),
    ("A file upload fails",
     "Max 10 MB per file. Accepted: PDF / DOCX / XLSX / PNG / JPG. If the file is under 10 MB and still fails, the tenant may lack S3 credentials — check with admin."),
    ("The public notice board is empty",
     "Only status=published notices are shown publicly. Drafts + closed + withdrawn are hidden. Confirm the notice was published (Notices tab → Status pill)."),
    ("Emails aren't arriving",
     "Every outbound email goes through Resend. If the tenant has no EMAIL_KEY, no email is sent (no error either). Verify the tenant → Masters → Tenants → key status."),
]

VERSION_HISTORY = [
    ("v5.0", GENERATED, "Pilot-testing edition. Three admin panels intentionally hidden from the UI during external QA (backend routes intact). All external references purged. Base URL updated to www.pmcmanagers.com throughout. Ready for investor review."),
    ("v4.0", "September 04, 2026", "Bug-fix showcase edition. Added chapters for V-02 vendor status filter, N-02 template jump-link, T-01 Tender Builder ALL KINDS view, E-03 Escrow reconciliation, RA-01 post-auction summary, MP-01 Masters clone role, AU-01 Audit filter bar, EN-03 Engagements buyer jump. Registration wizard sections A–E, vendor bid submit, reverse-auction room, meeting room and escrow-officer magic-link pages captured live via seeded runtime tokens. 71 screens total."),
    ("v3.0", "September 04, 2026", "Novice-grade rewrite. Every screen captured full-page. Glossary + acronym index + Day-1 quickstart added. Sub-tabs for masters/boq/evaluation/tender-builder walked separately. Vendor + staff portals captured post-login."),
    ("v2.0", "September 04, 2026", "Deep-dive edition. 16 core modules + 12 non-core stubs. First inclusion of API tables per screen."),
    ("v1.x", "August 2026", "Ops handbooks (Trainee v1/v3.1/v3.2). Screenshot manual v1."),
]


# =============================================================
# RENDERER — front matter
# =============================================================
def render_front_matter(doc: Document):
    # ------ COVER ------
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _title(p, "PMC MANAGERS v2", size=14, color=GREY, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _title(p, "Master Training Manual", size=44, color=NAVY, bold=True)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _title(p, "v5 · Novice edition", size=16, color=NAVY_SOFT, bold=False)
    for _ in range(4):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _title(p, "Every screen · Every field · Every action", size=12, color=NAVY_SOFT, bold=False)
    for _ in range(8):
        doc.add_paragraph()
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _title(p, f"Generated {GENERATED}", size=10, color=GREY, bold=False)
    p = doc.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    _title(p, "www.pmcmanagers.com", size=10, color=GREY, bold=False)
    _pagebreak(doc)

    # ------ HOW TO USE ------
    _kicker(doc, "Preface")
    _h1(doc, "How to use this manual")
    _p(doc, "This manual is written for the reader who has never seen the PMC Managers portal before. It assumes zero domain knowledge — every term is defined in the glossary, every acronym in the acronym index, and every screen is captured full-page so you can recognise the UI before you touch it.")
    _p(doc, "Read the front matter cover-to-cover once. After that, use the manual as a reference: jump to the chapter that matches the screen you are looking at, follow the numbered steps, and consult the API table only if you are integrating or debugging.")
    _h3(doc, "Reading paths")
    _bullet(doc, "New master admin — read every chapter in order. This is the deepest role.")
    _bullet(doc, "New reviewer / sub-admin — read Ch 1–3 (login, dashboard, notices) then jump to Bidding / Evaluation.")
    _bullet(doc, "New vendor — read Ch 1, then the Vendor Portal chapters.")
    _bullet(doc, "New staff (escrow / certifier / legal / accounting) — Ch 1, then the Staff Portal chapters and the module tied to your role (Escrow / Evaluation / Awards).")
    _bullet(doc, "QA engineer — every chapter includes an 'API reference' table and 'Error states' list — those are your test hooks.")
    _pagebreak(doc)

    # ------ GLOSSARY ------
    _kicker(doc, "Preface")
    _h1(doc, "Glossary of terms")
    _p(doc, "Every non-obvious term used in this manual is defined here. If you meet an unfamiliar term in a chapter, flip here first.")
    doc.add_paragraph()
    _kv_table(doc, GLOSSARY, col_widths=(1.9, 4.9))
    _pagebreak(doc)

    # ------ ACRONYMS ------
    _kicker(doc, "Preface")
    _h1(doc, "Acronym & jargon index")
    _kv_table(doc, ACRONYMS, col_widths=(1.3, 5.5))
    _pagebreak(doc)

    # ------ DAY-1 QUICK-START ------
    _kicker(doc, "Preface")
    _h1(doc, "Day-1 quick-start")
    _p(doc, "This is the shortest possible path from 'never seen the portal' to 'first productive action'. Even if you skip everything else, do these seven steps before you close the manual.")
    doc.add_paragraph()
    for title, body in DAY1_STEPS:
        _h3(doc, title)
        _p(doc, body)
    _pagebreak(doc)

    # ------ PORTAL ANATOMY ------
    _kicker(doc, "Preface")
    _h1(doc, "Portal anatomy — the ten UI patterns")
    _p(doc, "The portal repeats the same ten UI patterns everywhere. Learn them once, and every chapter of this manual will feel familiar.")
    doc.add_paragraph()
    for title, body in ANATOMY_ITEMS:
        _h3(doc, title)
        _p(doc, body)
    _pagebreak(doc)


# =============================================================
# RENDERER — one screen chapter
# =============================================================
def render_screen(doc: Document, spec: dict, chapter_no: int):
    _kicker(doc, f"Chapter {chapter_no} · {spec.get('role','').title() or 'Screen'}")
    _h1(doc, spec.get("title", spec["slug"]))

    if spec.get("audience"):
        _p(doc, "Audience: " + " · ".join(spec["audience"]), size=9.5, color=GREY)

    if spec.get("purpose"):
        _p(doc, spec["purpose"])

    # Meta table
    meta = [
        ("URL", spec.get("url", "")),
        ("Role", spec.get("role", "")),
    ]
    if spec.get("tab"):
        meta.append(("Admin tab", spec["tab"]))
    _kv_table(doc, meta, col_widths=(1.4, 5.4))

    # Screenshot
    doc.add_paragraph()
    img = SHOTS / spec.get("image", f"{spec['slug']}.png")
    _image(doc, img, width_in=6.7)
    _p(doc, f"Figure {chapter_no}.1 — {spec.get('title','')} (captured live).", size=9, color=GREY)

    # Anatomy of the screen
    if spec.get("fields"):
        _band(doc, "Anatomy · every element on this screen")
        _kv_table(doc, spec["fields"], col_widths=(2.0, 4.8))

    # Tutorial
    if spec.get("tutorial"):
        _band(doc, "Step-by-step tutorial")
        for i, (t, body) in enumerate(spec["tutorial"], start=1):
            _h3(doc, f"Step {i} · {t}")
            _p(doc, body)

    # API reference
    if spec.get("api"):
        _band(doc, "API reference")
        _api_table(doc, spec["api"])

    # Error states
    if spec.get("errors"):
        _band(doc, "Error states you may see")
        for e in spec["errors"]:
            _bullet(doc, e)

    # Pitfalls
    if spec.get("pitfalls"):
        _band(doc, "Common pitfalls")
        for p in spec["pitfalls"]:
            _bullet(doc, p)

    _pagebreak(doc)


# =============================================================
# BACK MATTER
# =============================================================
def render_back_matter(doc: Document):
    _kicker(doc, "Appendix")
    _h1(doc, "Troubleshooting cookbook")
    _p(doc, "The most common 'stuck' moments and how to unblock them.")
    doc.add_paragraph()
    for title, body in TROUBLESHOOT:
        _h3(doc, title)
        _p(doc, body)
    _pagebreak(doc)

    _kicker(doc, "Appendix")
    _h1(doc, "Version history")
    _kv_table(doc, [(f"{ver} · {date}", note) for ver, date, note in VERSION_HISTORY], col_widths=(1.9, 4.9))
    _pagebreak(doc)

    _kicker(doc, "Appendix")
    _h1(doc, "Support & escalation")
    _p(doc, "For portal issues, open a Help request from any authenticated screen (Help → New request) — the request ID is stamped in the toast and mailed to support. For urgent outages, escalate to the on-call ops manager via the phone tree published in Masters → Staff.")
    _p(doc, "Portal URL: https://www.pmcmanagers.com  |  Support inbox: support@pmcmanagers.com")


# =============================================================
# BUILD
# =============================================================
def build_manual(spec_module=None):
    # Import the spec module at run-time so we can pick up its lists
    import importlib.util
    spec_path = Path("/app/scripts/capture_manual_v7.py")
    sp = importlib.util.spec_from_file_location("cap_v3", spec_path)
    mod = importlib.util.module_from_spec(sp)
    sp.loader.exec_module(mod)

    manifest_path = SHOTS / "manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else []
    by_slug = {m["slug"]: m for m in manifest}

    # Merge the rich in-code specs (PUBLIC / ADMIN / VENDOR / STAFF) with
    # the runtime manifest (which has the image + resolved URL).
    all_screens: list[dict] = []
    for spec in mod.PUBLIC + mod.ADMIN + mod.VENDOR + mod.STAFF:
        m = by_slug.get(spec["slug"], {})
        merged = {**spec, **{k: v for k, v in m.items() if v}}
        # keep the rich fields from spec (m has fewer)
        for k in ("fields", "tutorial", "api", "pitfalls", "errors", "audience", "kpis", "purpose"):
            if spec.get(k):
                merged[k] = spec[k]
        all_screens.append(merged)

    # Stakeholder sub-tabs — hidden during pilot testing (see capture script).

    # -------- Build the document -----------------------------------------
    doc = Document()
    _style(doc)
    render_front_matter(doc)

    _kicker(doc, "Body")
    _h1(doc, "The portal · screen by screen")
    _p(doc, "Every subsequent chapter is one screen: what it does, every field on it, how to complete the primary action, the API endpoints it calls, common pitfalls and error states.")
    _pagebreak(doc)

    for i, spec in enumerate(all_screens, start=1):
        render_screen(doc, spec, i)

    render_back_matter(doc)
    doc.save(str(OUT_DOCX))
    print(f"[docx] wrote {OUT_DOCX} ({OUT_DOCX.stat().st_size // 1024} KB, screens={len(all_screens)})")

    # PDF via LibreOffice
    try:
        subprocess.run([
            "libreoffice", "--headless", "--convert-to", "pdf",
            "--outdir", str(OUT_DOCX.parent), str(OUT_DOCX),
        ], check=True, timeout=180)
        print(f"[pdf ] wrote {OUT_PDF} ({OUT_PDF.stat().st_size // 1024} KB)")
    except Exception as exc:
        print(f"[pdf ] convert failed: {exc}")


if __name__ == "__main__":
    build_manual()
