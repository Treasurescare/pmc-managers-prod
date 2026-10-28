"""Builds the customer-facing governance due-diligence hand-over document (DOCX)."""
import os, json
from datetime import datetime
from docx import Document
from docx.shared import Pt, Inches, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

IMG = "/tmp"
GREEN = RGBColor(0x1b, 0x4d, 0x3e)
GREY = RGBColor(0x55, 0x55, 0x55)
AMBER = RGBColor(0xb0, 0x6a, 0x00)
RED = RGBColor(0xb0, 0x00, 0x00)

doc = Document()
styles = doc.styles
styles["Normal"].font.name = "Calibri"
styles["Normal"].font.size = Pt(10.5)


def h(text, size=15, color=GREEN, space_before=10, space_after=4):
    p = doc.add_paragraph()
    p.space_before = Pt(space_before)
    r = p.add_run(text)
    r.bold = True
    r.font.size = Pt(size)
    r.font.color.rgb = color
    p.paragraph_format.space_before = Pt(space_before)
    p.paragraph_format.space_after = Pt(space_after)
    return p


def para(text, color=None, italic=False, size=10.5, bold=False):
    p = doc.add_paragraph()
    r = p.add_run(text)
    r.italic = italic
    r.bold = bold
    r.font.size = Pt(size)
    if color:
        r.font.color.rgb = color
    return p


def bullet(text, color=None):
    p = doc.add_paragraph(style="List Bullet")
    r = p.add_run(text)
    if color:
        r.font.color.rgb = color
    return p


def status(label, color):
    p = doc.add_paragraph()
    r = p.add_run("Status: ")
    r.bold = True
    r2 = p.add_run(label)
    r2.bold = True
    r2.font.color.rgb = color


def image(name, caption):
    path = os.path.join(IMG, name)
    if os.path.exists(path):
        doc.add_picture(path, width=Inches(6.4))
        last = doc.paragraphs[-1]
        last.alignment = WD_ALIGN_PARAGRAPH.CENTER
        cap = doc.add_paragraph()
        cr = cap.add_run("Evidence: " + caption)
        cr.italic = True
        cr.font.size = Pt(8.5)
        cr.font.color.rgb = GREY
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER


# ---------- Title page ----------
t = doc.add_paragraph()
t.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = t.add_run("PMC Managers")
r.bold = True
r.font.size = Pt(26)
r.font.color.rgb = GREEN
st = doc.add_paragraph()
st.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = st.add_run("Governance & Integrity Controls")
r.bold = True
r.font.size = Pt(18)
sub = doc.add_paragraph()
sub.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = sub.add_run("Response to the Portal Due-Diligence Questionnaire")
r.font.size = Pt(13)
r.font.color.rgb = GREY
d = doc.add_paragraph()
d.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = d.add_run("Prepared: " + datetime.now().strftime("%d %B %Y") + "  ·  Platform: www.pmcmanagers.com")
r.font.size = Pt(10)
r.font.color.rgb = GREY

doc.add_paragraph()
para("This document responds point-by-point to the integrity and governance questions raised. "
     "Each answer states how the control actually works in the platform and, where relevant, shows "
     "evidence captured directly from the live system. We have deliberately distinguished controls "
     "that are fully enforced in software from those that are policy matters or still in build, so "
     "the picture is complete and accurate.", italic=True)

# Legend
h("Status key", size=12)
bullet("ENFORCED — built into the software and demonstrated below")
bullet("IN PROGRESS — framework in place; live third-party integration being completed")
bullet("POLICY — a contractual / organisational matter rather than a software control")

# ---------- Summary table ----------
h("Summary", size=14)
rows = [
    ("Two-cover sealing (technical vs financial)", "ENFORCED"),
    ("System gate: financial opens only after technical clearance", "ENFORCED"),
    ("Tamper-evident audit ledger + public verification", "ENFORCED"),
    ("AI tools blocked from financial data", "ENFORCED"),
    ("Manual-exceptions register", "ENFORCED"),
    ("Buyer public/private classification (two-person verify)", "ENFORCED"),
    ("Integrity committee + collusion indicators + recorded override", "ENFORCED"),
    ("Fee-waiver maker-checker control", "ENFORCED"),
    ("Per-country legal register (board-visible)", "ENFORCED"),
    ("Incident register + published service standard (SLA)", "ENFORCED"),
    ("Escrow signer independence + dual signature", "ENFORCED"),
    ("Supplier rating / reputation", "ENFORCED"),
    ("KYC / AML / sanctions screening (Refinitiv World-Check One)", "IN PROGRESS"),
    ("Introducer-commission conflict checks", "IN PROGRESS"),
    ("Platform liability / remedy", "POLICY"),
]
table = doc.add_table(rows=1, cols=2)
table.style = "Light Grid Accent 1"
hdr = table.rows[0].cells
hdr[0].paragraphs[0].add_run("Control").bold = True
hdr[1].paragraphs[0].add_run("Status").bold = True
for name, stt in rows:
    c = table.add_row().cells
    c[0].text = name
    rr = c[1].paragraphs[0].add_run(stt)
    rr.bold = True
    rr.font.color.rgb = GREEN if stt == "ENFORCED" else (AMBER if stt == "IN PROGRESS" else GREY)

doc.add_page_break()

# ---------- 1. Two-cover ----------
h("1. Two-cover separation — technical vs financial", size=14)
para("Q: Is the price-blinding real and database/server-enforced, or only hidden on screen? Is there a "
     "hard system gate that prevents the financial envelope from being opened before technical evaluation "
     "is complete? Who can override the separation, and is every override recorded?", italic=True, color=GREY)
para("Response", bold=True)
bullet("Price, commercial notes and all commercial documents are stripped server-side from the API response "
       "for technical evaluators, and for everyone, until the financial envelope is formally opened. The "
       "figures never reach the browser, so they cannot be recovered client-side.")
bullet("Opening the financial envelope is blocked by the server (HTTP 412 \u201cfinancial locked\u201d) until "
       "technical clearance has been recorded. The gate applies to administrators too \u2014 there is no \u201cskip "
       "technical\u201d path.")
bullet("Every technical clearance and every financial open writes an actor-stamped entry to the tamper-evident "
       "audit ledger, so any override is permanently recorded.")
bullet("The AI bid-comparison tool has been changed so it no longer receives the price at all (verified by the "
       "automated test test_ai_compare_scope_has_no_price).")
status("ENFORCED", GREEN)
para("Note: the sealing is role-based server redaction that we have functionally tested. We recommend an "
     "independent penetration test before any formal certification statement.", italic=True, color=GREY)

# ---------- 2. Audit ledger ----------
h("2. Audit ledger", size=14)
para("Q: Is the ledger truly immutable? Can an administrator edit it? Can an outside party verify it?",
     italic=True, color=GREY)
para("Response", bold=True)
bullet("Every significant action is written to an append-only ledger where each entry is hashed together with "
       "the previous entry (SHA-256 hash chain).")
bullet("It is tamper-EVIDENT: if any stored row were altered, the chain no longer validates and the exact "
       "broken entry is pinpointed. We state this honestly rather than claim data \u201ccannot be changed\u201d.")
bullet("Any bidder or auditor can independently verify a single record via the public endpoint "
       "/api/v1/audit/verify-record (no login required), surfaced on the public Trust & Security page.")
status("ENFORCED (tamper-evident)", GREEN)

# ---------- 3. Exceptions register ----------
h("3. Manual-exceptions register", size=14)
para("Q: Where is the record of manual exceptions \u2014 KYC bypasses, skipped stages, overrides \u2014 kept, and "
     "is it reviewable?", italic=True, color=GREY)
para("Response", bold=True)
bullet("Every bypass, waiver and override is written to a single reviewable register and mirrored to the audit "
       "ledger, with the exception type, the target, the officer responsible, the reason and the timestamp.")
status("ENFORCED", GREEN)
image("gov_exceptions.png", "Manual-exceptions register in the admin console (demo data).")

# ---------- 4. Buyer classification ----------
h("4. Buyer public / private classification", size=14)
para("Q: How do you confirm whether a buyer is public or private, and who checks that this has been classified "
     "correctly?", italic=True, color=GREY)
para("Response", bold=True)
bullet("One officer classifies the buyer (public / private) with the basis; a SECOND, different officer must "
       "verify it. The person who classified cannot verify their own entry (segregation of duties, enforced "
       "server-side \u2014 returns HTTP 403).")
bullet("A verified classification is locked and cannot be silently reset; the full history is retained.")
status("ENFORCED", GREEN)
image("gov_buyer.png", "Buyer classification \u2014 note the different Classified-by vs Verified-by officers (demo data).")

# ---------- 5. Integrity + collusion ----------
h("5. Integrity committee & collusion indicators", size=14)
para("Q: How are hidden links between bidders (possible collusion) detected? Can a senior person override the "
     "integrity committee, and is that recorded?", italic=True, color=GREY)
para("Response", bold=True)
bullet("Any officer can raise an integrity hold on a notice; the committee reviews and votes; cases follow a "
       "strict state machine so a resolved or overridden case cannot be silently changed.")
bullet("A senior officer may overrule the committee, but ONLY on the record: the override, its author and its "
       "reason are written to the ledger, logged in the exceptions register, and flagged as publicly "
       "disclosable.")
bullet("A collusion-indicator scan highlights bidders on the same notice that share an email domain, phone, "
       "registered address or bank account, and bidders that repeatedly bid together. These are prompts for "
       "human review, explicitly NOT proof of wrongdoing.")
status("ENFORCED", GREEN)
image("gov_integrity.png", "Integrity case showing a recorded, disclosed senior override (demo data).")

# ---------- 6. Fee waivers ----------
h("6. Fee waivers", size=14)
para("Q: How do you prevent fee waivers being used to favour particular parties?", italic=True, color=GREY)
para("Response", bold=True)
bullet("Fee waivers follow a maker-checker control: the officer who requests a waiver cannot approve it \u2014 a "
       "different officer must decide (enforced server-side, HTTP 403).")
bullet("Every approved waiver is automatically recorded in the exceptions register with the reason and both "
       "officers named.")
status("ENFORCED", GREEN)
image("gov_fees.png", "Fee-waiver workflow with maker-checker rule (demo data).")

# ---------- 7. Legal register ----------
h("7. Per-country legal register", size=14)
para("Q: Is legal approval for operating in each country recorded and visible to the Board?", italic=True, color=GREY)
para("Response", bold=True)
bullet("A board-visible register records the legal status (approved / pending / blocked) for each country, the "
       "approving counsel and the note, with a full update trail.")
status("ENFORCED", GREEN)
image("gov_legal.png", "Per-country legal register (demo data).")

# ---------- 8. Incidents + SLA ----------
h("8. Incident disclosure & published service standard", size=14)
para("Q: What happens if a live public bid-opening fails, and what is your service standard?", italic=True, color=GREY)
para("Response", bold=True)
bullet("Live bid-opening rooms stream over SSE with an automatic polling fallback; if streaming fails the "
       "opening continues on a manual, audit-logged close, so no bid is lost.")
bullet("Incidents affecting a bid deadline or opening are logged and, where bidders are affected, publicly "
       "disclosed. A published service standard (SLA) is served to the public with no login required.")
status("ENFORCED", GREEN)
image("gov_incidents.png", "Incident register with public disclosure (demo data).")
try:
    sla = json.load(open("/tmp/gov_sla.txt"))
    para("Published service standard (live, public endpoint /api/v1/governance-controls/public/incidents):", bold=True)
    for k, v in sla.get("sla", {}).items():
        bullet(f"{k.replace('_', ' ').title()}: {v}")
except Exception:
    pass

doc.add_page_break()

# ---------- 9. KYC honest ----------
h("9. KYC / AML / sanctions screening", size=14, color=AMBER)
para("Q: Do you perform sanctions, beneficial-ownership and debarment checks, and are they kept up to date?",
     italic=True, color=GREY)
para("Response (full transparency)", bold=True)
bullet("The KYC framework is in place \u2014 case records, manual-decision controls (with every manual override "
       "recorded in the exceptions register), and risk levels.")
bullet("Live screening is being connected to Refinitiv World-Check One (LSEG), to which the client holds a "
       "subscription. Until that integration is completed and switched on, the platform is NOT performing live "
       "sanctions / PEP / beneficial-ownership / debarment screening. We are stating this plainly rather than "
       "representing it as already live.")
status("IN PROGRESS \u2014 Refinitiv World-Check One integration being completed", AMBER)

# ---------- 10. Escrow ----------
h("10. Escrow independence, dual signature & secure links", size=14)
para("Q: Is the escrow sign-off independent? Does the two-signature rule cover commission/franchise payments or "
     "only buyer escrow? Are the e-mail \u201cmagic links\u201d protected?", italic=True, color=GREY)
para("Response", bold=True)
bullet("Escrow signer independence is enforced: the PMC officer and the escrow-institution officer cannot be "
       "the same person (rejected at account level and by the e-signature envelope, which uses two independent "
       "signers).")
bullet("Escrow releases, refunds and fee-outs require BOTH signatures before funds move.")
bullet("Password-reset links are single-use and expire after one hour; sessions are time-limited.")
status("ENFORCED (escrow)", GREEN)
para("In build: a dedicated commission / franchise payout module (so the dual-signature rule extends there "
     "too) and tightening of the institution onboarding link to single-use. Disclosed for completeness.",
     italic=True, color=GREY)

# ---------- 11. Supplier rating ----------
h("11. Supplier rating & reputation", size=14)
para("Response", bold=True)
bullet("The platform operates a supplier rating system (peer, PMC and buyer reviews) with an approved-only "
       "public aggregate, anti-self-rating protection and reputation tiers.")
status("ENFORCED", GREEN)

# ---------- 12. Remaining ----------
h("12. Remaining items", size=14)
para("Introducer-commission conflict checks", bold=True)
bullet("No introducer-commission module exists yet; it will be added alongside the commission payout module. "
       "(IN PROGRESS)")
para("Platform liability / remedy for harm", bold=True)
bullet("This is a contractual and organisational matter addressed in the platform's terms and insurance "
       "arrangements rather than a software control. (POLICY)")

# ---------- Verification appendix ----------
doc.add_page_break()
h("Appendix \u2014 How these controls were verified", size=14)
para("The controls above are covered by an automated regression test suite that runs against the live backend. "
     "Latest run:", )
try:
    txt = open("/tmp/gov_pytest.txt").read().strip().splitlines()
    summary = [l for l in txt if "passed" in l or "failed" in l]
    para(summary[-1] if summary else txt[-1], bold=True, color=GREEN)
except Exception:
    pass
para("Key automated checks include:")
for name in [
    "Financial data (price) is never sent to the AI comparison tool",
    "Buyer classification: the classifier is blocked (403) from verifying their own entry",
    "Fee waiver: the requester is blocked (403) from approving their own waiver",
    "Integrity: a resolved/overridden case cannot be silently re-resolved",
    "Senior override is written to the exceptions register",
    "Public incident/SLA endpoint exposes only safe fields (no internal data)",
]:
    bullet(name)
para("All demonstration records shown in the screenshots were clearly marked (DEMO) and removed after capture; "
     "the audit ledger is append-only by design.", italic=True, color=GREY)

out = "/app/frontend/public/downloads/PMC_Governance_DueDiligence_Response.docx"
doc.save(out)
print("SAVED", out)
