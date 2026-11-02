"""Reply to the data-room inconsistencies + the 'not yet a complete global framework' comment."""
import os
import sys

from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

sys.path.insert(0, os.path.dirname(__file__))
from build_reviewer_reply import GOLD, GREEN, GREY, TODAY, W, legend, new_doc  # noqa: E402

OUT = "/app/frontend/public/downloads/PMC_Reply_Inconsistencies_and_Framework.docx"


def main():
    d = new_doc()
    w = W(d)
    t = d.add_paragraph()
    t.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = t.add_run("PMC Managers")
    r.bold = True
    r.font.size = Pt(24)
    r.font.color.rgb = GREEN
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    p.add_run("Reply to the data-room review: five inconsistencies and the global framework").font.size = Pt(14)
    p = d.add_paragraph()
    p.alignment = WD_ALIGN_PARAGRAPH.CENTER
    rr = p.add_run("Prepared " + TODAY + "  \u00b7  THE PMC MANAGERS LTD (company no. 17031540)")
    rr.font.size = Pt(9.5)
    rr.font.color.rgb = GREY

    w.h("Covering note", 13)
    w.p("Dear [Reviewer name],")
    w.p("Thank you for your two further comments. Part 1 resolves each of the five inconsistencies you identified "
        "between our documents and states one binding position for each, which will replace the earlier wording "
        "in every document in the data room. Part 2 responds to your observation that our document explains what "
        "PMC Manager does, why buyers should use it and how it earns revenue, but not yet how it is secured, "
        "governed, regulated, implemented and supported across different countries.")
    w.p("Yours sincerely,\nHarneet Kaur\nDirector, THE PMC MANAGERS LTD")
    legend(w, shots=False)

    d.add_page_break()
    w.h("Part 1 \u2014 Resolving the five inconsistencies", 16, GOLD)
    w.table(["#", "Topic", "Binding position", "Status"], [
        ("1", "Screening provider", "Refinitiv World-Check One (LSEG). Not yet live.", "IN PROGRESS"),
        ("2", "Escrow / who holds money", "PMC never holds funds. Banks hold and move money; the platform enforces "
         "dual-signed instructions and records the bank reference.", "ENFORCED"),
        ("3", "Fee from the winning supplier", "None on public tenders. Optional 0.30% only on private tenders, "
         "chosen by the buyer and shown before bidding.", "TO CONFIRM"),
        ("4", "Paid visibility", "Kept, but firewalled from tender execution.", "ENFORCED"),
        ("5", "India retainer", "Removed as a minimum. Licence only; retainer becomes an optional managed service.",
         "TO CONFIRM"),
    ], widths=[0.3, 1.5, 3.7, 1.1], tag_col=3)

    w.h("1. Screening provider: \u201cVindex\u201d, \u201cWindex\u201d or Dow Jones?", 13)
    w.b("The correct provider is Refinitiv World-Check One, now operated by LSEG (London Stock Exchange Group; "
        "Refinitiv was formerly part of Thomson Reuters). \u201cVindex\u201d and \u201cWindex\u201d were drafting "
        "errors, and Dow Jones is not a provider we use. All three references will be removed.", "TO CONFIRM")
    w.b("Status: the World-Check One connection is not built yet; it will be added once the LSEG subscription "
        "is signed. Until then, sanctions and adverse-media checks are carried out manually by PMC compliance during "
        "supplier verification, and the verification decision is recorded in the audit ledger.", "IN PROGRESS")
    w.b("For the data room: we will add the LSEG/Refinitiv order form once signed. We have no Dow Jones contract "
        "and will not claim one.", "TO CONFIRM")

    w.h("2. Escrow: \u201cdual-signature EMD escrow\u201d versus \u201cPMC does not hold money\u201d", 13)
    w.p("Both statements are true; the earlier wording was imprecise. The position is:")
    w.b("PMC Manager never holds, pools or moves money. Deposits (EMD) and contract payments sit in a bank account "
        "held by the buyer or by a licensed escrow/payments partner.", "ENFORCED")
    w.b("What the platform does is control the instruction. A release needs two separate authorised signatures; "
        "the same person cannot sign twice; the platform then issues a payment instruction; the bank makes the "
        "transfer; the bank's reference is recorded back against the instruction; and each step goes to the "
        "tamper-evident audit ledger.", "ENFORCED")
    w.b("For card and online payments (for example tender fees) we use Stripe, a licensed payment provider; "
        "funds settle directly to the receiving account.", "ENFORCED")
    w.b("Wording to use from now on: \u201cDual-signature escrow control over funds held by the buyer's bank or a "
        "licensed escrow partner.\u201d The named partner bank for each country will be listed in the data room.",
        "TO CONFIRM")

    w.h("3. A success fee from the winning supplier", 13)
    w.b("Public tenders: no fee of any kind is taken from the winning supplier. This keeps the principle in our "
        "strategy report and avoids any perception that suppliers pay to win public work.", "TO CONFIRM")
    w.b("Private tenders only: a private buyer may choose to pass a 0.30% service charge on the awarded value to "
        "the winning bidder. This is allowed only if it is written into the tender before publication, so every "
        "bidder sees it and can price it in. It can never be added after bids are opened.", "TO CONFIRM")
    w.b("The platform already calculates fees from the published fee settings and shows them on the public "
        "pricing page, so what is published is what is charged. A 0.30% winner charge is not yet configured and "
        "will be added only on these terms.", "IN PROGRESS")

    w.h("4. Paid visibility and procurement intelligence packages", 13)
    w.p("We keep these packages, but they are firewalled from tender execution:")
    w.b("Packages may buy market data, analytics, training and promotion of a supplier's company profile on the "
        "marketplace and directory.", "TO CONFIRM")
    w.b("They can never affect criteria, qualification, proof review, scoring, price ranking or award. The "
        "evaluation and ranking code reads only the bid, the tender's criteria and the committee's decisions; it "
        "does not read any package or subscription data.", "ENFORCED")
    w.b("Every evaluation step is in the audit ledger, so an auditor can confirm that no paid feature took part.",
        "VERIFIABLE")
    w.b("On public tenders, any registered and verified supplier may bid, whether or not it holds a paid package. "
        "We are reviewing the supplier category settings so that paid category options can never restrict "
        "access to a public tender.", "IN PROGRESS")
    w.b("Paid promotion will always be labelled \u201cPromoted\u201d and will never appear inside a tender notice or "
        "the bidder list.", "TO CONFIRM")

    w.h("5. India pricing: \u20b915 lakh retainer minimum", 13)
    w.b("The \u20b915 lakh a year retainer is withdrawn as a minimum. The India price is the licence band "
        "(\u20b920,000 to \u20b91.99 lakh, by tier) and nothing else is compulsory.", "TO CONFIRM")
    w.b("A retainer becomes an optional managed service: PMC staff running tenders on the buyer's behalf, priced "
        "per engagement. Buyers who run their own tenders pay the licence only.", "TO CONFIRM")
    w.b("India platform fees today, from the live fee settings: tender fee INR 1,000 flat; tender management fee "
        "3% up to 5 million and 2% on the value above. These figures are configurable.", "ENFORCED")
    w.b("The strategy report figure (about $8,100 a year, \u20b96.75 lakh) and the licence band will be "
        "reconciled into one India price table. [Final India tier table to be inserted.]", "TO CONFIRM")

    d.add_page_break()
    w.h("Part 2 \u2014 From corporate introduction to global platform framework", 16, GOLD)
    w.p("We accept the observation. The introduction explains what PMC Manager does, why buyers should use it and "
        "how it earns revenue. It does not yet set out how the platform is secured, governed, regulated, "
        "implemented and supported in each country. We have prepared that framework as a companion document, "
        "\u201cResponse to the Commercial & Institutional Review\u201d, with screenshots of the live platform as "
        "evidence. Its structure:")
    w.table(["Your question", "Where it is answered", "Summary"], [
        ("How is it secured?", "Section B1, B2",
         "Encrypted sealed bid envelopes; server-enforced opening; role-based access; two-factor sign-in; "
         "tamper-evident SHA-256 audit ledger with a public check page."),
        ("How is it governed?", "Section A2, A3, A4",
         "Integrity committee workflow, conflict-of-interest declarations, unanimous proof decisions, bid "
         "challenges with a standstill period, appeal to a senior officer, and an exceptions register."),
        ("How is it regulated?", "Section A1, C2",
         "Per-country legal register, country templates and fee rules, data-protection controls, e-signature, "
         "and a contractual split of responsibilities."),
        ("How is it implemented?", "Section C1",
         "Six steps from registration to go-live, with role-based training and a 104-page screenshot manual."),
        ("How is it supported?", "Section B4",
         "Published service standard (99.5% availability target for live openings; critical incidents "
         "acknowledged within 1 hour) and proposed contract service levels."),
        ("Across different countries?", "Below", "Country onboarding model."),
    ], widths=[1.5, 1.2, 3.9])

    w.h("Country onboarding model", 13)
    w.p("A country goes live only after these steps, each recorded in the platform's legal register:")
    w.table(["Step", "What is done", "Status"], [
        ("1. Legal clearance", "Local legal opinion on procurement law, e-signature validity and data protection; "
         "the country is marked approved, pending or blocked.", "ENFORCED"),
        ("2. Data protection", "Data-processing agreement with the buyer; local data-residency requirement "
         "confirmed (hosting region chosen accordingly).", "TO CONFIRM"),
        ("3. Money flow", "Named partner bank or licensed escrow provider; PMC never holds funds.", "TO CONFIRM"),
        ("4. Fees and taxes", "Country fee rules and currency configured; local VAT/GST applied on invoices.",
         "ENFORCED"),
        ("5. Templates and criteria", "Country tender templates and criteria library loaded; reviewed by the buyer's "
         "procurement lead.", "ENFORCED"),
        ("6. Screening", "World-Check One screening switched on for the country once live.", "IN PROGRESS"),
        ("7. Support", "Support hours in the local time zone and an escalation contact.", "TO CONFIRM"),
    ], widths=[1.4, 4.0, 1.2], tag_col=2)

    w.h("What we will add to the data room", 13)
    for txt in ["This reply, replacing the five conflicting statements in all documents",
                "The \u201cResponse to the Commercial & Institutional Review\u201d with screenshots",
                "LSEG / Refinitiv World-Check One order form (when signed)",
                "Partner bank / escrow agreement for each launch country",
                "One reconciled price table per country, including India",
                "Independent penetration-test report (when issued)"]:
        w.b(txt, "TO CONFIRM")
    w.p("We would welcome a walk-through of the live platform at your convenience.", italic=True)
    d.save(OUT)
    print(OUT)


if __name__ == "__main__":
    main()
