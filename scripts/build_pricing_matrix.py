"""Builds PMC_Pricing_Matrix.docx — bands, rate card (report baseline + recommended), and how fees are set in the portal."""
import os
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml import OxmlElement
from docx.oxml.ns import qn
from docx.shared import Inches, Pt, RGBColor

sys.path.insert(0, "/app/backend")
from routers.pricing import DEFAULT_BANDS  # noqa: E402

GREEN = RGBColor(0x16, 0x29, 0x21)
GOLD = RGBColor(0x9A, 0x7B, 0x2F)
OUT = "/app/frontend/public/downloads/PMC_Pricing_Matrix_8a0d8109.docx"
LOGO = "/app/frontend/public/downloads/pmc-logo-full-ivory.png"

d = Document()
st = d.styles["Normal"]
st.font.name, st.font.size = "Calibri", Pt(10.5)
for s in d.sections:
    s.left_margin = s.right_margin = Inches(0.8)


def shade(cell, hex_):
    tc = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear"), sh.set(qn("w:color"), "auto"), sh.set(qn("w:fill"), hex_)
    tc.append(sh)


def h(text, lvl=1):
    p = d.add_heading(text, level=lvl)
    for r in p.runs:
        r.font.color.rgb = GREEN if lvl == 1 else GOLD
    return p


def para(text, bold=False, italic=False, size=None):
    p = d.add_paragraph()
    r = p.add_run(text)
    r.bold, r.italic = bold, italic
    if size:
        r.font.size = Pt(size)
    return p


def bullets(items):
    for i in items:
        d.add_paragraph(i, style="List Bullet")


def table(head, rows, widths=None):
    t = d.add_table(rows=1, cols=len(head))
    t.style = "Table Grid"
    for i, x in enumerate(head):
        c = t.rows[0].cells[i]
        c.text = ""
        r = c.paragraphs[0].add_run(x)
        r.bold, r.font.size, r.font.color.rgb = True, Pt(9), RGBColor(0xFF, 0xFF, 0xFF)
        shade(c, "162921")
    for k, row in enumerate(rows):
        cells = t.add_row().cells
        for i, x in enumerate(row):
            cells[i].text = ""
            cells[i].paragraphs[0].add_run(str(x)).font.size = Pt(9)
            if k % 2:
                shade(cells[i], "F3EFE4")
    if widths:
        for row in t.rows:
            for i, w in enumerate(widths):
                row.cells[i].width = Inches(w)
    d.add_paragraph()


if os.path.exists(LOGO):
    d.add_picture(LOGO, width=Inches(2.2))
    d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
t = d.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("Global Tender Grid — Pricing Matrix")
r.bold, r.font.size, r.font.color.rgb = True, Pt(20), GREEN
t = d.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("Internal working document · DRAFT — prices are not finalised and are not published")
r.italic, r.font.size, r.font.color.rgb = True, Pt(10), GOLD

h("1. Principles")
bullets([
    "Buyer pays. Suppliers bid free by default; supplier fees are switched on or off per supplier by PMC.",
    "Every fee is a choice. Rates live in the portal (Masters → Fee rules) and can be changed at any time — 0.30% today, 0.10% or 1% tomorrow, or waived completely.",
    "Rates apply by pricing band, with a country-specific rule overriding its band where needed.",
    "Fees are confirmed per tender before publishing (Charge / Waive), then frozen on that tender. Later rate changes affect new tenders only.",
    "PMC never holds the buyer's contract money. Bid security (EMD) sits in dual-control escrow.",
])

h("2. Pricing bands (countries)")
para("Bands are editable in Masters → Pricing bands. A country can belong to one band only.", italic=True)
table(["Band", "Countries (ISO codes)", "Status"],
      [(n, " ".join(cs), "Inactive (not offered)" if c == "CHINA" else "Active") for c, n, cs, _ in DEFAULT_BANDS], [1.1, 4.6, 1.1])

h("3. Fee types")
table(["Fee", "Charged to", "When", "How it is calculated"], [
    ("Annual licence", "Buyer", "Yearly", "Fixed per band and tier (invoiced by PMC)"),
    ("Per-tender (hosting) fee", "Buyer", "Before publishing", "Fixed or % of tender budget, per band / tier"),
    ("Award fee", "Buyer or winning supplier (chosen per tender)", "Automatically at award", "% of awarded value, with maximum per package and no fee below a threshold"),
    ("Programme retainer", "Private programme owners", "Yearly", "Floor amount per band (invoiced by PMC)"),
    ("Extra business categories", "Supplier (if not waived)", "When the supplier adds a category", "First category free; extra categories per fee rule"),
    ("Tender document download", "Supplier (if not waived)", "Before download", "Fixed per tender, per fee rule"),
], [1.4, 1.5, 1.4, 2.5])

h("4. Rate card — baseline (from the Global Market & Pricing Intelligence Report)")
para("Tiers A / B / C. Amounts are list prices before launch discounts.", italic=True)
table(["Band", "Annual licence", "Per-tender fee", "Award fee", "Max per package", "No fee below", "Retainer floor"], [
    ("Global", "$24K / $9K / $2.4K", "$950 / $450 / $150", "0.50 / 0.75 / 1.00%", "$50K / $15K / $15K", "$25K", "$60K / yr"),
    ("Regional", "RM50K / RM19K / RM5K", "RM2K / RM950 / RM320", "0.50 / 0.75 / 1.00%", "RM200K / 60K / 60K", "RM100K", "RM150K / yr"),
    ("Programme", "$9.6K / $3.6K / $960", "$380 / $180 / $60", "0.50%", "$10K", "$10K", "$36K / yr"),
    ("India", "INR 1.99L / INR 75K / INR 20K", "INR 12.5K / INR 6K / INR 2K", "0.30%", "INR 3L", "INR 5L", "INR 15L / yr"),
    ("China", "Not active", "—", "—", "—", "—", "—"),
])

h("5. Recommended adjustments (report)")
table(["Item", "Recommendation"], [
    ("Award fee", "Harmonise at 0.30% in all bands, with an optional 0.50% assurance tier"),
    ("Who pays", "Buyer by default; India default is the winning supplier paying 0.30% (aligned with GeM)"),
    ("No fee below", "Raise India to INR 10L; consider $50K for Global"),
    ("Retainer floor", "Apply only to private programme owners"),
    ("Tier names", "Starter / Professional / Programme (replace A/B/C and Essential/Professional/Enterprise)"),
    ("Launch pricing", "India year-1 50–65% below list (from INR 99K); step up towards ~75% of list; renewals elsewhere capped at +5% a year"),
    ("Go-to-market", "Use live Kazakhstan tenders as proof; first tender free for 5–10 anchor buyers per market; full price after 30–40 paying buyers"),
], [1.5, 5.3])

h("6. Decision sheet — to be finalised by PMC")
table(["Band", "Licence (S / P / Pg)", "Per-tender fee", "Award fee %", "Max per package", "No fee below", "Award fee paid by", "Supplier fees"],
      [(n, "", "", "", "", "", "Supplier" if c == "INDIA" else "Buyer", "Charge / Waive") for c, n, _, _ in DEFAULT_BANDS])

h("7. How this is set up in the portal")
bullets([
    "Masters → Pricing bands: edit band countries, default award-fee payer and the default for supplier fees (charge or waive). Edit tier names.",
    "Masters → Fee rules → New: choose the fee type (Award fee, Tender hosting, Tender document download, Registration / extra categories), then Applies to: All countries, Pricing bands, or Specific countries. Optional buyer tier, % rate, maximum per package and No fee below value.",
    "Rule priority: category rule > country rule > band rule > all-countries rule; a tier rule only applies to tenders set to that tier.",
    "Notice publish checklist → Fees: an admin, reviewer or Master Admin ticks Charge or Waive for each fee (waivers need a reason and are audit-logged), picks the tier, chooses who pays the award fee and enters the buyer billing email. A tender cannot be published until fees are confirmed.",
    "At award: the award fee is calculated on the awarded value, and a Stripe payment link is emailed to the payer. Admin and Accounts are notified; Billing → Award fees shows status with Resend link and Waive.",
    "Supplier approval (Registrations): Charge or Waive for extra categories and document downloads, defaulted from the band. Waived suppliers bid free.",
    "Licence and retainer are agreed per buyer contract and invoiced by PMC; they are not charged automatically by the portal.",
])
para("Prepared for internal discussion. Not for publication until prices are finalised.", italic=True, size=9)

d.save(OUT)
print("saved", OUT)
