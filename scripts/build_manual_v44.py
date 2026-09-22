"""
build_manual_v44.py — PMC v2 User Manual (v44) DOCX + PDF.

Same assembly engine as v43, with:
  * "What's new in v44" chapter (Directors registration tab, Activate Now)
  * A deep-dive RFP & RFQ creation chapter that replaces the thin
    Tender Builder section (kind picker, master library, clone, sections,
    attachments, AI draft, versioning, multilingual PDF export)
  * Output: PMC_User_Manual_v44.docx / .pdf
"""
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone

sys.path.insert(0, str(Path(__file__).parent))
from manual_content import MODULES  # noqa: E402

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

SHOTS_DIR = Path("/app/deliverables/manual/screenshots")
ACTION_DIR = SHOTS_DIR / "action"
OUT_DIR = Path("/app/deliverables/manual")
OUT_DIR.mkdir(parents=True, exist_ok=True)
DOCX_PATH = OUT_DIR / "PMC_User_Manual_v44.docx"
PDF_PATH = OUT_DIR / "PMC_User_Manual_v44.pdf"

NAVY = RGBColor(0x0B, 0x1E, 0x3F)
GREY = RGBColor(0x55, 0x55, 0x55)
GREEN = RGBColor(0x04, 0x78, 0x57)


# --------------------------------------------------------------------------
# v44 — deep RFP / RFQ content (replaces the thin tender-builder module)
# --------------------------------------------------------------------------

RFP_RFQ_MODULE = {
    "surface": "admin",
    "title": "Tender Builder — RFP & RFQ Creation (deep dive)",
    "url_path": "/admin?tab=tender-builder",
    "purpose": (
        "Tender Builder is the section-by-section composer for three document "
        "kinds: TENDER (full public procurement pack), RFP (Request for "
        "Proposal — technical + commercial envelopes, evaluated on a rubric) "
        "and RFQ (Request for Quotation — price-driven, specs already fixed). "
        "You start from a seeded master template, clone it into a working "
        "draft, edit every section in a rich editor, attach per-section "
        "files, fill sections with AI, and export a trilingual PDF. Every "
        "Save snapshots the previous version (max 20 kept) so nothing is "
        "ever lost."
    ),
    "prerequisites": [
        "Admin login (admin or staff_admin role)",
        "For RFP: evaluation rubric criteria agreed internally before drafting",
        "For RFQ: final specifications frozen — RFQs invite price only",
    ],
    "actions": [
        {"id": "choose-kind", "label": "Choose TENDER vs RFP vs RFQ",
         "when": "First decision of every procurement. The kind drives the master template, the sections offered, and the downstream notice settings.",
         "steps": [
             "Open Admin → TENDER BUILDER tab.",
             "In the left sidebar, use the kind picker at the top: TENDER · RFP · RFQ.",
             "Pick TENDER for formal public works with EMD and pre-qualification (full NIB/ITB pack).",
             "Pick RFP when you are buying a solution — you want methodology, team and approach scored on a rubric, not just price.",
             "Pick RFQ when the specification is already frozen and you only need prices back (commodity goods / standard works).",
         ],
         "expected": "The master library list refreshes to show only templates of the chosen kind; the right-hand pane stays empty until you clone or open a draft.",
         "controls": [
             {"name": "Kind picker", "desc": "TENDER / RFP / RFQ toggle. Switching kind swaps the master library but does not delete your open draft."},
         ],
         "errors": [
             {"code": "Empty library", "msg": "No master templates listed for the kind",
              "fix": "Ask the Master Admin to re-seed the template library (POST /api/v1/tender-templates/seed) or pick a different kind."},
         ],
         "screenshot": "action/admin-tender-builder-idle.png"},

        {"id": "clone-master", "label": "Clone a master template into a working draft",
         "when": "Always. Never edit a master directly — clones keep organisational standards intact and start at version v1.",
         "steps": [
             "In the left sidebar master library, find the template closest to your procurement (e.g. 'RFP · Consulting Services' or 'RFQ · Goods').",
             "Click CLONE on that card.",
             "The clone opens in the right pane with all sections pre-loaded: for RFP you get Sections 1–4 plus Annexures I–VIII and Forms A–E; for RFQ a shorter commercial pack.",
             "Note: attachments from the master are deliberately NOT carried over (Bug #69) — you re-attach only what is relevant to this procurement.",
         ],
         "expected": "Toast: 'Cloned — attachments were reset'. Header form shows the cloned name with '(copy)' suffix; version badge reads v1.",
         "controls": [
             {"name": "Master library", "desc": "Seeded read-only templates. Filtered by the kind picker."},
             {"name": "My drafts", "desc": "Below the library — all your clones, newest first. Click to reopen."},
         ],
         "errors": [
             {"code": "HTTP 500 on clone", "msg": "Dangling file reference",
              "fix": "Fixed in v22+ (Bugs #69–#71). If you see this on an old environment, redeploy backend."},
         ],
         "screenshot": "admin-tender-builder-clone.png"},

        {"id": "header-meta", "label": "Fill the header meta (title, industry, reference)",
         "when": "Immediately after cloning — the header appears on every page of the exported PDF.",
         "steps": [
             "In the right pane header form, replace the name with your procurement title (e.g. 'RFP — Corporate Legal Services 2026').",
             "Set the industry/sector — this drives reporting and Vendor Intel matching.",
             "Review the auto-suggested section order; RFPs normally run NIB → ITB → Qualifying Criteria → Financial Bid Format → Annexures → Forms.",
         ],
         "expected": "Header fields persist on Save; the PDF cover uses exactly this title.",
         "controls": [
             {"name": "Name", "desc": "Working title of the draft. Shown in My drafts and on the PDF cover."},
             {"name": "Industry", "desc": "Free text / picker depending on tenant masters. Drives vendor matching."},
         ],
         "errors": [], "screenshot": "admin-tender-builder-new.png"},

        {"id": "edit-sections", "label": "Edit sections in the rich editor",
         "when": "The core authoring step — tailor each clause to this procurement.",
         "steps": [
             "Each section renders as a card: code, title, kind badge (Section / Annexure / Form), hint text from the master.",
             "Click into the body to open the rich-text editor — paste your scope, qualifying criteria or commercial format.",
             "RFP-specific: put measurable, scorable requirements in Section 3 (Qualifying Criteria) — these feed the Evaluation rubric later.",
             "RFQ-specific: keep Section 4 (Financial Bid Format) as a pure price schedule with units and quantities — bidders must not add alternatives.",
             "Reorder sections with the ↑ ↓ arrows (order is stored in steps of 10, so inserts slot between existing cards).",
             "Remove an irrelevant annexure with the ✕ on its card (confirmation required).",
             "Add a missing block with '+ Section' / '+ Annexure' / '+ Form' at the bottom — a blank card is appended with the next order number.",
         ],
         "expected": "Every keystroke is local state; the Save button enables as soon as anything changes.",
         "controls": [
             {"name": "Rich editor", "desc": "Headings, lists, tables. HTML is sanitised server-side on save."},
             {"name": "↑ ↓ reorder", "desc": "Swaps adjacent cards and re-numbers order 10, 20, 30…"},
             {"name": "✕ remove", "desc": "Deletes the section from THIS draft only — the master is untouched."},
         ],
         "errors": [
             {"code": "Pasted content loses formatting", "msg": "Tables look flat after save",
              "fix": "The server sanitises HTML (allow-list). Re-create complex tables with the editor's table button instead of pasting from Word."},
         ], "screenshot": "admin-tender-builder-idle.png"},

        {"id": "ai-draft", "label": "Fill a section with AI (AI Draft)",
         "when": "First draft of boilerplate-heavy sections (ITB, General Undertaking) or when you need a starting structure fast.",
         "steps": [
             "On any section card, click the AI DRAFT button (sparkle icon).",
             "The backend drafts text for exactly that section code using the Emergent LLM key — no API key setup needed.",
             "Review the diff preview in the modal.",
             "Click APPLY to insert, or DISCARD to keep your existing text.",
         ],
         "expected": "Toast 'Draft filled by AI · sec-2' then 'AI draft applied'. The section body is replaced only after you click Apply.",
         "controls": [
             {"name": "Apply / Discard", "desc": "AI never overwrites without an explicit Apply."},
         ],
         "errors": [
             {"code": "HTTP 502", "msg": "AI provider timeout",
              "fix": "Retry — if persistent, check Universal Key balance (Profile → Manage plan → Universal Key)."},
         ], "screenshot": None},

        {"id": "attachments", "label": "Attach files per section (single + bulk)",
         "when": "BOQ spreadsheets, drawings, site photos, forms that bidders must fill and return.",
         "steps": [
             "On a section card, click ATTACH and pick a file (PDF/DOCX/XLSX).",
             "The attachment name appears as a chip on the card — bidders download it with the tender pack.",
             "For a full pack, use BULK UPLOAD at the top: select many files at once; filenames are fuzzy-matched to section codes (e.g. 'boq_v3.xlsx' → the BOQ section) and the toast reports 'n/m files matched to sections'.",
             "Remove with the ✕ on the chip (confirmation required).",
         ],
         "expected": "Attachment chips persist after Save; the exported PDF lists them under each section.",
         "controls": [
             {"name": "Bulk upload", "desc": "One picker, many files. Unmatched files are reported in the toast — rename and retry."},
         ],
         "errors": [
             {"code": "HTTP 413", "msg": "File exceeds upload limit",
              "fix": "Split oversized BOQs or compress drawings; the per-file cap is config.MAX_UPLOAD_BYTES."},
         ], "screenshot": None},

        {"id": "save-version", "label": "Save — and use version history",
         "when": "Continuously. Every Save snapshots the previous version (max 20 retained).",
         "steps": [
             "Click SAVE (enabled only when there are unsaved edits).",
             "The version badge next to ⟲ HISTORY increments (v1 → v2 → …).",
             "Open ⟲ HISTORY to see every snapshot with timestamp and author.",
             "Click a prior version to preview; click RESTORE to roll the draft back.",
         ],
         "expected": "Toast confirms the save; history modal lists versions newest-first.",
         "controls": [
             {"name": "Save", "desc": "Creates the immutable snapshot of the PREVIOUS state, then writes your edits."},
             {"name": "History ⟲", "desc": "Restore or diff any of the last 20 versions."},
         ],
         "errors": [], "screenshot": None},

        {"id": "export-pdf", "label": "Export the trilingual PDF / public pack",
         "when": "Before linking the document to a notice — and again after any change.",
         "steps": [
             "Click EXPORT PDF to preview in-browser.",
             "Pick the language (EN / RU / KK) and click the download variant to get the file.",
             "For the public bidder pack, the same document is also available as a ZIP (document + all attachments) via the public export endpoint once linked to a notice.",
         ],
         "expected": "PDF opens with cover (your header), sections in order, annexures and forms paginated, attachment list per section.",
         "controls": [
             {"name": "Language", "desc": "EN, RU and KK strings are rendered from the i18n catalog — the section bodies stay in the language you wrote them."},
         ],
         "errors": [], "screenshot": None},

        {"id": "publish-rfp-rfq", "label": "Publish: link the document to a live notice",
         "when": "The draft is final and approved internally.",
         "steps": [
             "Go to the NOTICES tab and create the notice (title, dates, EMD, category) as usual.",
             "Reference the tender/RFP/RFQ draft in the notice so bidders get the public pack.",
             "RFP: open the EVALUATION tab and build the scoring rubric BEFORE the bid deadline — criteria must mirror Section 3.",
             "RFQ: set the EMD to zero or nominal and keep the window short — RFQs are designed for fast turnaround.",
         ],
         "expected": "The notice goes live on the public board; bidders download the pack and submit through the normal bidding pipeline.",
         "controls": [], "errors": [
             {"code": "HTTP 409", "msg": "Notice slug already exists",
              "fix": "Pick a unique reference — slugs are unique per tenant."},
         ], "screenshot": "admin-notices-publish.png"},
    ],
}

V44_NEW_MODULE = {
    "surface": "admin",
    "title": "What's new in v44 (22 Feb 2026)",
    "url_path": "/admin",
    "purpose": (
        "v44 closes the vendor-onboarding loop. The Admin Vendors panel now has "
        "a one-click ACTIVATE NOW button on every inactive vendor row, and the "
        "registration form has a new mandatory Directors & Beneficial Owners "
        "section between Sections D and E."
    ),
    "prerequisites": [],
    "actions": [
        {"id": "v44-activate-now", "label": "Vendors panel — inline 'Activate now'",
         "when": "A vendor was invited but never clicked the magic link, or was created in verify mode and needs to be activated manually.",
         "steps": [
             "Open Admin → VENDORS tab and click the INACTIVE filter chip.",
             "Every inactive row shows a green ACTIVATE NOW button.",
             "Click it: press OK in the dialog to re-send the verify email, or press Cancel to set a temporary password yourself (min 8 chars) — the vendor is then active immediately and must change the password on first login.",
             "On success the list refreshes and the row is scrolled into view with a 3.5-second emerald highlight.",
         ],
         "expected": "Green toast with the vendor ref; the row flashes emerald so it never feels 'lost'.",
         "controls": [
             {"name": "Activate now", "desc": "data-testid vendor-activate-<ref>. Two modes: resend-link (OK) or set-password (Cancel)."},
         ],
         "errors": [
             {"code": "HTTP 400", "msg": "Vendor is already active",
              "fix": "Nothing to do — the row will show as active after refresh."},
         ], "screenshot": None},
        {"id": "v44-directors", "label": "Registration — Directors & Beneficial Owners tab",
         "when": "Every vendor registration, both self-service and admin-assisted.",
         "steps": [
             "The stepper now has 6 steps: A · B · C · D · DIRECTORS · E.",
             "Open DIRECTORS · BENEFICIAL OWNERS and click '+ ADD ANOTHER PERSON' for each director, ≥10% shareholder and UBO.",
             "Per person fill: full legal name, role (Director / Shareholder / UBO / Officer / Other), nationality, ID/passport number, ownership %, residential address.",
             "At least one row with a full name is mandatory — SUBMIT stays disabled with a red hint until it is provided.",
         ],
         "expected": "Draft auto-saves the directors list; final submit is gated on it.",
         "controls": [], "errors": [], "screenshot": None},
    ],
}


def _heading(doc, text, level=1, color=NAVY):
    h = doc.add_heading("", level=level)
    r = h.add_run(text)
    r.font.color.rgb = color


def _kv(doc, label, value):
    p = doc.add_paragraph()
    r = p.add_run(f"{label}: ")
    r.bold = True
    r.font.color.rgb = NAVY
    p.add_run(value or "")


def _panel_shot(doc, code):
    shot = SHOTS_DIR / f"{code}-panel.png"
    if shot.exists():
        doc.add_picture(str(shot), width=Inches(6.0))


def _action_shot(doc, filename):
    if not filename:
        return
    shot = SHOTS_DIR / filename
    if not shot.exists():
        shot = ACTION_DIR / filename.split("/")[-1]
    if shot.exists():
        doc.add_picture(str(shot), width=Inches(5.8))


def _action_shots_for(code):
    prefix = f"{code}-"
    if not ACTION_DIR.exists():
        return []
    return sorted([p for p in ACTION_DIR.iterdir() if p.name.startswith(prefix)])


def _render_module(doc, code, m):
    _heading(doc, m["title"], level=1)
    _kv(doc, "Surface", m["surface"])
    _kv(doc, "URL path", m["url_path"])
    _kv(doc, "Purpose", m["purpose"])
    if m.get("prerequisites"):
        doc.add_paragraph().add_run("Prerequisites").bold = True
        for pr in m["prerequisites"]:
            doc.add_paragraph(pr, style="List Bullet")
    _panel_shot(doc, code)

    extras = _action_shots_for(code)
    if extras:
        doc.add_paragraph().add_run("Per-modal screenshots").bold = True
        for shot in extras:
            doc.add_picture(str(shot), width=Inches(5.8))
            cap = doc.add_paragraph()
            r = cap.add_run(shot.stem)
            r.italic = True; r.font.size = Pt(9); r.font.color.rgb = GREY

    for i, a in enumerate(m.get("actions") or [], start=1):
        _heading(doc, f"{i}. {a['label']}", level=2)
        _kv(doc, "When to use", a.get("when", ""))
        if a.get("steps"):
            doc.add_paragraph().add_run("Steps").bold = True
            for step in a["steps"]:
                doc.add_paragraph(step, style="List Number")
        _kv(doc, "Expected result", a.get("expected", ""))
        if a.get("controls"):
            doc.add_paragraph().add_run("Controls & fields").bold = True
            for c in a["controls"]:
                p = doc.add_paragraph(style="List Bullet")
                p.add_run(c["name"] + ": ").bold = True
                p.add_run(c["desc"])
        if a.get("errors"):
            doc.add_paragraph().add_run("Common errors & fixes").bold = True
            for e in a["errors"]:
                p = doc.add_paragraph(style="List Bullet")
                p.add_run(f"{e['code']} — {e['msg']}").bold = True
                doc.add_paragraph(f"Fix: {e['fix']}").paragraph_format.left_indent = Inches(0.5)
        _action_shot(doc, a.get("screenshot"))
    doc.add_page_break()


def build():
    doc = Document()

    cover = doc.add_paragraph()
    cover.alignment = WD_ALIGN_PARAGRAPH.CENTER
    r = cover.add_run("PMC Managers v2\n")
    r.font.size = Pt(28); r.font.color.rgb = NAVY; r.bold = True
    r = cover.add_run("User Manual\n")
    r.font.size = Pt(22); r.font.color.rgb = NAVY
    r = cover.add_run(f"\nVersion 44 · {datetime.now(timezone.utc).strftime('%d %B %Y')}\n")
    r.font.size = Pt(12); r.font.color.rgb = GREY
    r = cover.add_run(
        "End-to-end guide — every module, every action, every screen.\n"
        "Special focus chapter: RFP & RFQ creation in Tender Builder.\n"
        "Includes v44: Directors & Beneficial Owners registration + one-click vendor activation.\n"
    )
    r.font.size = Pt(11); r.italic = True; r.font.color.rgb = GREY
    doc.add_page_break()

    # ---- v44 module first (highlight), then deep RFP/RFQ, then everything else
    ordered = {"v44-release": V44_NEW_MODULE,
               "admin-tender-builder": RFP_RFQ_MODULE}
    for code, m in MODULES.items():
        if code in ordered:
            continue
        ordered[code] = m

    _heading(doc, "Contents", level=1)
    for code, m in ordered.items():
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(f"{m['title']}  ").bold = True
        p.add_run(f"— {len(m.get('actions') or [])} action(s)").italic = True
    doc.add_page_break()

    for code, m in ordered.items():
        _render_module(doc, code, m)

    _heading(doc, "Appendix A — Live URLs", level=1)
    for label, url in [
        ("Public notice board", "https://www.pmcmanagers.com/"),
        ("Registration portal", "https://www.pmcmanagers.com/register"),
        ("Admin console", "https://www.pmcmanagers.com/admin"),
        ("Vendor portal", "https://www.pmcmanagers.com/vendor"),
        ("Staff portal", "https://www.pmcmanagers.com/staff"),
    ]:
        p = doc.add_paragraph(style="List Bullet")
        p.add_run(f"{label}: ").bold = True
        p.add_run(url)

    doc.save(str(DOCX_PATH))
    print(f"DOCX → {DOCX_PATH} ({DOCX_PATH.stat().st_size // 1024} KB)")

    r = subprocess.run(
        ["libreoffice", "--headless", "--convert-to", "pdf",
         "--outdir", str(OUT_DIR), str(DOCX_PATH)],
        capture_output=True, text=True, timeout=300,
    )
    if r.returncode != 0:
        print("PDF conversion stderr:", r.stderr[:500])
    if PDF_PATH.exists():
        print(f"PDF  → {PDF_PATH} ({PDF_PATH.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    build()
