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

SCREENS = (json.load(open("/app/scripts/manual_screens.json")) + json.load(open("/app/scripts/manual_screens_extra.json"))
           + json.load(open("/app/scripts/manual_screens_new.json")) + json.load(open("/app/scripts/manual_screens_v61.json")))
ORDER = ["Public website", "Supplier portal", "Buyer portal", "Admin console", "Partner portal", "Staff portal"]
CH = ParagraphStyle("ch", parent=ss["Title"], textColor=NAVY, fontSize=22, leading=26, alignment=0, spaceAfter=6)
SEC = ParagraphStyle("sec", parent=H2, fontSize=13)
TIP = ParagraphStyle("tip", parent=B, backColor=colors.HexColor("#FFF7E0"), borderColor=GOLD, borderWidth=0.6, borderPadding=5, spaceBefore=4, spaceAfter=6)
MONO = ParagraphStyle("mono", parent=SM, fontName="Courier", fontSize=7, leading=8.5)


class Doc(BaseDocTemplate):
    header = "PMC Managers \u00b7 Master Training Manual v4 \u00b7 Whole-site edition"

    def __init__(self, path, title="PMC v4 Master Training Manual"):
        super().__init__(path, pagesize=A4, leftMargin=15 * mm, rightMargin=15 * mm, topMargin=16 * mm, bottomMargin=14 * mm,
                         title=title, author="PMC Managers")
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
        c.drawString(15 * mm, A4[1] - 9.5 * mm, self.header)
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


# Internal chapters kept in the source but left out of the published manual until go-live.
# Publish them with MANUAL_SHOW_INTERNAL=1 python3 scripts/build_manual_v4.py
HIDDEN_UNTIL_LIVE = {"13", "16", "17", "18"}


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
    chapter(f"{n if n < 6 else str(n - 1) + 'b'} \u00b7 {sec} \u2014 screen tour")(lambda sec=sec: screens_chapter(sec))


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


@chapter("28a \u00b7 What's new: fees, growth tools & languages")
def c28a():
    return [P("This chapter covers the features added in the latest releases. Each one also has a help guide and a video in the Help Centre."),
            Paragraph("Pricing bands & fee rules", SEC),
            steps(["Countries are grouped into pricing bands. Band names, tier names and the fee for each band are edited in <b>Masters</b> \u2192 <b>Fee rules</b>; nothing is fixed in code.",
                   "Before a tender is published, an admin opens <b>Fees</b> on the notice and ticks <b>Charge</b> or <b>Waive</b> for each fee. Publishing is blocked until the fees are confirmed.",
                   "The award fee rate is set per band (for example 0.30% today, any other rate or waived tomorrow). At publishing the admin also chooses who pays it: the buyer or the supplier.",
                   "When the award is completed, a Stripe payment link is sent automatically to the payer and is shown to admin accounts for follow-up.",
                   "Supplier bid fees: for each new supplier the admin decides whether extra categories are charged or waived.",
                   "Waivers can be approved by the Master Admin, an Admin or a Reviewer. Every decision is audit-logged."]),
            Paragraph("Supplier AI tools & saved alerts", SEC),
            steps(["<b>AI tender tools</b>: a supplier uploads any tender document (or picks a PMC tender) and gets a summary of eligibility, turnover, experience, EMD, fees, key dates and required documents.",
                   "<b>Bid readiness check</b>: compares the tender with the company profile and lists missing documents and disqualification risks.",
                   "Both are charged per use; the price, or a waiver, is set by the admin in Fee rules.",
                   "<b>Saved alerts</b>: suppliers save keywords, countries, value range and buyers and get matching PMC and global tenders instantly, daily or weekly."]),
            Paragraph("Growth tools (admin \u2192 Growth)", SEC),
            tbl([["Tab", "What it does"], ["Buyer applications", "Organisations apply at /buyers/apply; approve to create the organisation code, or reject."],
                 ["Consultancy services", "Create the services shown on /consultancy and track each request."],
                 ["Supplier directory", "Feature a supplier for premium visibility in /suppliers/directory."],
                 ["Global tender sources", "Turn sources on or off and fetch tenders (World Bank, EU TED, and a pipe ready for a licensed paid provider)."],
                 ["Data API clients", "Issue API keys with daily limits so outside businesses can read tender data."],
                 ["Translation review", "Native speakers approve or correct the AI translations."]], [45 * mm, 135 * mm]),
            Paragraph("Languages", SEC),
            steps(["The whole portal (public site, supplier portal, admin and staff portals) is available in 14 languages: English, Russian, Kazakh, Simplified Chinese, Traditional Chinese, Spanish, French, German, Hindi, Malay, Bahasa Indonesia, Korean, Japanese and Arabic (right-to-left).",
                   "The flag button at the top of every page (bottom-left on phones) changes the language. Everything on screen is translated, including tender titles and descriptions.",
                   "Public pages have their own address per language, for example /fr/buyers, so search engines show the site in each language.",
                   "Ask PMC answers in the chosen language, help videos have a voice-over in each language, and this manual is published in all 14 languages.",
                   "Translations are made by AI and checked by native speakers in <b>Growth</b> \u2192 <b>Translation review</b>. Reviewed phrases are never overwritten by AI."])]


@chapter("28b \u00b7 What's new: Supplier Marketplace & AI catalogue import")
def c28b():
    return [P("Suppliers can now sell products directly to verified buyers without running a tender. Every listing is approved by PMC first. Each part below also has a help guide and a video in the Help Centre."),
            Paragraph("Ways to sell", SEC),
            tbl([["Sale method", "How it works"],
                 ["Timed auction", "Starting price, optional hidden reserve, minimum bid step and closing time. The highest bid at closing wins."],
                 ["Best offer", "Buyers send offers until a deadline; the supplier accepts the one they want."],
                 ["Fixed price", "Buy now at the price the supplier sets."]], [40 * mm, 140 * mm]),
            P("A supplier can switch on any mix of the three for each product and chooses whether only verified buyer organisations, or any verified account, may take part."),
            Paragraph("Supplier: add products (Sell products)", SEC),
            steps(["Open <b>Sell products</b> and click <b>Add a product</b>. Enter the details, click <b>Upload photos</b> (up to 12) and <b>Attach spec sheet</b> for PDF datasheets (up to 6).",
                   "Tick the sale methods and prices, check what you will receive after the PMC fee, then click <b>Submit for approval</b>."]),
            Paragraph("Supplier: import a catalogue with AI", SEC),
            steps(["Click <b>Import from a catalogue with AI</b> and choose a PDF catalogue, brochure or a JPG/PNG photo of a page (up to 25 MB; the first 30 pages are read).",
                   "AI reads the file in 1 to 3 minutes and lists every product with its photo, a description, category, unit and specifications. Photos are taken from the PDF, or cut out of the page when the page is a scan or photo.",
                   "For each product the supplier decides: keep it or untick it; use the AI description (and edit it) or <b>Write my own</b>; add the specifications or not; which photos to keep, add or upload; and whether to attach the catalogue PDF as a spec sheet.",
                   "<b>Create draft listing(s)</b> saves the chosen products as drafts marked <i>set price &amp; how to sell</i>. A draft cannot be submitted until the supplier opens <b>Edit</b> and sets the sale method and price.",
                   "AI only uses facts in the document; it never adds prices or certifications. Reading a catalogue is free unless an admin sets a fee for <b>AI catalogue reading</b> in Pricing; a failed reading is never charged."]),
            Paragraph("Admin: approvals, fees and payouts (Marketplace)", SEC),
            steps(["Every listing waits in <b>Admin \u2192 Marketplace</b>. Check the photos, spec sheets and prices, then <b>Approve</b> or <b>Reject</b> with a note.",
                   "The PMC <b>sale fee</b> is a percentage or a fixed amount, or switched off. It can be waived for one listing when approving it. The listing fee is set in <b>Pricing \u2192 fee rules \u2192 Marketplace product listing</b>.",
                   "The buyer pays PMC through a secure Stripe link from <b>My bids &amp; purchases</b>. The order shows the PMC fee and the seller's bank details; the admin pays the balance and clicks <b>Mark seller paid</b> with the transfer reference. Automatic split payouts are not switched on."]),
            Paragraph("Buyers: the public Marketplace", SEC),
            steps(["<b>Marketplace</b> in the top menu lists approved products with photos, spec sheets, price or current bid and closing time.",
                   "Verified buyers bid, send an offer or click <b>Buy now</b>; purchases are paid from <b>My bids &amp; purchases</b> by <b>Pay securely</b>.",
                   "In the iPhone app the buy and pay buttons are hidden; buyers pay on the website."])]


@chapter("28c \u00b7 What's new: Buyer portal, watchlist & buyer teams")
def c28c():
    return [P("Buyers now have their own portal at <b>/buyer</b>, laid out like the supplier portal: left sidebar, top header with a notification bell and avatar menu, and a footer. Only verified buyers can bid or buy."),
            Paragraph("Becoming a buyer", SEC),
            tbl([["Route", "Steps", "Who approves"],
                 ["Register free", "Sign in page \u2192 Buyer organisation \u2192 Register as a buyer \u2014 free. Name, email, mobile, country and city are required (from the masters); state, address, ZIP and organisation are optional. Confirm the email link (3 days).", "PMC admin in Growth \u2192 Buyer applications (only after the email is confirmed)"],
                 ["Apply as an organisation", "/buyers/apply form for tender-issuing organisations.", "PMC admin; approval emails a 7-day set-password link"],
                 ["Added by PMC", "Admin \u2192 Growth \u2192 Buyer applications \u2192 + Add a buyer directly.", "Approved at once; sign-in emailed"]], [32 * mm, 98 * mm, 50 * mm]),
            Paragraph("Buyer portal pages", SEC),
            tbl([["Page", "What the buyer sees"], ["Dashboard", "Tiles: active bids & offers, to pay, in delivery, won, unread notifications; latest activity"],
                 ["Watchlist", "Products saved with \u2661 Save; reminder about an hour before a watched auction closes"],
                 ["Bids & auctions", "Status of every bid (Leading, Outbid, Won, Lost) and offer (Open, Accepted, Declined)"],
                 ["Purchases & deliveries", "Pay securely, delivery status set by the seller, I received it"], ["Payments & refunds", "Payments made and any refunds or payouts back to the buyer"],
                 ["Notifications", "Bell list; important events are also emailed"], ["My team", "Main buyer invites colleagues (PMC approves each) and removes them (immediate)"],
                 ["Profile & security", "Masters-backed profile, photo, change password; forgot password via the sign-in page"]], [40 * mm, 140 * mm]),
            Paragraph("Notifications sent to buyers", SEC),
            steps(["Outbid on an auction.", "About an hour before a watched auction closes (scheduler every 15 minutes).", "Auction won, offer accepted or order placed \u2014 pay now.",
                   "Payment received.", "Order dispatched / delivered (supplier marks it in Sell products \u2192 sales).", "Account verified by PMC."]),
            Paragraph("Security rules", SEC),
            steps(["Buyer sign-ins can never open PMC admin or staff pages; buyer-organisation admins are not PMC staff.", "A colleague only gets access after PMC approves the invite; removing a colleague ends every open session.",
                   "A buyer sees only their own bids, orders, notifications and organisation members.", "Unconfirmed emails cannot sign in; unverified buyers can browse but not bid or buy."]),
            Paragraph("Sample data in the screenshots is labelled DEMO and is not real business data.", TIP)]


DIAGRAMS = [("pmc-flow-1-tender-process", "Process flow 1 \u2014 Tender lifecycle"), ("pmc-flow-2-supplier-onboarding", "Process flow 2 \u2014 Supplier onboarding"),
            ("pmc-flow-3-buyer-onboarding", "Process flow 3 \u2014 Buyer onboarding & team"), ("pmc-flow-4-marketplace", "Process flow 4 \u2014 Supplier marketplace"),
            ("pmc-dfd-0-context", "Data flow \u2014 Level 0 (context)"), ("pmc-dfd-1-tendering", "Data flow \u2014 Level 1: tendering"),
            ("pmc-dfd-2-marketplace", "Data flow \u2014 Level 1: marketplace & buyer portal")]


@chapter("28d \u00b7 Process flow & data flow diagrams")
def c28d():
    out = [P("The same diagrams are in the separate <b>PMC Process & Data Flow Diagrams</b> PDF. Process flows show who acts and in which order; data flows show what information moves between people, processes and data stores (grey).")]
    for f, t in DIAGRAMS:
        out += [KeepTogether([Paragraph(t, SEC), Image(f"{D}/{f}.png", width=180 * mm, height=180 * mm * 0.707)]), Spacer(1, 4 * mm)]
    return out


@chapter("29 \u00b7 Glossary")
def c19():
    g = [("DPR", "Detailed project report used to draft a tender"), ("EMD", "Earnest money deposit held in escrow with a bid"), ("L1", "Lowest compliant price among qualified bids"),
         ("Mandatory criterion", "Must be met by every bidder"), ("Optional criterion", "Counts toward the minimum number the tender sets"), ("Proof review", "AI finding + unanimous committee decision on each proof"),
         ("Corrigendum", "Formal change to a live tender sent to every bidder"), ("Consortium", "Registered suppliers bidding together"), ("Sealed bid", "Encrypted until the committee signs the opening")]
    return [tbl([["Term", "Meaning"]] + [list(x) for x in g], [45 * mm, 135 * mm])]


def body_story(hidden, only=None):
    story, n = [], 0
    for title, fn in CHAPTERS:
        num, _, name = title.partition(" \u00b7 ")
        if num in hidden or (only is not None and num not in only):
            continue
        n += 1
        story.append((f"{n} \u00b7 {name}", fn()))
    return story


def build(path=None, title="Master Training Manual v4", sub="Whole-site edition \u00b7 every portal, every screen, every process", only=None, header=None):
    path = path or f"{D}/PMC_v4_Master_Training_Manual.pdf"
    toc = TableOfContents()
    toc.levelStyles = [ParagraphStyle("t0", fontName="Helvetica-Bold", fontSize=10, leading=14), ParagraphStyle("t1", fontName="Helvetica", fontSize=8.5, leading=11, leftIndent=12)]
    W = ParagraphStyle("w", parent=B, textColor=colors.white)
    logo = "/app/backend/assets/pmc-logo-mark-256.png"
    from reportlab.platypus import NextPageTemplate
    story = [Spacer(1, 45 * mm), Image(logo, width=34 * mm, height=34 * mm), Spacer(1, 14 * mm),
             Paragraph("<font color='#B8892B' size='11'>PMC MANAGERS</font>", W), Spacer(1, 3 * mm),
             Paragraph(f"<font size='28'>{title}</font>", ParagraphStyle("ct", parent=W, leading=34)), Spacer(1, 4 * mm),
             Paragraph(f"<font size='12'>{sub}</font>", W), Spacer(1, 60 * mm),
             Paragraph(f"Issued {TODAY} \u00b7 build v61 \u00b7 for testing", W), NextPageTemplate("body"), PageBreak(),
             Paragraph("<b>Contents</b>", ParagraphStyle("ch2", parent=H2, fontSize=16)), toc, PageBreak()]
    hidden = set() if os.environ.get("MANUAL_SHOW_INTERNAL") == "1" else HIDDEN_UNTIL_LIVE
    body = []
    for t, fl in body_story(hidden, only):
        body += [Paragraph(t, CH), Spacer(1, 2 * mm)] + fl + [PageBreak()]
    doc = Doc(path, title=f"PMC {title}")
    doc.header = header or f"PMC Managers \u00b7 {title}"
    doc.multiBuild(story + body)
    return path, body


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
    p, _ = build()
    n, pages = section_pages(p)
    print(n, "pages;", len(pages), "anchors")
