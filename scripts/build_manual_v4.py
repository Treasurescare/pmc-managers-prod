"""PMC v4 Master Training Manual — whole-site edition (screens, journeys, deep dives, runbooks, API, data model)."""
import json
import os
import re
import sys
from collections import defaultdict

import fitz
from pymongo import MongoClient
from reportlab.lib import colors
from reportlab.lib.units import mm
from reportlab.platypus import Image, KeepTogether, PageBreak, Paragraph, Spacer, Table, TableStyle
from reportlab.platypus.tableofcontents import TableOfContents
from reportlab.platypus.doctemplate import BaseDocTemplate, PageTemplate, Frame
from reportlab.lib.pagesizes import A4

sys.path.insert(0, "/app/scripts")
from build_manuals import B, D, GOLD, H2, H3, NAVY, SM, TODAY, shot, CREAM, ParagraphStyle, ss  # noqa: E402

SCREENS = json.load(open("/app/scripts/manual_screens.json")) + json.load(open("/app/scripts/manual_screens_extra.json"))
ORDER = ["Public website", "Supplier portal", "Admin console", "Partner portal", "Staff portal"]
CH = ParagraphStyle("ch", parent=ss["Title"], textColor=NAVY, fontSize=22, leading=26, alignment=0, spaceAfter=6)
SEC = ParagraphStyle("sec", parent=H2, fontSize=13)
TIP = ParagraphStyle("tip", parent=B, backColor=colors.HexColor("#FFF7E0"), borderColor=GOLD, borderWidth=0.6, borderPadding=5, spaceBefore=4, spaceAfter=6)
MONO = ParagraphStyle("mono", parent=SM, fontName="Courier", fontSize=7, leading=8.5)


class Doc(BaseDocTemplate):
    def __init__(self, path):
        super().__init__(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=16 * mm, bottomMargin=14 * mm,
                         title="PMC v4 Master Training Manual", author="PMC Managers")
        f = Frame(self.leftMargin, self.bottomMargin, self.width, self.height, id="f")
        self.addPageTemplates([PageTemplate(id="cover", frames=[f], onPage=self._cover), PageTemplate(id="body", frames=[f], onPage=self._body)])

    def _cover(self, c, d):
        c.saveState()
        c.setFillColor(NAVY)
        c.rect(0, 0, A4[0], A4[1], fill=1, stroke=0)
        c.setFillColor(GOLD)
        c.rect(0, A4[1] * 0.42, A4[0], 3, fill=1, stroke=0)
        c.restoreState()

    def _body(self, c, d):
        c.saveState()
        c.setStrokeColor(GOLD)
        c.line(15 * mm, A4[1] - 11 * mm, A4[0] - 15 * mm, A4[1] - 11 * mm)
        c.setFont("Helvetica", 7.5)
        c.setFillColor(colors.grey)
        c.drawString(15 * mm, A4[1] - 9.5 * mm, "PMC Managers \u00b7 Master Training Manual v4 \u00b7 Whole-site edition")
        c.drawString(15 * mm, 8 * mm, f"Issued {TODAY}")
        c.drawRightString(A4[0] - 15 * mm, 8 * mm, f"Page {d.page}")
        c.restoreState()

    def afterFlowable(self, fl):
        if isinstance(fl, Paragraph) and fl.style.name in ("ch", "sec"):
            lvl = 0 if fl.style.name == "ch" else 1
            txt = fl.getPlainText()
            key = f"k{self.seq.nextf('toc')}"
            self.canv.bookmarkPage(key)
            self.canv.addOutlineEntry(txt, key, level=lvl, closed=lvl == 0)
            self.notify("TOCEntry", (lvl, txt, self.page, key))


def tbl(rows, widths, head=True):
    t = Table([[Paragraph(str(c), SM if i or not head else ParagraphStyle("th", parent=SM, fontName="Helvetica-Bold")) for c in r] for i, r in enumerate(rows)], colWidths=widths, repeatRows=1 if head else 0)
    st = [("GRID", (0, 0), (-1, -1), 0.3, colors.HexColor("#D8D0BD")), ("VALIGN", (0, 0), (-1, -1), "TOP")]
    if head:
        st.append(("BACKGROUND", (0, 0), (-1, 0), CREAM))
    t.setStyle(TableStyle(st))
    return t


def P(t):
    return Paragraph(t, B)


def steps(items):
    return P("".join(f"{i}. {s}<br/>" for i, s in enumerate(items, 1)))


CHAPTERS = []


def chapter(title):
    def deco(fn):
        CHAPTERS.append((title, fn))
        return fn
    return deco


@chapter("1 \u00b7 Platform overview & architecture")
def c1():
    return [P("PMC Managers is a global e-procurement platform: buyers publish tenders, verified suppliers bid with sealed envelopes, an evaluation committee opens, checks and awards, and payments move through escrow \u2014 every step recorded in a tamper-evident audit ledger."),
            Paragraph("Portals", SEC), tbl([["Portal", "Address", "Who"], ["Public website", "/ , /tenders, /notices", "Anyone"], ["Supplier portal", "/vendor", "Registered suppliers"],
                                               ["Admin console", "/admin/e", "PMC admins and reviewers"], ["Staff portal", "/staff", "Committee, escrow, legal, accounting, certifier"],
                                               ["Partner portal", "/partner/me", "Partners who onboard suppliers"], ["Escrow portal", "/login?role=escrow", "Escrow institutions"]], [40 * mm, 55 * mm, 85 * mm]),
            Paragraph("Architecture", SEC),
            P("React single-page app (served from S3 + CloudFront) \u2192 FastAPI backend (Docker on AWS Elastic Beanstalk, all routes under /api) \u2192 MongoDB. "
              "Bid answers, prices and uploaded bid files are encrypted at rest and only decrypted after the committee signs each opening. "
              "AI features (DPR tender drafting, criteria reading, proof reading) use Gemini through the platform's AI key. Email goes through the managed email service. "
              "Scheduled jobs (reminders, statements, digests) run from the platform scheduler."),
            Image(f"{D}/pmc-data-flow.png", width=180 * mm, height=180 * mm * 0.707)]


@chapter("2 \u00b7 Roles at a glance")
def c2():
    return [tbl([["Role", "Main jobs", "Where"], ["Supplier", "Register, KYC, bid with criteria proofs, consortium, results, payouts", "Supplier portal"],
                 ["Admin", "Tenders, criteria, publishing, suppliers, partners, settings", "Admin console"], ["Reviewer", "Approves supplier-prepared tenders; edits criteria master", "Admin console"],
                 ["Committee member", "Signs openings, reviews proofs (all must agree), doubts, scores, awards", "Bidding ops / Staff portal"],
                 ["Certifier / Legal / Accounting", "Sequential bid clearances before award", "Staff portal"], ["Escrow agent", "EMD, dual-signed releases, payouts", "Staff portal / Escrow"],
                 ["Partner", "Onboards suppliers, earns commission", "Partner portal"], ["Auditor", "Reads the audit ledger and reports", "Admin console"]], [38 * mm, 95 * mm, 47 * mm])]


@chapter("3 \u00b7 Security, audit & data protection")
def c3():
    return [steps(["Sign-in by role with email + password (session cookie + CSRF token on every change).", "Role-based access: the admin console only admits admin and reviewer; other staff use the staff portal.",
                   "Sealed bidding: answers, price and bid files are encrypted; nobody (including admins) can open them before the committee signs.",
                   "Audit ledger: every action is chained with SHA-256; 'Verify chain' re-checks every link.", "Soft deletion: records are archived, not erased, unless a narrowly scoped deletion is explicitly requested.",
                   "AI sees proof files only after technical opening and only for qualified bids; AI only flags \u2014 people decide."])]


def screens_chapter(section):
    out = []
    for s in [x for x in SCREENS if x["section"] == section]:
        acts = "".join(f"\u2022 {a}<br/>" for a in s["actions"])
        out.append(KeepTogether([Paragraph(s["title"], SEC), Paragraph(f"Screen: <font face='Courier'>{s['path']}</font>", SM), Spacer(1, 2 * mm), shot(s["id"]),
                                 Spacer(1, 2 * mm), P(s["desc"]), P(f"<b>Main actions</b><br/>{acts}"), Spacer(1, 5 * mm)]))
    return out


for n, sec in enumerate(ORDER, 4):
    chapter(f"{n} \u00b7 {sec} \u2014 screen tour")(lambda sec=sec: screens_chapter(sec))


@chapter("9 \u00b7 Deep-dive: Tender builder & AI DPR")
def c9():
    return [steps(["Tender builder \u203a AI generate from DPR: pick country, a master template (or 'build a brand-new master'), upload up to 3 DPRs (PDF/DOCX/TXT, max 100 MB each).",
                   "Analyze runs in the background; each file shows progress, extracted headings and missing categories.", "Create AI-drafted tenders, review every section, then use Criteria and Create notice."]),
            Paragraph("If upload fails with 'status code 413' on AWS, the backend bundle was deployed without the .platform/nginx upload-size setting \u2014 redeploy the full backend ZIP (see chapter 13).", TIP)]


@chapter("10 \u00b7 Deep-dive: Criteria, sealed bids, opening & AI proof review")
def c10():
    return [steps(["Criteria come from the Criteria master or saved sets, AI-read from the tender document, or one-off. Each is pass/fail or scored, Mandatory or optional, with proof required or not.",
                   "Rule: a bid qualifies if it meets every mandatory criterion and at least N of the optional ones (blank = all).",
                   "Publish needs: main document, future deadline, at least one must-pass criterion (checklist on the draft row). Live tenders without bids can still change criteria.",
                   "Suppliers must answer mandatory items with proofs; everything is sealed on submit.", "After the deadline every committee member signs the technical opening; the system checks every bid and emails result notices.",
                   "AI reads each must-pass proof of qualified bids: Matches / Does not match / Unclear + figure found.",
                   "Every member accepts or rejects each proof (comment to reject). Mandatory rejection disqualifies; optional rejection disqualifies only below the minimum.",
                   "Doubts can be raised and resolved with notes. Download the proof check report (PDF) for the file."]),
            Image(f"{D}/pmc-process-flow.png", width=180 * mm, height=180 * mm * 0.707)]


@chapter("11 \u00b7 Deep-dive: Price opening, L1, award & escrow")
def c11():
    return [steps(["Price opening is blocked until every proof is decided; only qualified bids' prices open.", "L1 ranking runs automatically and shows on the opening card.",
                   "Award to L1 (committee member, one click + note) requires certifier, legal and accounting clearance on the L1 bid. Weighted tenders use the Award recommendation report.",
                   "On award: award letter and contract are generated; the winner is emailed 'Congratulations \u2014 your bid is awarded'; every other bidder is emailed that the tender went to another supplier, why (criteria failed, disqualified with the committee's note, or their L-rank and the awarded price) and their EMD refund date.",
                   "Escrow releases need two signatures; consortium awards create per-member payment instructions with bank references and a downloadable payout report."])]


@chapter("12 \u00b7 Partners, reminders & tracking")
def c12():
    return [steps(["Admin invites a partner; partner completes Profile, Banking, Documents, Agreement (progress bar 'N of 4').", "Reminder emails go 3 and 7 days after joining if unfinished (daily 09:00 London).",
                   "Every tender shows a progress line (Criteria \u2192 Bids \u2192 Opening \u2192 Proof review \u2192 Price \u2192 L1 \u2192 Award) on Notices and on the dashboard."])]


@chapter("13 \u00b7 Deployment runbook (AWS S3 + CloudFront + Elastic Beanstalk)")
def c13():
    return [steps(["Download the latest pmc-backend-vXX.zip and pmc-frontend-vXX-prod-build.zip.", "Backend: Elastic Beanstalk \u203a Upload and deploy the backend ZIP as-is (it contains .ebextensions and .platform/nginx \u2014 do not re-zip).",
                   "Check environment health is Green and /health returns 200.", "Frontend: empty the S3 site bucket, upload the contents of the frontend ZIP, then CloudFront \u203a Invalidations \u203a /*.",
                   "Check production secrets (email, AI key, cron secret) are set; scheduled jobs on AWS need an EventBridge rule calling each /api/v1/cron/... endpoint with the Bearer secret."])]


@chapter("14 \u00b7 Troubleshooting playbook")
def c14():
    return [tbl([["Symptom", "Likely cause", "Fix"], ["Upload fails: status code 413", "Web server body limit on AWS", "Redeploy full backend ZIP with .platform"],
                 ["AWS health 'Degraded'", "Failing health checks or 5xx", "EB \u203a Health \u203a causes; check /health and logs"], ["Old screens after deploy", "CloudFront cache", "Invalidate /*"],
                 ["Emails not arriving", "Email key missing/invalid", "Update the email secret and redeploy"], ["Price opening blocked", "Proof review or doubt pending", "Decide every proof / resolve doubts"],
                 ["Award to L1 refused", "L1 bid not cleared", "Complete certifier, legal, accounting clearances"], ["Supplier can't submit", "Mandatory criterion or proof missing", "Answer all mandatory items"]], [50 * mm, 55 * mm, 75 * mm])]


@chapter("15 \u00b7 Sample workflow \u2014 one tender end to end")
def c15():
    return [steps(["Admin drafts 'Hospital beds supply' from a DPR and adds 3 mandatory + 2 optional criteria (at least 1 optional), L1.", "Checklist all ticked \u2192 Publish.",
                   "Three suppliers bid; one misses a mandatory proof and cannot submit until fixed.", "Deadline passes; committee signs; 2 bids qualify, 1 fails (turnover below 500,000) and is notified.",
                   "AI flags a mismatch on one proof; one member rejects with a comment \u2192 that bid is disqualified.", "Price opening; L1 = remaining bid; clearances done; Award to L1; letters and emails go out; EMDs of others scheduled for refund."])]


@chapter("16 \u00b7 API reference index")
def c16():
    spec = json.load(open("/tmp/openapi.json"))
    groups = defaultdict(list)
    for p, ops in spec["paths"].items():
        for m in ops:
            if m in ("get", "post", "put", "patch", "delete"):
                groups[(ops[m].get("tags") or ["other"])[0]].append(f"{m.upper():6} {p}")
    out = [P(f"{sum(len(v) for v in groups.values())} endpoints, grouped by module. All are under /api; changes need sign-in and the CSRF header.")]
    for g in sorted(groups):
        out += [Paragraph(f"{g} ({len(groups[g])})", H3), Paragraph("<br/>".join(sorted(groups[g])).replace("{", "&#123;").replace("}", "&#125;"), MONO)]
    return out


@chapter("17 \u00b7 Data model appendix")
def c17():
    env = dict(l.strip().split("=", 1) for l in open("/app/backend/.env") if "=" in l)
    db = MongoClient(env["MONGO_URL"].strip('"'))[env["DB_NAME"].strip('"')]
    rows = [["Collection", "Main fields"]]
    for name in sorted(db.list_collection_names()):
        doc = db[name].find_one() or {}
        rows.append([name, ", ".join(k for k in list(doc)[:14] if k != "_id") or "\u2014"])
    return [P("Collections and their main fields (from the current schema; no data values shown)."), tbl(rows, [45 * mm, 135 * mm])]


@chapter("18 \u00b7 Release history")
def c18():
    txt = open("/app/memory/CHANGELOG.md").read()
    entries = re.findall(r"^## (.+)$", txt, re.M)
    return [P("Most recent releases first."), Paragraph("<br/>".join(f"\u2022 {e}" for e in reversed(entries)), SM)]


def _policy(title, purpose, rows, notes=None):
    out = [P(f"<b>Purpose.</b> {purpose}"), Spacer(1, 2 * mm), tbl(rows, [45 * mm, 135 * mm] if len(rows[0]) == 2 else [40 * mm, 70 * mm, 70 * mm])]
    if notes:
        out += [Paragraph(notes, TIP)]
    return out


@chapter("19 \u00b7 Procurement policy: criteria & qualification")
def p19():
    return _policy("", "Make sure every tender is judged by clear, published criteria applied the same way to every bidder.", [
        ["Rule", "What it means"], ["Published criteria only", "Bids are judged only on the criteria shown in the tender. Criteria come from the Criteria master or are added by the tender author and saved before publishing."],
        ["Mandatory vs optional", "The tender author marks each pass/fail criterion Mandatory (must be met) or optional and sets the minimum number of optional criteria a bidder must meet (blank = all)."],
        ["At least one must-pass", "A tender cannot be published without at least one must-pass criterion (publish checklist)."],
        ["Changing criteria", "Allowed on a live tender only while it has no bids; once a bid arrives criteria lock. Any other change is a corrigendum sent to all bidders."],
        ["System decides pass/fail", "At technical opening the system compares every answer with the rule. Nobody can override a pass/fail directly; the committee can only raise a logged doubt and decide it."],
        ["Consortium rules", "Each criterion says whether the lead, the combined members or every member must meet it."]])


@chapter("20 \u00b7 Proof review policy (AI + committee)")
def p20():
    return _policy("", "Check that the documents bidders attach actually support what they declared.", [
        ["Rule", "What it means"], ["Sealed until opening", "Proof files are encrypted on upload and cannot be opened by anyone before the committee signs the technical opening."],
        ["AI reads, people decide", "For qualified bids the AI reads each must-pass proof and records Matches / Does not match / Unclear with the figure found. The AI never passes or fails a bid."],
        ["Unanimous acceptance", "Every committee member must accept a proof for it to stand. One rejection (with a written comment) fails that proof."],
        ["Effect of a rejection", "Mandatory proof rejected \u2192 bid disqualified. Optional proof rejected \u2192 disqualified only if the bid falls below the minimum optional criteria."],
        ["Unreadable files", "Word/Excel or unreadable scans are marked 'check by hand'; the committee must still open and decide them."],
        ["Price opening gate", "Price envelopes cannot be opened until every proof on every qualified bid is decided and every doubt resolved."],
        ["Record", "The proof check report (PDF) is downloaded and kept on the tender file."]])


@chapter("21 \u00b7 Evaluation & award policy (L1 / weighted)")
def p21():
    return _policy("", "Award fairly and transparently to the right bidder.", [
        ["Rule", "What it means"], ["Method set in advance", "Each tender states before publishing whether the winner is the lowest compliant price (L1) or weighted technical + price marks."],
        ["Only qualified bids ranked", "Only bids that passed criteria and proof review have prices opened and are ranked."],
        ["Automatic L1", "L1 ranking runs automatically at price opening; compliance flags (e.g. suspiciously low, above budget) are shown for the committee."],
        ["Clearances before award", "The winning bid must have certifier, legal and accounting clearance before award."],
        ["Award to L1", "A committee member awards with one click and a note; the action is recorded in the audit ledger."],
        ["Notices to bidders", "The winner is congratulated; every other bidder is told why they were not selected (criteria failed, disqualified with the committee's note, or their L-rank and the awarded price) and their EMD refund date."]])


@chapter("22 \u00b7 Code of ethics & conflict of interest")
def p22():
    return _policy("", "Protect the integrity of every tender.", [
        ["Rule", "What it means"], ["Declare conflicts", "Committee members declare any interest in a bidder before signing an opening; a conflicted member steps aside."],
        ["No contact during evaluation", "Committee members do not discuss a live tender with bidders; clarifications go through the platform's messages."],
        ["Gifts", "No gifts or hospitality from bidders during a tender."], ["Confidentiality", "Bid contents, scores and committee comments are confidential until the award notice."],
        ["Reporting", "Concerns are raised to the PMC integrity officer; retaliation is prohibited."]])


@chapter("23 \u00b7 Data protection, retention & deletion")
def p23():
    return _policy("", "Handle personal and commercial data lawfully and securely.", [
        ["Rule", "What it means"], ["Minimum data", "Collect only what tendering, KYC and payments need."],
        ["Encryption", "Bid answers, prices and bid files are encrypted at rest; access is by role."],
        ["Soft deletion", "Records are archived, not erased, to keep the audit trail. Narrow, explicit deletion only on a verified request."],
        ["AI processing", "Only proof files of qualified bids are sent to the AI, after technical opening, to read the figures."],
        ["Secrets", "API keys and passwords live only in the server's secret settings \u2014 never in documents, chat, email or Git. If one leaks, revoke and replace it immediately."],
        ["Retention", "Tender records and audit ledger kept for the period required by the buyer's regulations (typically 7 years)."]])


@chapter("24 \u00b7 Incident response")
def p24():
    return _policy("", "Act quickly and consistently when something goes wrong.", [
        ["Step", "Owner", "Action"], ["1 Detect", "Anyone", "Report via the help desk or integrity email; note time and screen."],
        ["2 Contain", "PMC admin", "Suspend affected accounts or tender; revoke leaked keys at the provider and replace them in AWS."],
        ["3 Assess", "PMC admin + IT", "Use the audit ledger to see what happened and who was affected."],
        ["4 Notify", "PMC lead", "Tell affected buyers/suppliers; regulators where required (e.g. 72 hours for personal data breaches)."],
        ["5 Recover", "IT", "Redeploy clean bundles, verify chain, re-open the tender if needed."], ["6 Learn", "PMC lead", "Write a short review and update this manual."]])


@chapter("25 \u00b7 Complaints, appeals & escalation")
def p25():
    return _policy("", "Give bidders a clear route to question a decision.", [
        ["Stage", "Who", "Time"], ["Clarification", "Bidder asks via messages; PMC replies", "3 working days"],
        ["Complaint", "Bidder writes to PMC within 5 days of the result notice", "Acknowledged in 2 days"],
        ["Review", "PMC officer not involved in the tender reviews the record (proof check report, audit ledger)", "10 working days"],
        ["Appeal", "Buyer's appeal body or vendor-intel appeal process", "As per buyer rules"]])


@chapter("26 \u00b7 RACI matrix")
def p26():
    rows = [["Activity", "Responsible / Accountable", "Consulted / Informed"], ["Build tender & criteria", "Admin (R), Buyer (A)", "Reviewer (C)"], ["Publish", "Admin (R/A)", "Suppliers (I)"],
            ["Technical opening", "Committee (R), Chair (A)", "Suppliers (I)"], ["Proof review", "Every committee member (R), Chair (A)", "AI (C)"],
            ["Price opening & L1", "Committee (R/A)", "Accounting (I)"], ["Clearances", "Certifier, Legal, Accounting (R)", "Committee (I)"],
            ["Award", "Committee member (R), Chair (A)", "All bidders (I)"], ["Escrow release", "Two escrow signatories (R/A)", "Accounts (I)"]]
    return _policy("", "Who does what in each tender step.", rows)


@chapter("27 \u00b7 Templates")
def p27():
    def t(name, lines):
        return [Paragraph(name, SEC), Paragraph("<br/>".join(lines), MONO), Spacer(1, 3 * mm)]
    return (t("Committee minutes \u2014 technical opening", ["Tender: ______  Date/time: ______  Chair: ______", "Members present and conflict declarations: ______",
              "Bids received: __  Qualified by system: __  Not qualified: __", "Proof review decisions (attach proof check report): ______", "Doubts raised and resolution: ______", "Signatures: ______"])
            + t("Proof rejection comment", ["Criterion: ______  Bid: ______", "What the document shows: ______  What was declared: ______", "Reason for rejection: ______"])
            + t("Award notice (L1)", ["Tender ______ has been awarded to ______ at ______ (lowest compliant price).", "Ranking of qualified bids: L1 ______, L2 ______, L3 ______",
                "Bids not qualified and reasons: ______", "EMD refunds due by: ______"])
            + t("Corrigendum", ["Tender: ______  Corrigendum no.: ______  Date: ______", "What changes: ______  New deadline (if any): ______", "Reason: ______"])
            + t("Clarification reply", ["Question received: ______  From: (kept anonymous)", "Answer (shared with all bidders): ______"]))


@chapter("28 \u00b7 Service levels")
def p28():
    return _policy("", "Target response times.", [["Item", "Target"], ["Supplier KYC review", "2 working days"], ["Tender review (supplier-prepared)", "3 working days"],
                                                    ["Clarification answer", "3 working days"], ["Proof review after technical opening", "5 working days"],
                                                    ["Award after price opening", "10 working days"], ["EMD refund to losing bidders", "14 days after award"], ["Partner approval", "3 working days"]])


@chapter("29 \u00b7 Glossary")
def c19():
    g = [("DPR", "Detailed project report used to draft a tender"), ("EMD", "Earnest money deposit held in escrow with a bid"), ("L1", "Lowest compliant price among qualified bids"),
         ("Mandatory criterion", "Must be met by every bidder"), ("Optional criterion", "Counts toward the minimum number the tender sets"), ("Proof review", "AI finding + unanimous committee decision on each proof"),
         ("Corrigendum", "Formal change to a live tender sent to every bidder"), ("Consortium", "Registered suppliers bidding together"), ("Sealed bid", "Encrypted until the committee signs the opening")]
    return [tbl([["Term", "Meaning"]] + [list(x) for x in g], [45 * mm, 135 * mm])]


def build():
    path = f"{D}/PMC_v4_Master_Training_Manual.pdf"
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("t0", fontName="Helvetica-Bold", fontSize=10, leading=14), ParagraphStyle("t1", fontName="Helvetica", fontSize=8.5, leading=11, leftIndent=12)]
    W = ParagraphStyle("w", parent=B, textColor=colors.white)
    logo = "/app/backend/assets/pmc-logo-mark-256.png"
    from reportlab.platypus import NextPageTemplate
    story = [Spacer(1, 45 * mm), Image(logo, width=34 * mm, height=34 * mm), Spacer(1, 14 * mm),
             Paragraph("<font color='#B8892B' size='11'>PMC MANAGERS</font>", W), Spacer(1, 3 * mm),
             Paragraph("<font size='28'>Master Training Manual v4</font>", ParagraphStyle("ct", parent=W, leading=34)), Spacer(1, 4 * mm),
             Paragraph("<font size='12'>Whole-site edition \u00b7 every portal, every screen, every process</font>", W), Spacer(1, 60 * mm),
             Paragraph(f"Issued {TODAY} \u00b7 replaces v3 (Sovereign Edition)", W), NextPageTemplate("body"), PageBreak(),
             Paragraph("<b>Contents</b>", ParagraphStyle("ch2", parent=H2, fontSize=16)), toc, PageBreak()]
    for title, fn in CHAPTERS:
        story += [Paragraph(title, CH), Spacer(1, 2 * mm)] + fn() + [PageBreak()]
    Doc(path).multiBuild(story)
    return path


def section_pages(path):
    doc = fitz.open(path)
    pages = {}
    for i, pg in enumerate(doc):
        t = pg.get_text()
        for m in re.finditer(r"Screen: (/\S+)", t):
            pages.setdefault(m.group(1), i + 1)
        for key, ch in (("public", "4 \u00b7 Public"), ("supplier", "5 \u00b7 Supplier"), ("admin", "6 \u00b7 Admin"), ("partner", "7 \u00b7 Partner"), ("staff", "8 \u00b7 Staff")):
            if t.lstrip().split("\n")[1:2] and ch in t and key not in pages and i > 3:
                pages[key] = i + 1
    json.dump({"file": "/downloads/manual/PMC_v4_Master_Training_Manual.pdf", "pages": pages}, open(f"{D}/sections.json", "w"), indent=1)
    return len(doc), pages


if __name__ == "__main__":
    p = build()
    n, pages = section_pages(p)
    print(n, "pages;", len(pages), "anchors")
