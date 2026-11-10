"""v61 manual set: Master Training Manual (refresh), PMC Staff & Admin manual, External Users manual — PDF + editable DOCX."""
import sys

import fitz
from docx import Document
from docx.enum.text import WD_BREAK
from docx.shared import Mm, Pt, RGBColor
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, Table

sys.path.insert(0, "/app/scripts")
import build_manual_v4 as M  # noqa: E402
from build_manual_v4 import CHAPTERS, D, P, SEC, TIP, steps, tbl, mm  # noqa: E402


def intro_external():
    return [P("This manual is for people outside PMC who use the platform: suppliers, buyers, partners and escrow institutions. Each part shows the screens you will use, with sample (DEMO) data."),
            Paragraph("Which part is for me?", SEC),
            tbl([["You are", "Sign in with", "Read"], ["A company that sells or bids on tenders", "Supplier", "Public website, Supplier portal, Marketplace"],
                 ["An organisation or person that buys", "Buyer organisation", "Buyer portal, Marketplace"], ["A partner who refers suppliers", "Partner", "Partner portal"],
                 ["A bank holding deposits", "Escrow institution", "Escrow institutions (below)"]], [62 * mm, 40 * mm, 78 * mm]),
            Paragraph("Signing in, passwords and help", SEC),
            steps(["Open the site and click <b>Sign in</b>. Choose your card (Supplier, Buyer organisation, Partner, Escrow) and enter your email and password.",
                   "New? Use the register link under your card: <b>Register as a supplier</b> (about 15 minutes, KYC checked by PMC) or <b>Register as a buyer \u2014 free</b>.",
                   "Forgot your password? Click <b>Forgot password</b>, choose the same card and follow the emailed link.",
                   "Every screen has <b>Help</b> in the top bar with guides and videos; questions go to tenders@pmcmanagers.com."]),
            Paragraph("Escrow institutions", SEC),
            steps(["PMC invites the bank; the escrow officer signs in with the <b>Escrow institution</b> card.", "Confirm earnest money deposits (EMD) held against bids.",
                   "Releases and payouts need two signatures; every action is recorded in the audit ledger."]),
            Paragraph("Your data is private: other users never see your bids, orders, documents or team. Sealed tender bids are encrypted until the committee opens them.", TIP)]


def intro_staff():
    return [P("This manual is for PMC's own people: administrators, reviewers, committee members, certifiers, legal, accounting, escrow agents and auditors. It covers the admin console, the staff portal, the day-to-day approval queues and the policies that govern them."),
            Paragraph("Daily queues to check", SEC),
            tbl([["Queue", "Where", "What to do"], ["Supplier registrations / KYC", "Admin \u2192 Registrations / Vendors", "Review documents, approve or ask for changes"],
                 ["Buyer applications & self-registrations", "Admin \u2192 Growth \u2192 Buyer applications", "Approve (only confirmed emails), reject, add a buyer directly, resend sign-ins"],
                 ["Buyer team invites", "Same tab \u2192 Team invites", "Approve or reject each colleague"], ["Marketplace listings", "Admin \u2192 Marketplace", "Approve / reject one by one or in bulk; fee and waivers"],
                 ["Supplier-added categories", "Admin \u2192 Masters \u2192 Category review", "Approve, rename or merge"], ["Seller payouts", "Admin \u2192 Marketplace \u2192 Orders", "Pay the net amount and mark seller paid"],
                 ["Tender openings & awards", "Staff portal / Bidding ops", "Sign openings, decide proofs, clear awards"]], [48 * mm, 58 * mm, 74 * mm]),
            Paragraph("Staff and admin accounts are separate from buyer accounts. A buyer-organisation admin can never use PMC staff pages.", TIP)]


CHAPTERS.insert(0, ("E1 \u00b7 Welcome \u2014 who this manual is for", intro_external))
CHAPTERS.insert(0, ("S1 \u00b7 Welcome \u2014 PMC staff & admin duties", intro_staff))

SETS = {
    "master": ("PMC_Master_Training_Manual_v61", "Master Training Manual", "Complete edition \u00b7 every portal, screen, process and policy", None),
    "staff": ("PMC_Staff_and_Admin_User_Manual_v61", "PMC Staff & Admin User Manual", "Admin console \u00b7 staff portal \u00b7 approvals \u00b7 policies",
              ["S1", "1", "2", "3", "6b", "8b", "9", "10", "11", "12", "14", "15", "19", "20", "21", "22", "23", "24", "25", "26", "27", "28", "28a", "28b", "28c", "28d", "29"]),
    "external": ("PMC_External_Users_Manual_v61", "PMC User Manual \u2014 Suppliers, Buyers & Partners", "Public website \u00b7 supplier portal \u00b7 buyer portal \u00b7 partner portal",
                 ["E1", "4", "5", "5b", "7b", "28b", "28c", "28d", "29"]),
}


# ---------- DOCX ----------
def _text(fl):
    return fl.getPlainText().strip()


def _img(doc, path, w):
    doc.add_picture(path, width=Mm(min(170, w / mm)))


def _emit(doc, fl):
    if isinstance(fl, KeepTogether):
        for x in fl._content:
            _emit(doc, x)
    elif isinstance(fl, PageBreak):
        doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    elif isinstance(fl, Image):
        _img(doc, fl.filename, fl.drawWidth)
    elif isinstance(fl, Paragraph):
        name, t = fl.style.name, _text(fl)
        if not t:
            return
        if name == "ch":
            doc.add_heading(t, level=1)
        elif name == "sec":
            doc.add_heading(t, level=2)
        else:
            for line in fl.text.replace("<br/>", "\n").split("\n"):
                s = Paragraph(line, fl.style).getPlainText().strip() if line.strip() else ""
                if s:
                    p = doc.add_paragraph(s)
                    if name == "tip":
                        p.runs[0].font.color.rgb = RGBColor(0x8A, 0x63, 0x1B)
                    if name in ("sm", "mono"):
                        p.runs[0].font.size = Pt(8)
    elif isinstance(fl, Table):
        cells = fl._cellvalues
        if len(cells) == 1 and len(cells[0]) == 1 and isinstance(cells[0][0], Image):
            _img(doc, cells[0][0].filename, cells[0][0].drawWidth)
            return
        t = doc.add_table(rows=len(cells), cols=len(cells[0]))
        t.style = "Table Grid"
        for i, row in enumerate(cells):
            for j, c in enumerate(row):
                t.cell(i, j).text = _text(c) if isinstance(c, Paragraph) else str(c or "")
                if i == 0:
                    for r in t.cell(i, j).paragraphs[0].runs:
                        r.bold = True
        doc.add_paragraph()
    elif hasattr(fl, "contents") and hasattr(fl, "width") and fl.__class__.__name__ == "Drawing":
        pass


def to_docx(body, path, title, sub):
    doc = Document()
    for s in doc.sections:
        s.left_margin = s.right_margin = Mm(18)
    doc.add_picture("/app/backend/assets/pmc-logo-mark-256.png", width=Mm(30))
    doc.add_heading(f"PMC Managers \u2014 {title}", 0)
    doc.add_paragraph(sub)
    doc.add_paragraph(f"Issued {M.TODAY} \u00b7 build v61 \u00b7 for testing. Screenshots use labelled DEMO sample data.")
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    doc.add_heading("Contents", 1)
    for fl in body:
        if isinstance(fl, Paragraph) and fl.style.name == "ch":
            doc.add_paragraph(_text(fl), style="List Bullet")
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)
    for fl in body:
        _emit(doc, fl)
    doc.save(path)


if __name__ == "__main__":
    for key in (sys.argv[1:] or SETS):
        name, title, sub, only = SETS[key]
        if only is None:
            only = [t.partition(" \u00b7 ")[0] for t, _ in CHAPTERS if not t.startswith(("S1", "E1"))]
        pdf, _ = M.build(f"{D}/{name}.pdf", title, sub, only=only)
        body = []
        for t, fl in M.body_story(M.HIDDEN_UNTIL_LIVE, only):
            body += [Paragraph(t, M.CH)] + fl + [PageBreak()]
        to_docx(body, f"{D}/{name}.docx", title, sub)
        print(key, pdf, len(fitz.open(pdf)), "pages")
