"""Reply to the Chairman's reviewer (12 points + A/B/C) with screenshot evidence, plus an internal note."""
import os
from datetime import datetime
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

IMG = "/tmp/reply"
OUT = "/app/frontend/public/downloads"
GREEN = RGBColor(0x1b, 0x4d, 0x3e)
GOLD = RGBColor(0x9a, 0x74, 0x1c)
GREY = RGBColor(0x55, 0x55, 0x55)
AMBER = RGBColor(0xb0, 0x6a, 0x00)
BLUE = RGBColor(0x1f, 0x4e, 0x8c)
TODAY = datetime.now().strftime("%d %B %Y")

TAGS = {
    "ENFORCED": GREEN,       # the software does it automatically and cannot be skipped
    "VERIFIABLE": BLUE,      # an outside party can check it
    "BUYER": GOLD,           # remains the buyer's responsibility
    "IN PROGRESS": AMBER,    # partly built / being completed
    "TO CONFIRM": GREY,      # a business / contractual decision for PMC to confirm
}


def new_doc():
    d = Document()
    d.styles["Normal"].font.name = "Calibri"
    d.styles["Normal"].font.size = Pt(10.5)
    for s in d.sections:
        s.left_margin = s.right_margin = Inches(0.9)
    return d


def shade(cell, hex_):
    tcPr = cell._tc.get_or_add_tcPr()
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:color"), "auto")
    sh.set(qn("w:fill"), hex_)
    tcPr.append(sh)


class W:
    def __init__(self, d):
        self.d = d
        self.fig = 0

    def h(self, text, size=15, color=GREEN, before=12):
        p = self.d.add_paragraph()
        r = p.add_run(text)
        r.bold = True
        r.font.size = Pt(size)
        r.font.color.rgb = color
        p.paragraph_format.space_before = Pt(before)
        p.paragraph_format.space_after = Pt(4)
        p.paragraph_format.keep_with_next = True
        return p

    def p(self, text, italic=False, bold=False, color=None, size=10.5):
        p = self.d.add_paragraph()
        r = p.add_run(text)
        r.italic, r.bold = italic, bold
        r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
        return p

    def b(self, text, tag=None):
        p = self.d.add_paragraph(style="List Bullet")
        if tag:
            r = p.add_run(f"[{tag}] ")
            r.bold = True
            r.font.size = Pt(9)
            r.font.color.rgb = TAGS[tag]
        p.add_run(text)
        return p

    def q(self, text):
        self.p("Raised: " + text, italic=True, color=GREY, size=10)

    def img(self, name, caption, width=6.3):
        path = os.path.join(IMG, name)
        if not os.path.exists(path):
            return
        self.fig += 1
        self.d.add_picture(path, width=Inches(width))
        self.d.paragraphs[-1].alignment = WD_ALIGN_PARAGRAPH.CENTER
        c = self.d.add_paragraph()
        r = c.add_run(f"Figure {self.fig}. {caption}")
        r.italic = True
        r.font.size = Pt(8.5)
        r.font.color.rgb = GREY
        c.alignment = WD_ALIGN_PARAGRAPH.CENTER

    def table(self, header, rows, widths=None, tag_col=None):
        t = self.d.add_table(rows=1, cols=len(header))
        t.style = "Table Grid"
        for i, htxt in enumerate(header):
            cell = t.rows[0].cells[i]
            cell.text = ""
            r = cell.paragraphs[0].add_run(htxt)
            r.bold = True
            r.font.size = Pt(9.5)
            r.font.color.rgb = RGBColor(0xff, 0xff, 0xff)
            shade(cell, "1B4D3E")
        for row in rows:
            cells = t.add_row().cells
            for i, v in enumerate(row):
                cells[i].text = ""
                r = cells[i].paragraphs[0].add_run(str(v))
                r.font.size = Pt(9.5)
                if tag_col is not None and i == tag_col:
                    r.bold = True
                    for k, col in TAGS.items():
                        if str(v).startswith(k):
                            r.font.color.rgb = col
        if widths:
            for row in t.rows:
                for i, w in enumerate(widths):
                    row.cells[i].width = Inches(w)
        self.d.add_paragraph()
        return t


def legend(w, shots=True):
    w.h("How to read this reply", 12)
    w.p("You asked us to distinguish what the platform enforces automatically, what can be independently "
        "verified, and what remains the buyer's responsibility. Every answer below is labelled accordingly:")
    w.b("built into the software; a user cannot skip or switch it off from the screen.", "ENFORCED")
    w.b("an outside party (auditor, bidder, lender) can check it without relying on our word.", "VERIFIABLE")
    w.b("the platform supports it, but the decision or obligation stays with the buyer.", "BUYER")
    w.b("partly built, or being connected; we state plainly what is not yet live.", "IN PROGRESS")
    w.b("a contractual or commercial commitment PMC Managers will confirm in writing; not a software feature.",
        "TO CONFIRM")
    if shots:
        w.p("All screenshots were taken from the PMC Managers platform on " + TODAY + " using clearly marked "
        "demonstration records (shown as \u201cDemo\u201d). No live buyer or supplier data is shown.",
        italic=True, color=GREY, size=9.5)


def build_reply():
    d = new_doc()
    w = W(d)

    t = d.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("PMC Managers")
    r.bold = True
    r.font.size = Pt(26)
    r.font.color.rgb = GREEN
    for txt, sz, col in [("Response to the Commercial & Institutional Review", 17, None),
                         ("Governance \u00b7 Security \u00b7 Implementation \u00b7 Commercial terms", 12, GREY),
                         ("Prepared " + TODAY + "  \u00b7  www.pmcmanagers.com", 10, GREY)]:
        p = d.add_paragraph()
        p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        rr = p.add_run(txt)
        rr.font.size = Pt(sz)
        rr.bold = sz > 15
        if col:
            rr.font.color.rgb = col

    w.h("Covering note", 13)
    w.p("Dear [Reviewer name],")
    w.p("Thank you for your careful review of the PMC Managers proposition and for the twelve points you raised. "
        "We agree that buyers, governments, development institutions, lenders and auditors will ask exactly these "
        "questions, and we would rather answer them with evidence than with assurances.")
    w.p("This reply takes each point in turn. For each one we explain how the platform works today, show the "
        "screen where it happens, and say clearly where a control is automatic, where it can be independently "
        "checked, where the buyer remains responsible, and where work is still in progress. We have followed your "
        "recommendation and grouped the answers into the three sections you proposed: A. Governance, Compliance "
        "and Integrity; B. Technology, Security and Operational Reliability; and C. Implementation, "
        "Accountability and Commercial Sustainability. Part D then walks through one tender from start to finish, "
        "with a screenshot of every step, and Part E sets out the responsibility matrix you asked for.")
    w.p("Yours sincerely,")
    w.p("[Name]\nChairman, PMC Managers")
    legend(w)

    d.add_page_break()
    w.h("Summary of answers", 13)
    w.table(["#", "Your point", "Where answered", "Position today"], [
        ("1", "Legal & regulatory compliance", "A1", "ENFORCED (register, country rules) + BUYER (local law)"),
        ("2", "Cybersecurity & data protection", "B1", "ENFORCED; independent test IN PROGRESS"),
        ("3", "Independent oversight committee", "A2", "ENFORCED (workflow) + TO CONFIRM (charter)"),
        ("4", "Dispute resolution", "A3", "ENFORCED (debrief, window, holds) + IN PROGRESS (formal appeals)"),
        ("5", "System integrity", "B2", "ENFORCED + VERIFIABLE"),
        ("6", "Technical evaluation & conflicts", "A4", "ENFORCED"),
        ("7", "Integration capabilities", "B3", "ENFORCED (exports, webhooks) + IN PROGRESS (ERP connectors)"),
        ("8", "Service levels & continuity", "B4", "ENFORCED (published standard) + TO CONFIRM (contract SLA)"),
        ("9", "Implementation & onboarding", "C1", "ENFORCED (guided onboarding, manuals)"),
        ("10", "Insurance & liability", "C2", "TO CONFIRM"),
        ("11", "Commercial pricing clarity", "C3", "ENFORCED (fee engine) + TO CONFIRM (tier table)"),
        ("12", "Independent validation", "B5", "IN PROGRESS"),
    ], widths=[0.35, 2.1, 0.9, 3.3], tag_col=3)

    d.add_page_break()
    # ================= A =================
    w.h("Section A \u2014 Governance, Compliance and Integrity", 17, GOLD)
    w.p("Why buyers, boards, lenders and auditors can have confidence in how a tender is run.", italic=True)

    w.h("A1. Legal and regulatory compliance (your point 1)", 14)
    w.q("How PMC Manager adapts to different national procurement laws, public procurement regulations, data "
        "protection requirements and electronic signature legislation.")
    w.b("Every tender is created for a specific country. The country decides which tender templates, fee rules, "
        "date rules and currency apply, and the AI tender builder drafts sections against that country's master "
        "template.", "ENFORCED")
    w.b("A per-country legal register, visible to the board, records whether PMC Managers is legally cleared to "
        "operate in each country (approved / pending / blocked), who gave the opinion, and a full change history.",
        "ENFORCED")
    w.b("Buyers can be classified as public or private. One officer classifies and a different officer must "
        "verify; the person who classified cannot verify their own entry.", "ENFORCED")
    w.b("Data protection: suppliers can export or permanently anonymise (\u201cforget\u201d) their own data from "
        "their account. Documents are visible only to the roles that need them.", "ENFORCED")
    w.b("Electronic signatures: committee members sign each bid opening electronically inside the platform "
        "(name, time and network address are recorded). Escrow releases and contracts use DocuSign, which provides "
        "a signature certificate recognised under the major e-signature laws (for example the US ESIGN Act and "
        "the EU eIDAS Regulation for advanced/simple signatures).", "ENFORCED")
    w.b("Whether a particular procurement must follow a specific national statute (thresholds, mandatory "
        "advertising periods, domestic preference rules) remains the buyer's legal decision. The platform makes "
        "these settings available per tender; it does not replace the buyer's legal adviser.", "BUYER")
    w.b("Formal legal opinions for each target country, and a data-processing agreement template for buyers, "
        "will be supplied with the contract.", "TO CONFIRM")
    w.img("r06-gov-legal.png", "Board-visible per-country legal register (Governance & integrity \u2192 Legal register).")

    w.h("A2. Independent oversight \u2014 the Procurement Integrity Committee (your point 3)", 14)
    w.q("Composition, appointment, independence, responsibilities and authority of the Independent Procurement "
        "Integrity Committee.")
    w.p("What the software enforces today:", bold=True)
    w.b("Any officer can place an integrity hold on a tender. The committee reviews and votes; a case follows a "
        "fixed sequence (raised \u2192 under review \u2192 resolved) and a resolved case cannot be quietly reopened "
        "or changed.", "ENFORCED")
    w.b("A senior officer can overrule the committee only on the record: the override, its author and the reason "
        "are written to the audit ledger, logged in the exceptions register and flagged as publicly disclosable.",
        "ENFORCED")
    w.b("A collusion-indicator scan highlights bidders on the same tender who share an email domain, phone, "
        "address or bank account, or who repeatedly bid together. These are prompts for review, not findings of "
        "wrongdoing.", "ENFORCED")
    w.p("What PMC Managers proposes to adopt as the committee charter (for confirmation):", bold=True)
    w.table(["Item", "Proposed position"], [
        ("Composition", "[3] members: [1] independent chair with procurement or audit background, [1] legal "
                        "member, [1] member nominated by the buyer or lender. No member may work on the tenders "
                        "they oversee."),
        ("Appointment", "Appointed by the PMC Managers board for [2] years, renewable once; independent chair "
                        "approved by [the board / the lender]."),
        ("Independence", "Annual declaration of interests; recusal on any tender involving a related party; no "
                         "remuneration linked to tender volumes."),
        ("Authority", "Can suspend any tender, require re-evaluation, refer to the buyer's audit body, and publish "
                      "a finding. Overrides by management are recorded and reported to the board."),
        ("Reporting", "Quarterly report to the board and, where agreed, to lenders: holds raised, cases resolved, "
                      "overrides, collusion indicators reviewed."),
    ], widths=[1.4, 5.2])
    w.img("r05-gov-integrity.png", "Integrity & collusion: raise a hold, run the collusion-indicator scan, review cases.")

    w.h("A3. Dispute resolution (your point 4)", 14)
    w.q("Procedures for supplier complaints, bid challenges, procurement disputes, suspected irregularities and appeals.")
    w.b("Before the deadline: suppliers raise clarification questions on the tender; answers are published to all "
        "bidders, and any change to the tender is issued as a numbered corrigendum.", "ENFORCED")
    w.b("After qualification and award: every supplier automatically receives a result notice. Losing bidders "
        "can open a private debrief page showing their own criteria results, proof-review decisions and rank, and "
        "the reason they were not selected. They never see another bidder's details.", "ENFORCED")
    w.b("Complaint window: the debrief invites the supplier to raise a clarification or complaint within 5 days "
        "of the result, through the platform's Messages, so every complaint is time-stamped and kept with the "
        "tender file.", "ENFORCED")
    w.b("Suspected irregularities: any officer can place an integrity hold (A2). A supplier barred from bidding "
        "can lodge an appeal with evidence; the decision and reason are recorded.", "ENFORCED")
    w.b("A formal multi-stage bid-challenge procedure (standstill period before contract signature, review by the "
        "Integrity Committee, then appeal to an external body or arbitration) is being built. Until then the "
        "standstill and appeal stages are run under the buyer's own rules.", "IN PROGRESS")
    w.b("The final appeal body and the governing law for disputes are set by the buyer's procurement rules and the "
        "contract.", "BUYER")
    w.img("r27-debrief.png", "Bidder debrief page seen by a losing supplier (only their own result; note the 5-day "
          "complaint window).")

    w.h("A4. Technical evaluation, separation and conflicts of interest (your point 6)", 14)
    w.q("How technical and commercial evaluations are conducted, documented and separated, including conflicts of "
        "interest and evaluator accountability.")
    w.b("Two sealed envelopes. Technical and commercial (price) parts of each bid are encrypted on upload and kept "
        "sealed. Price is removed by the server itself, not merely hidden on screen, until the commercial opening.",
        "ENFORCED")
    w.b("Order is fixed. The commercial envelope cannot be opened until the technical envelopes have been opened, "
        "at least one bid has passed technical evaluation, and every doubt raised by the committee has been "
        "resolved. This applies to administrators as well.", "ENFORCED")
    w.b("Criteria are set per tender before publishing (mandatory and optional, drawn from a criteria master). At "
        "the technical opening the system checks every bid against them and records pass or fail with the reason, "
        "for example \u201cFail: 400,000 GBP is below the required 500,000 GBP\u201d.", "ENFORCED")
    w.b("AI reads each proof document and flags mismatches (for example \u201caccounts show 400,000; vendor "
        "declared 750,000\u201d). The AI only flags. Every committee member must agree to accept or reject each "
        "proof and record a comment. The AI never sees prices.", "ENFORCED")
    w.b("Conflict of interest: each evaluator must declare any conflict before scoring, and each opening signature "
        "includes the statement \u201cI have no conflict of interest\u201d. Declarations go to the audit ledger.",
        "ENFORCED")
    w.b("Ranking (lowest compliant price, weighted score, or the method chosen for the tender) runs only among "
        "qualified bids. Award to the lowest-ranked bid (L1) is one recorded action.", "ENFORCED")
    w.b("Choosing competent, independent evaluators and the weightings for a tender is the buyer's decision.",
        "BUYER")
    w.img("r13-criteria.png", "Criteria master: reusable mandatory and optional criteria, with rules for consortium bids.")
    w.img("r15-evaluations.png", "Evaluation: committee scoring, declarations and the evaluation record.")
    w.img("r16-l1.png", "L1 comparison: ranking among qualified bids only, with one-click award to L1.")

    d.add_page_break()
    # ================= B =================
    w.h("Section B \u2014 Technology, Security and Operational Reliability", 17, GOLD)
    w.p("Why the platform can be trusted with sensitive international procurement.", italic=True)

    w.h("B1. Cybersecurity and data protection (your point 2)", 14)
    w.q("Encryption, access controls, cybersecurity monitoring, independent security testing, disaster recovery "
        "and protection of confidential bids.")
    w.table(["Control", "How it works today", "Status"], [
        ("Encryption in transit", "All traffic is served over HTTPS (TLS).", "ENFORCED"),
        ("Encryption of bids at rest", "Technical and commercial envelopes are encrypted with a server key "
                                       "(AES with an integrity check) when uploaded, and stay sealed until the "
                                       "committee opening.", "ENFORCED"),
        ("Passwords", "Stored only as salted bcrypt hashes. Reset links are single-use, expire after one hour and "
                      "are rate-limited.", "ENFORCED"),
        ("Access control", "Role-based permissions for every screen and action (admin, reviewer, committee, "
                           "escrow, legal, accounts, auditor, supplier, partner). Staff accounts cannot be given "
                           "admin rights by mistake.", "ENFORCED"),
        ("Two-factor sign-in", "Authenticator-app (TOTP) two-factor sign-in is available to all users. Making it "
                               "compulsory for high-risk roles (escrow, legal, accounts) is a setting we will "
                               "switch on for institutional buyers.", "ENFORCED (available) / TO CONFIRM (compulsory)"),
        ("Session protection", "Time-limited sessions with cross-site request forgery protection on every change.",
         "ENFORCED"),
        ("Release safeguards", "Every software release is scanned automatically and blocked if it contains a "
                               "password or access key.", "ENFORCED"),
        ("Monitoring & incidents", "Incidents affecting a deadline or opening are logged and, where bidders are "
                                   "affected, disclosed publicly.", "ENFORCED"),
        ("Hosting", "Amazon Web Services (Elastic Beanstalk application hosting, CloudFront delivery).", "ENFORCED"),
        ("Backups & disaster recovery", "Database backups with documented restore. Recovery point / recovery time "
                                        "objectives: RPO [24 hours], RTO [4 hours].", "TO CONFIRM"),
        ("Independent penetration test", "Not yet carried out. Commissioning an accredited (CREST or equivalent) "
                                         "test before institutional launch.", "IN PROGRESS"),
    ], widths=[1.5, 3.9, 1.2], tag_col=2)
    w.img("r10-permissions.png", "Permissions: role-by-role access to every screen and action.")
    w.img("r25-vendor-account.png", "Account & security: two-factor sign-in, password and data controls for each user.")

    w.h("B2. System integrity \u2014 opening times, unalterable records, proof of no interference (your point 5)", 14)
    w.q("How opening times are enforced, how records are protected against alteration, and how the platform "
        "demonstrates that no unauthorised access or intervention occurred.")
    w.b("Deadline: bids are accepted up to the published deadline to the second, using the server's clock, not "
        "the user's computer.", "ENFORCED")
    w.b("Opening: the server refuses to open any envelope while submission is still open, before the published "
        "opening date and time, or before every member of the tender's committee has signed the opening "
        "electronically. Only committee members can sign, and each can sign once.", "ENFORCED")
    w.b("Records: every significant action (sign-in, upload, opening, decision, award, payment instruction) is "
        "written to an append-only audit ledger. Each entry is sealed with a SHA-256 hash of the previous entry, so "
        "changing any past record breaks the chain at that exact point.", "ENFORCED")
    w.b("Proof: the chain is re-verified automatically and the result is published on the public Trust & "
        "security page (events recorded, breaks found). Any auditor or bidder can check a single record "
        "themselves with \u201cVerify a record\u201d, without signing in.", "VERIFIABLE")
    w.b("Exceptions: every manual bypass, waiver or override is copied to a single exceptions register naming the "
        "officer and the reason, so the absence of an entry is itself meaningful evidence.", "ENFORCED")
    w.p("A note on precision: we describe the ledger as tamper-evident rather than tamper-proof. It shows, and "
        "pinpoints, any alteration; it does not physically prevent a database administrator from attempting one.",
        italic=True, color=GREY, size=9.5)
    w.img("r01-trust.png", "Public Trust & security page: live ledger status and \u201cVerify a record\u201d for outside parties.")
    w.img("r09-audit.png", "Audit ledger: every action, who did it and when.")
    w.img("r04-gov-exceptions.png", "Exceptions register: every manual bypass or override, with officer and reason.")

    w.h("B3. Integration capabilities (your point 7)", 14)
    w.q("How PMC Manager connects with existing ERP, accounting, financial management, banking and project "
        "management systems.")
    w.b("Standard exports available today: comparative statement (Excel), escrow releases (CSV), consortium "
        "payment instructions (CSV), contracts list (CSV), bills of quantities (Excel/PDF), tender documents and "
        "proof-review reports (PDF). These import directly into most ERP and accounting systems.", "ENFORCED")
    w.b("Live connections already in use: card and bank payments (Stripe), e-signature (DocuSign), email "
        "notifications and WhatsApp alerts.", "ENFORCED")
    w.b("Sanctions screening: PMC Manager will send supplier and director details to Vindex, our own screening "
        "platform, which screens them by direct API against Refinitiv World-Check One (LSEG). The PMC Manager to "
        "Vindex link is not built yet; until then checks are made manually during supplier verification.", "IN PROGRESS")
    w.b("The platform is built on a documented web interface (REST/JSON), so direct connectors can be added for a "
        "buyer's ERP (for example SAP, Oracle, Microsoft Dynamics) or project management tools. These are scoped "
        "per buyer during implementation.", "IN PROGRESS")
    w.b("Banking: payments to suppliers are not moved automatically. After a dual-signed escrow release the "
        "platform issues a payment instruction; the bank transfer is made by the authorised bank and its reference "
        "is recorded back against the instruction. We regard this separation as a control, not a gap.", "ENFORCED")
    w.img("r18-escrow.png", "Escrow / EMD: dual-signed releases, payment instructions and downloadable reports.")

    w.h("B4. Service levels and business continuity (your point 8)", 14)
    w.q("Platform availability, technical support, response times, maintenance, incident management and business "
        "continuity.")
    w.p("Published service standard (shown publicly today):", bold=True)
    w.b("Bids accepted until the published deadline to the second, server-timestamped.", "ENFORCED")
    w.b("Live bid-opening availability target: 99.5% per month.", "ENFORCED")
    w.b("If live streaming of an opening fails, it continues automatically on a fallback connection; if that "
        "fails, it closes on a manual, audited record, so no bid is lost.", "ENFORCED")
    w.b("Critical incidents (deadline or opening affected) acknowledged within 1 hour, and disclosed where "
        "bidders are affected.", "ENFORCED")
    w.p("Contractual service levels proposed (for confirmation):", bold=True)
    w.table(["Item", "Proposed commitment"], [
        ("Overall platform availability", "[99.5%] per calendar month, excluding scheduled maintenance"),
        ("Scheduled maintenance", "[Sundays 00:00\u201304:00 UTC], announced [72 hours] ahead; never during a "
                                  "published deadline or opening"),
        ("Support hours", "[Monday\u2013Friday, 08:00\u201318:00 GST / UK time]; critical line 24/7"),
        ("Response times", "Critical [1 hour] \u00b7 High [4 hours] \u00b7 Normal [1 business day]"),
        ("Deadline protection", "If an outage affects a deadline, the deadline is extended by corrigendum and all "
                                "bidders are told"),
        ("Continuity", "Backups and restore as in B1; tested restore [quarterly]"),
    ], widths=[2.0, 4.6])
    w.img("r07-gov-incidents.png", "Incidents & service standard: incident log and the published standard.")

    w.h("B5. Independent validation (your point 12)", 14)
    w.q("Independent technical, cybersecurity, governance and procurement-process assessments.")
    w.p("We agree this is essential for institutional buyers. Our position, stated plainly:")
    w.b("Internal: the controls in this document are covered by automated tests that run on every release (for "
        "example: price never reaches the AI tool; an officer cannot verify their own classification or approve "
        "their own fee waiver; a resolved integrity case cannot be changed). These are our own tests, not an "
        "independent assessment.", "ENFORCED")
    w.b("Outside parties can already verify audit records themselves (B2).", "VERIFIABLE")
    w.b("Planned independent assessments: (1) accredited penetration test; (2) ISO/IEC 27001 readiness review; "
        "(3) independent review of the procurement process against the UNCITRAL Model Law on Public Procurement, "
        "World Bank Procurement Regulations and OECD integrity principles; (4) annual governance review of the "
        "Integrity Committee. Target dates: [to be confirmed].", "IN PROGRESS")
    w.p("We will not describe the platform as certified or independently assessed until these reports are issued.",
        italic=True, color=GREY, size=9.5)

    d.add_page_break()
    # ================= C =================
    w.h("Section C \u2014 Implementation, Accountability and Commercial Sustainability", 17, GOLD)

    w.h("C1. Implementation and onboarding (your point 9)", 14)
    w.q("How a new organisation moves from initial registration to operational use, including configuration, "
        "training and implementation support.")
    w.table(["Step", "What happens", "Who"], [
        ("1. Register", "Organisation registers online, or downloads a blank registration form.", "Buyer / supplier"),
        ("2. Verify", "Company documents and KYC checked; account activated only after verification.", "PMC compliance"),
        ("3. Configure", "Country, currency, departments, committee members, roles, criteria library and fee rules "
                         "are set up.", "PMC + buyer"),
        ("4. Train", "Role-based training using the 104-page screenshot manual, in-portal Help linked to the right "
                     "manual section, and a guided first tender.", "PMC"),
        ("5. First tender", "First tender run with PMC staff alongside (criteria, publication, opening, award).",
         "Buyer, supported"),
        ("6. Go live", "Buyer runs tenders independently; dashboard shows each tender's stage so delays are "
                       "visible.", "Buyer"),
    ], widths=[1.1, 4.2, 1.3])
    w.p("Typical timeline from signature to first live tender: [4\u20136 weeks] (to be confirmed per buyer).",
        italic=True, color=GREY, size=9.5)
    w.img("r02-register.png", "Step 1 \u2014 online pre-tender registration (or a downloadable blank form).")
    w.img("r22-registrations.png", "Step 2 \u2014 registrations reviewed and verified by PMC compliance.")
    w.img("r03-help.png", "Step 4 \u2014 Help centre linked to the training manual sections.")

    w.h("C2. Insurance and liability (your point 10)", 14)
    w.q("Contractual responsibilities, professional liability, cyber insurance, indemnities and limitations of liability.")
    w.p("These are contractual matters rather than software controls. PMC Managers will confirm them in the "
        "master services agreement. The proposed framework is:")
    w.table(["Item", "Proposed position (to be confirmed)"], [
        ("Professional indemnity insurance", "[Amount] per claim, insurer [name]"),
        ("Cyber liability insurance", "[Amount] per claim, insurer [name]"),
        ("PMC Managers responsible for", "Platform availability, security of stored data, correct operation of "
                                         "the controls described here, confidentiality of sealed bids"),
        ("Buyer responsible for", "Tender content, choice of criteria and evaluators, award decision, compliance "
                                  "with its own procurement law, payment to suppliers"),
        ("Supplier responsible for", "Truth of declarations and authenticity of proof documents"),
        ("Limitation of liability", "[e.g. fees paid in the previous 12 months], with standard exclusions "
                                    "(fraud, wilful misconduct, data-protection breach)"),
        ("Indemnities", "Mutual indemnities for breach of confidentiality and data protection"),
    ], widths=[2.1, 4.5])

    w.h("C3. Commercial pricing clarity (your point 11)", 14)
    w.q("The three figures shown for each tier, which price applies to which buyer category, the transaction-fee "
        "calculation, caps, minimum thresholds, currency conversion and taxes.")
    w.p("How the platform calculates fees (built in today):", bold=True)
    w.b("Fee types are kept in one master list: tender fee (paid upfront), tender management fee, tender hosting "
        "fee, and transaction fee (a percentage of the awarded value, charged on completion).", "ENFORCED")
    w.b("Each fee can be fixed or a percentage, and can vary by tender-value band (\u201cslab\u201d), by country "
        "and by industry category. The amount due is calculated by the system from the tender value; nobody types it "
        "in by hand.", "ENFORCED")
    w.b("Fees are charged in the tender's currency. Waivers need a second officer's approval and are recorded in "
        "the exceptions register.", "ENFORCED")
    w.p("Pricing table to replace the three figures in the presentation (for completion by PMC Managers):",
        bold=True)
    w.table(["Tier", "Private-sector buyer", "Public-sector buyer", "Development institution / NGO"], [
        ("[Tier 1]", "[price]", "[price]", "[price]"),
        ("[Tier 2]", "[price]", "[price]", "[price]"),
        ("[Tier 3]", "[price]", "[price]", "[price]"),
    ], widths=[1.3, 1.8, 1.8, 1.7])
    w.table(["Transaction fee rule", "Proposed position"], [
        ("Calculation", "[x]% of the awarded contract value"),
        ("Minimum fee", "[amount] per tender"),
        ("Cap", "[amount] per tender"),
        ("Threshold", "No transaction fee below an awarded value of [amount]"),
        ("Currency conversion", "Charged in the tender currency; conversion, where needed, at [source] rate on "
                                "the award date"),
        ("Taxes", "Prices exclude VAT / GST, added at the rate applicable in the buyer's country"),
    ], widths=[1.8, 4.8])
    w.p("Example: a GBP 1,000,000 award at [1]% would be GBP [10,000], subject to the minimum and cap above.",
        italic=True, color=GREY, size=9.5)
    w.img("r08-gov-fees.png", "Fee waivers: a second officer must approve, and every waiver is recorded.")

    d.add_page_break()
    # ================= D =================
    w.h("Part D \u2014 One tender, end to end (evidence)", 17, GOLD)
    w.p("The screens below follow one tender through the platform in order. Each step names the control that "
        "applies.")
    steps = [
        ("r11-dashboard.png", "Dashboard: every live tender with its stage (criteria \u2192 bids \u2192 opening "
         "\u2192 proof review \u2192 price \u2192 L1 \u2192 award), so delays are visible.", "ENFORCED"),
        ("r12-notices.png", "Notices: tender created for a country; criteria and the publish checklist (document, "
         "dates, at least one mandatory criterion) must be complete before Publish is enabled.", "ENFORCED"),
        ("r24-vendor-bid.png", "Supplier's bids: technical and price envelopes are encrypted and sealed on upload. "
         "The supplier sees only their own bid.", "ENFORCED"),
        ("r14-bidding.png", "Bidding operations: the opening is refused until the deadline and opening time have "
         "passed and every committee member has signed electronically.", "ENFORCED"),
        ("r15-evaluations.png", "Technical evaluation: automatic criteria check, AI proof flags, unanimous "
         "committee decision with comments, conflict declarations.", "ENFORCED"),
        ("r16-l1.png", "Price opening and ranking among qualified bids only; award to L1 in one recorded step.",
         "ENFORCED"),
        ("r17-awards.png", "Award: winning and losing bidders are notified with their own rank and reason.",
         "ENFORCED"),
        ("r26-loser-mybids.png", "Losing supplier's view: the bid shows as not selected, with a Debrief link.",
         "ENFORCED"),
        ("r27-debrief.png", "Debrief: own result, reason and the 5-day complaint window.", "ENFORCED"),
        ("r19-docusign.png", "Contract and release signatures via DocuSign, with two independent signers.",
         "ENFORCED"),
        ("r18-escrow.png", "Escrow release: both signatures required before a payment instruction is issued; the "
         "bank's transfer reference is recorded.", "ENFORCED"),
        ("r23-reports.png", "Stakeholder reports for the buyer, board and lenders.", "ENFORCED"),
        ("r01-trust.png", "Public verification: anyone with audit rights can check that the record has not been "
         "altered.", "VERIFIABLE"),
    ]
    for i, (img, txt, tag) in enumerate(steps, 1):
        w.h(f"Step {i}", 12, GREEN, before=8)
        w.b(txt, tag)
        w.img(img, txt.split(":")[0] + ".", width=5.8)

    d.add_page_break()
    # ================= E =================
    w.h("Part E \u2014 Who is responsible for what", 17, GOLD)
    w.p("You rightly asked us to separate what the platform enforces, what is independently verified, and what "
        "remains the buyer's responsibility.")
    w.table(["Area", "Enforced by the platform", "Independently verifiable", "Buyer's responsibility"], [
        ("Tender rules", "Country templates, mandatory criteria, publish checklist", "\u2014",
         "Choosing the procurement law, thresholds and criteria"),
        ("Bid confidentiality", "Encryption, sealed envelopes, price withheld by the server", "Planned penetration test",
         "Keeping committee credentials secure"),
        ("Opening", "Deadline, opening time, all-member e-signature", "Audit ledger + public verification",
         "Appointing the committee"),
        ("Evaluation", "Criteria check, AI flags, unanimous proof decisions, conflict declarations, price only "
         "after technical", "Audit ledger", "Competent evaluators; final judgement"),
        ("Award", "Ranking among qualified bids; recorded award; notices to all bidders", "Audit ledger",
         "The award decision and contract"),
        ("Complaints", "Debrief, 5-day window, integrity holds, recorded appeals", "Audit ledger",
         "Final appeal body and governing law"),
        ("Payments", "Dual-signed escrow release, payment instruction, reference trail", "Bank statement + ledger",
         "Making the bank transfer"),
        ("Records", "Append-only, hash-chained ledger; exceptions register", "Public \u201cVerify a record\u201d",
         "Retention period under local law"),
    ], widths=[1.1, 2.3, 1.5, 1.7])

    w.h("Items requiring PMC Managers' written confirmation", 13)
    for txt in ["Integrity Committee charter (A2)", "Formal bid-challenge procedure and standstill period (A3)",
                "Contractual SLA figures (B4)", "Recovery point / time objectives (B1)",
                "Penetration test and other independent assessments, with dates (B5)",
                "Insurance cover and liability terms (C2)", "Final pricing tiers, transaction-fee figures and taxes (C3)",
                "Country legal opinions and data-processing agreement (A1)"]:
        w.b(txt, "TO CONFIRM")
    w.p("We would welcome the opportunity to walk you through the live platform.", italic=True)

    path = os.path.join(OUT, "PMC_Response_to_Commercial_Review.docx")
    d.save(path)
    return path


def build_internal():
    d = new_doc()
    w = W(d)
    w.h("INTERNAL \u2014 not for the reviewer", 18, AMBER)
    w.p("Notes for the Chairman on the Response to the Commercial & Institutional Review (" + TODAY + ").")

    w.h("1. Placeholders you must fill before sending", 13)
    w.table(["Where", "What is needed"], [
        ("Covering note", "Reviewer's name; your name/signature"),
        ("A1", "Which countries have written legal opinions; a data-processing agreement template"),
        ("A2", "Committee size, appointing body, term, chair profile (all shown in [brackets])"),
        ("B1", "RPO / RTO figures you are willing to commit to"),
        ("B4", "Support hours, response times, maintenance window"),
        ("B5", "Target dates for penetration test / ISO 27001 readiness / process review"),
        ("C1", "Typical onboarding timeline"),
        ("C2", "Insurer, cover amounts, liability cap"),
        ("C3", "The actual tier prices. The reviewer refers to \u201cthree figures per tier\u201d in the "
               "presentation you sent; that presentation was not shared with us, so the table is blank. Fill it with "
               "one price per buyer category so the three figures are explained."),
    ], widths=[1.2, 5.4])

    w.h("2. Honest gaps (we have stated these openly in the reply)", 13)
    for txt in [
        "No independent penetration test or certification yet. Do not let anyone describe the platform as "
        "\u201ccertified\u201d until reports exist.",
        "Two-factor sign-in exists but is NOT compulsory by default for escrow / legal / accounts roles. "
        "Recommend switching it on before institutional launch (a single setting).",
        "No formal multi-stage bid-challenge / standstill module yet; today complaints run through the debrief, the "
        "5-day Messages window, integrity holds and appeals. A dedicated module can be built.",
        "No ready-made ERP connectors (SAP / Oracle / Dynamics). Exports and the web interface exist; connectors "
        "are per-buyer work.",
        "Sanctions screening: the PMC Manager → Vindex → World-Check One link is not built yet; until it is, "
        "screening is manual only.",
        "Backups: confirm the AWS database backup schedule and that a test restore has been done before quoting "
        "RPO/RTO.",
        "Insurance and liability are entirely contractual; nothing in the software covers them.",
    ]:
        w.b(txt)

    w.h("3. Points where we are stronger than the reviewer may assume", 13)
    for txt in [
        "Opening rules are enforced by the server (deadline, opening time, every committee member's signature), "
        "not by procedure.",
        "Price is withheld by the server, and the AI never sees prices.",
        "The audit ledger is publicly verifiable today (Trust & security page), with 0 breaks shown.",
        "Every manual override is recorded in a single exceptions register.",
        "Losing bidders get an automatic, private debrief with their rank and reason.",
    ]:
        w.b(txt)

    w.h("4. Suggested next builds (if you want to close gaps in software)", 13)
    for txt in ["Formal bid-challenge module with standstill timer and committee review",
                "Compulsory two-factor sign-in for high-risk roles",
                "Pricing tier page generated from the fee master, so the published prices always match billing"]:
        w.b(txt)
    path = os.path.join(OUT, "PMC_Internal_Note_on_Review_Response.docx")
    d.save(path)
    return path


if __name__ == "__main__":
    print(build_reply())
    print(build_internal())
