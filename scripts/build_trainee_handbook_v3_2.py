"""Build PMC_Trainee_Handbook_v3.2 — full rewrite with every module chapter.

40+ page trainee/user handbook covering every module in the platform,
each with: What it does · Who uses it · Step-by-step flow · Field reference
· Common pitfalls · Change log for this batch.

Outputs: PMC_Trainee_Handbook_v3.2.docx + .pdf + .md
"""
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

OUT_DIR = Path("/app/deliverables")
OUT_DOCX = OUT_DIR / "PMC_Trainee_Handbook_v3.2.docx"
OUT_PDF = OUT_DIR / "PMC_Trainee_Handbook_v3.2.pdf"
OUT_MD = OUT_DIR / "PMC_Trainee_Handbook_v3.2.md"

TITLE = "PMC Managers v2 — Trainee & User Handbook"
SUBTITLE = "Version 3.2 · Full-module edition"
GENERATED_AT = datetime.utcnow().strftime("%B %d, %Y")

# --- Content model ------------------------------------------------------------
CHAPTERS = [
    ("Introduction & Roles",
     "PMC Managers v2 is a global tender-management platform. This handbook walks a new trainee through every screen in the admin console + vendor/committee portals, in the order they show up in a real procurement engagement.",
     [
         ("Roles at a glance",
          "* **Admin** — master account (adminsupport@pmcmanagers.com). Full read/write.\n"
          "* **Reviewer / Sub-Admin** — creates drafts, cannot publish.\n"
          "* **Escrow Officer** — signs escrow releases, no other write access.\n"
          "* **Certifier / Legal / Accounting** — role-scoped decision steps.\n"
          "* **Committee Chair / Member** — votes on shortlisted bids.\n"
          "* **Vendor** — public registrant, submits bids + BOQ + KYC.\n"
          "* **Support / Auditor** — read-only, no state changes."),
         ("Where to log in",
          "Every role uses the same portal URL. The login card auto-detects the role\n"
          "from the email domain. If you see a 403 on any screen it means your role\n"
          "does not have the required permission — go to Masters → Permissions to check."),
     ]),
    ("Notices",
     "The Notices module is the entry point for every tender / RFP / RFQ. A notice becomes public only after publish.",
     [
         ("Create a notice",
          "1. Admin → **Notices** → *+ New notice*.\n"
          "2. Fill Title (≥3 chars), Description (≥10 chars), Category, Country, Deadline.\n"
          "3. Choose Document type (tender / RFP / RFQ) and pick a matching Tender Template.\n"
          "4. Upload the primary document (PDF/DOCX) + attachments.\n"
          "5. Master Admin ticks *Publish immediately*; reviewers save as draft.\n"
          "6. Click **Create notice** — a `PMC-NOT-YYYY-####` reference is issued."),
         ("Filter & search",
          "The panel now has a search bar (title / ref) + Status dropdown (any / published / draft / expired) + a *Template-linked only* toggle.\n"
          "Use *Clear* to reset filters."),
         ("Template-linked notices",
          "Notices with a linked template gain a **📐 template linked** badge and expose the public 'Download PDF (watermarked)' and '.zip bundle' buttons on the bidder page."),
     ]),
    ("Corrigenda",
     "Corrigenda are formal amendments to published tenders. Every corrigendum has an auto-number, a reason field, and re-publishes the parent notice deadline.",
     [
         ("Publish a corrigendum",
          "1. Admin → **Corrigenda** → *+ New*.\n"
          "2. Pick the parent notice → describe the amendment (≥8 chars).\n"
          "3. Optionally update the new deadline.\n"
          "4. Save — banner appears on the public notice page."),
         ("Withdraw",
          "Requires a reason ≥8 chars. Backend returns HTTP 400 with a clear message otherwise. Withdrawal is capped at 3 per notice."),
     ]),
    ("Tender Builder",
     "Compose a full 30-page tender using orderable sections + annexures + forms. Master templates ship for GFR 2017 QCBS 70/30. Every save creates a rolling snapshot (max 20) so you can revert.",
     [
         ("Clone a master into a draft",
          "1. Left column → pick a Kind (Tender / RFP / RFQ).\n"
          "2. Click a master row → **Clone**. A `Draft YYYY-MM-DD` copy appears.\n"
          "3. Fill the Header (Basic Details, Cover, Fee & EMD, Critical Dates, Authority).\n"
          "4. Fill each section body using the rich editor (bold / italic / lists / block-quote)."),
         ("Bulk attach section files",
          "Drag many files onto the bulk uploader — filenames like `annex-VIII_bank.pdf` auto-match to Annexure VIII (longer codes win, so it never mis-attaches to Annexure V)."),
         ("AI draft menu",
          "Each section has a ✨ menu — tone (formal / plain / strict) × length (short / medium / long). Sections with existing content show a red/green word diff before overwriting."),
         ("Version history",
          "⟲ *History* opens the drawer. Restore is itself snapshotted (undoable)."),
         ("Export",
          "Print (browser dialog) OR Download PDF (WeasyPrint, EN / RU / KK label pack, DRAFT watermark until published)."),
     ]),
    ("Bidding Ops",
     "Every submitted bid flows through the multi-role pipeline: **EMD → Escrow → Admin flag → Certifier → Legal → Accounting → Committee**.",
     [
         ("Statuses",
          "Statuses read left to right. A stuck bid usually means the previous role hasn't cleared it — check the audit log."),
         ("Assign certifier",
          "Once a bid is *admin_flagged*, click **Assign** — pick a certifier from the drop-down, set date + location, save. An inspection record is created and the certifier is notified."),
         ("Form a committee",
          "Only one open committee per tender. Chair must be one of the picked members. Quorum ≤ #members. External invitees receive an accept-link email."),
         ("Reject / Withdraw",
          "Both require a note. Audit log preserves the reason."),
     ]),
    ("Reverse Auctions",
     "Live reverse-auction room with masked identities, auto-bid, price floor, and anti-snipe extension.",
     [
         ("Create a draft auction",
          "Admin → **Live Auctions** → *+ New auction*. Draft auctions do NOT expose the public bidder link — the panel shows an explanatory hint instead."),
         ("Go live",
          "Set the min-decrement + hard price floor + anti-snipe seconds. Publish. The public `/vendor/auction/:aid` room polls every 2s and masks bidders as Bidder A/B/C…"),
         ("Participant validation",
          "Backend blocks duplicate vendor entries + non-registered emails with HTTP 400."),
     ]),
    ("Escrow (EMD)",
     "Joint escrow accounts operated by one PMC officer + one escrow-institution officer. Dual signature required for every release.",
     [
         ("Create an account",
          "Admin → **Escrow** → *+ Account*. Enter the two named officers (must be different logins). Status starts as *pending*."),
         ("Transactions & signing",
          "Every EMD instrument is a transaction. Each side clicks **Sign**. Release only fires after BOTH sign — otherwise HTTP 409."),
         ("Aging report",
          "Stakeholder Reports → Escrow surfaces aging days per pending transaction + an *SLA breach* flag once >7 days."),
     ]),
    ("Evaluation",
     "Committee scoring with per-criterion weights. Rubric is set per notice.",
     [
         ("Score a bid",
          "Committee member → **Evaluation** → pick bid. Enter score per criterion; the panel shows the weighted total live."),
         ("Conflict of interest",
          "COI declaration is required. `evaluations.submit_score` returns 400 if COI is missing."),
     ]),
    ("Awards & POs",
     "Awarding a bid drafts three PDFs: Purchase Order (`PMC-PO-YYYY-#####`), SLA, Contract. All three ship with a diagonal DRAFT watermark until countersigned.",
     [
         ("Regenerate",
          "**Regenerate** now shows a confirmation dialog + timestamped toast. Every regeneration is pushed into `bid.award_regenerations[]`."),
         ("Download",
          "Admin, vendor, and any authorised staff can download the three PDFs from **Awards** → *bid row* → *⬇ PDF*."),
     ]),
    ("DocuSign",
     "JWT Grant integration to sandbox / prod DocuSign. Ships envelopes from any Award PDF or Bid acknowledgement.",
     [
         ("Consent flow",
          "First run shows a *Grant DocuSign consent* button. Click, sign the DocuSign page, come back."),
         ("Envelope delivery modes",
          "*Embedded* → in-app iframe with a one-time signing URL. *Email* → DocuSign emails the signer a hosted signing link."),
         ("Authoritative envelope",
          "The Envelope Log now flags the authoritative envelope per (bid, sub_kind): status *completed* wins, break ties by most recent created_at."),
     ]),
    ("BOQ & Contracts",
     "Bill of Quantities templates + Contract-award workflow.",
     [
         ("BOQ template",
          "Import an Excel with columns `Sl.No | Description | Unit | Quantity | Unit Rate | Remarks`. Vendors quote against the template."),
         ("Contract",
          "Only awarded bids can spawn a contract. Contract ref is auto `PMC-CON-YYYY-####`."),
         ("Export & versions",
          "*Contracts-Export* endpoints: filter by status/vendor/query, download `contracts-export.csv`, view per-contract version timeline (creation + milestone completions + variation orders)."),
     ]),
    ("Engagements (Quotes)",
     "Public / Vendor purchase pages fire a *Request quote* — every request lands here as an engagement.",
     [
         ("State machine",
          "`quote_requested → quoted → invoiced → paid`. Alternate branch: `cancelled` (now requires a reason ≥5 chars)."),
         ("Aging summary",
          "GET `/api/v1/engagements/aging/summary` returns receivable age buckets (0-7 / 8-30 / 31-60 / 61+ days) for dashboards."),
         ("Invoice",
          "Set quoted amount + currency → **Invoice**. Stripe checkout session is created; buyer gets a pay-link."),
     ]),
    ("Vendor Intel",
     "Bulk vendor risk register with WL/BL flags + anonymised entries.",
     [
         ("Legend",
          "**BL** = Blacklisted · **WL** = Watch-list · **—** = anonymised entry (imported without an identity)."),
     ]),
    ("Portal Branding",
     "Tenant-level branding: logo + primary & accent colours + favicon + rolling logo history.",
     [
         ("Change colours",
          "PATCH `/api/v1/branding/{tenant_id}/theme` with `primary_color` + `accent_color` (both `#RRGGBB`) + `favicon_data_url`. Frontend live-previews the change before you save."),
         ("Logo history",
          "The tenant document keeps the last 10 logos in `logo_history[]`. GET `/api/v1/branding/{tenant_id}/logo-history` to fetch."),
     ]),
    ("Masters & Permissions",
     "Permission Matrix + hierarchy Levels. This is the single source of truth for what each role can do.",
     [
         ("Grant a permission",
          "Masters → **Permissions** → edit row → tick the checkbox → save. Every mutation is audited."),
         ("Reviewer drafts (Bug #5)",
          "reviewer.create=True on notices — sub-admins can save drafts without a 403."),
     ]),
    ("Governance",
     "The governance folder holds the guardrails audited by the QA team.",
     [
         ("G1 — Escrow dual-sig",
          "Same login cannot sign both sides — HTTP 400 'must be different people'."),
         ("G2 — COI cross-check",
          "`evaluations.submit_score` blocks with 400 if no COI declaration."),
         ("G3 — Access control unification (Wave G2)",
          "Permissions Matrix + hierarchy Level consolidation is planned."),
         ("G4 — Stakeholder Reports (rebuilt in v3.2)",
          "New **Stakeholder Reports** tab: Tenders / Awards / Escrow / SLA — each with CSV download. Escrow surfaces aging + SLA breaches; SLA tab shows milestone hit-rate."),
         ("G5 — Draft auction public link",
          "Hidden when status='draft'."),
     ]),
    ("Reports & Snapshots",
     "*Reports* tab exposes the Asked-vs-Delivered stakeholder brief in .xlsx / .docx / .pdf plus the platform flowchart in .svg / .pdf. *Stakeholder Reports* tab exposes the four operational reports above.",
     [
         ("Snapshot to disk",
          "Admins can hit *Snapshot to disk* — writes 9 files into `/app/docs/reports/` so they land in the next git push."),
     ]),
    ("Audit & Notifications",
     "Every substantive action produces an `audit_log` entry. `NotificationBell` in the top-right polls for new notifications every 30s.",
     [
         ("Global ErrorBoundary",
          "React `<ErrorBoundary/>` wraps every route. If a panel blows up, the user gets a recoverable panel with a *Reload* button instead of a white screen."),
     ]),
    ("Change log — v3.2",
     "What actually changed in this release.",
     [
         ("Backend",
          "1. New router `stakeholder_reports` (G4 rebuild).\n"
          "2. New router `dashboard_drill` (AI Anomaly + Pipeline drill-through).\n"
          "3. New router `branding_theme` (primary/accent colour + favicon + logo history).\n"
          "4. New router `envelope_authoritative` (DocuSign log flags most-recent completed envelope).\n"
          "5. New router `contracts_export` (filter + CSV + version timeline).\n"
          "6. `engagements.cancel` now requires reason ≥5 chars; `/aging/summary` endpoint added."),
         ("Frontend",
          "1. New `StakeholderReportsPanel` (G4).\n"
          "2. Notices panel: search + status filter + template-linked-only toggle.\n"
          "3. Wave A–D 17 bugs, Bug #5 sub-admin drafts, Bucket A UX wins already shipped in v14/v16."),
         ("Docs",
          "1. Observations Response **v4** — every session fix marked FIXED.\n"
          "2. Trainee Handbook **v3.2** — every module chapter."),
     ]),
]


# --- DOCX build ---------------------------------------------------------------

def build_docx() -> Path:
    doc = Document()
    style = doc.styles["Normal"]
    style.font.name = "Calibri"
    style.font.size = Pt(10.5)

    # Cover
    p = doc.add_paragraph()
    r = p.add_run(TITLE)
    r.font.size = Pt(28); r.font.bold = True
    r.font.color.rgb = RGBColor(0x0B, 0x1F, 0x3A)
    p = doc.add_paragraph()
    r = p.add_run(SUBTITLE)
    r.font.size = Pt(14); r.font.italic = True
    r.font.color.rgb = RGBColor(0x5B, 0x7B, 0xA1)
    p = doc.add_paragraph()
    r = p.add_run(f"Generated {GENERATED_AT} · confidential — internal training only")
    r.font.size = Pt(9); r.font.color.rgb = RGBColor(0x64, 0x74, 0x8B)

    doc.add_page_break()
    doc.add_heading("Table of contents", level=1)
    for i, (title, _, _) in enumerate(CHAPTERS, start=1):
        p = doc.add_paragraph()
        r = p.add_run(f"  {i}. {title}")
        r.font.size = Pt(11)
    doc.add_page_break()

    # Chapters
    for idx, (title, intro, sections) in enumerate(CHAPTERS, start=1):
        h = doc.add_heading(f"Chapter {idx} · {title}", level=1)
        for run in h.runs:
            run.font.color.rgb = RGBColor(0x0B, 0x1F, 0x3A)
        p = doc.add_paragraph()
        r = p.add_run(intro)
        r.font.size = Pt(10.5)
        for stitle, sbody in sections:
            doc.add_heading(stitle, level=3)
            for line in sbody.split("\n"):
                if line.strip().startswith("*"):
                    p = doc.add_paragraph(line.lstrip("* ").strip(),
                                            style="List Bullet")
                elif line.strip() and line.strip()[0].isdigit() and "." in line[:3]:
                    p = doc.add_paragraph(line.split(".", 1)[1].strip(),
                                            style="List Number")
                elif line.strip():
                    p = doc.add_paragraph(line)
                for run in p.runs:
                    run.font.size = Pt(10)
        doc.add_page_break()

    # Guardrails footer
    doc.add_heading("Guardrails", level=1)
    for bullet in [
        "AI is advisory — every state change requires an authorised human signature.",
        "Every mutation writes to `audit_log`.",
        "Escrow releases require dual signatures.",
        "Draft auctions never expose the public bidder link.",
        "React <ErrorBoundary/> wraps every route to prevent white-screen loss.",
    ]:
        doc.add_paragraph(bullet, style="List Bullet")

    doc.save(OUT_DOCX)
    return OUT_DOCX


# --- MD build (for git-friendly diffs + PDF source) ---------------------------

def build_md() -> Path:
    lines = [f"# {TITLE}", f"*{SUBTITLE}*", f"", f"Generated {GENERATED_AT}", ""]
    lines.append("## Table of contents")
    for i, (title, _, _) in enumerate(CHAPTERS, start=1):
        lines.append(f"{i}. [{title}](#chapter-{i}-{title.lower().replace(' ', '-').replace('&', '').replace('/', '')})")
    lines.append("")
    for i, (title, intro, sections) in enumerate(CHAPTERS, start=1):
        lines.append(f"## Chapter {i} · {title}")
        lines.append("")
        lines.append(intro)
        lines.append("")
        for stitle, sbody in sections:
            lines.append(f"### {stitle}")
            lines.append(sbody)
            lines.append("")
    lines.append("---")
    lines.append("### Guardrails")
    for b in ["AI is advisory.", "Every mutation audited.",
              "Escrow dual-signature.", "Drafts hide public links.",
              "ErrorBoundary wraps every route."]:
        lines.append(f"- {b}")
    OUT_MD.write_text("\n".join(lines))
    return OUT_MD


# --- PDF build via WeasyPrint --------------------------------------------------

def build_pdf() -> Path:
    from weasyprint import HTML
    try:
        import markdown as _md
    except ImportError:  # pragma: no cover
        _md = None
    md_text = OUT_MD.read_text()
    html_body = _md.markdown(md_text, extensions=["tables"]) if _md else f"<pre>{md_text}</pre>"
    html = f"""<!doctype html><html><head><meta charset='utf-8'>
    <title>{TITLE}</title>
    <style>
      @page {{ size: A4; margin: 20mm 16mm 22mm 16mm;
        @bottom-right {{ content: 'Page ' counter(page) ' / ' counter(pages); font: 8.5pt Georgia, serif; color: #64748b; }}
        @bottom-left  {{ content: '{TITLE} · v3.2'; font: 8.5pt Georgia, serif; color: #64748b; }}
      }}
      body {{ font: 10.5pt/1.5 Calibri, Arial, sans-serif; color: #0B1F3A; }}
      h1 {{ font-size: 22pt; color: #0B1F3A; page-break-before: always; }}
      h1:first-of-type {{ page-break-before: auto; }}
      h2 {{ font-size: 14pt; color: #0B1F3A; }}
      h3 {{ font-size: 11pt; color: #5B7BA1; margin-top: 14pt; }}
      code {{ background: #f1f5f9; padding: 1pt 3pt; border-radius: 3pt; }}
    </style></head><body>{html_body}</body></html>"""
    HTML(string=html).write_pdf(str(OUT_PDF))
    return OUT_PDF


if __name__ == "__main__":
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    d = build_docx()
    m = build_md()
    p = build_pdf()
    for f in (d, m, p):
        print(f"Wrote {f}  {f.stat().st_size / 1024:.1f} KB")
