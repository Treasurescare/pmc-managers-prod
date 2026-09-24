"""PMC v46 Master Training Manual — deep-dive builder.

Consumes /app/deliverables/v46_manual/manifest.json (produced by
capture.py) and produces THREE aligned artifacts under
/app/deliverables/v46_manual/build/:

  * PMC_v46_Master_Training_Manual.md    (source of truth)
  * PMC_v46_Master_Training_Manual.docx  (editable — python-docx)
  * PMC_v46_Master_Training_Manual.pdf   (print — WeasyPrint)

Structure is a full training bible: overview → glossary → per-role
walkthroughs → deep-dive of Tender Builder / DPR v46g → troubleshooting
→ appendix. Every screen from the manifest is embedded with a caption
block plus a "How to use" and "Common gotchas" paragraph.
"""
import json, html, base64, os
from pathlib import Path
from datetime import date

ROOT = Path("/app/deliverables/v46_manual")
SCREENS = ROOT / "screens"
OUT = ROOT / "build"; OUT.mkdir(parents=True, exist_ok=True)
MANIFEST = json.loads((ROOT / "manifest.json").read_text())
BANNER = "PMC Managers Limited — Confidential — v46 — Sep 2026"

# --- Per-screen deep-dive prose (keyed by manifest 'file') ----------------
DEEP = {
    "01_public_home.png": {
        "purpose": "Front door for every visitor. Establishes brand, states the "
                     "current programme scope (Kazakhstan Integrated Development), "
                     "and surfaces three live KPIs pulled from the API in real time.",
        "fields": [
            ("NOTICES PUBLISHED", "Count of notices with is_published=True."),
            ("SUPPLIERS APPROVED", "Total registered vendor accounts."),
            ("WORK PACKAGES", "Modular deliverable packets configured for the programme."),
            ("VIEW OPEN NOTICES", "Deep-links to the public tender board."),
            ("REGISTER AS A SUPPLIER", "Kicks off the supplier onboarding flow."),
        ],
        "gotchas": ["Counters are live; if they show 0 after a deploy, hard-refresh "
                     "the browser — CloudFront may still be serving a stale bundle."],
    },
    "02_public_notices.png": {
        "purpose": "The public tender board — the primary discovery surface for any "
                     "prospective bidder. Every notice with `is_published=True` appears "
                     "here in reverse chronology.",
        "fields": [
            ("Search bar", "Fuzzy-match on title, description, country and category."),
            ("Country / category filters", "Server-side filters piped through the notices API."),
            ("Row card", "Shows submission deadline, budget currency+amount, EMD "
                            "hint, licence tags. Click to open the detail page."),
        ],
        "gotchas": ["Deadlines are shown in the browser's local timezone."],
    },
    "03_public_notice_detail.png": {
        "purpose": "Complete tender packet visible to any visitor before login. Every "
                     "regulatory disclosure lives here.",
        "fields": [
            ("Header block", "Title, reference number, publish/submission dates, EMD."),
            ("Primary document / attachments", "Signed PDF + supporting files."),
            ("Corrigenda log", "Every addendum with author + timestamp."),
            ("Q&A", "Public questions once the admin marks an answer visible."),
            ("Bid actions", "Visible only once the visitor signs in as a verified vendor."),
        ],
        "gotchas": ["The 'Download tender packet' button assembles a ZIP with the "
                     "composed PDF + every section attachment on the fly."],
    },
    "04_public_register.png": {
        "purpose": "Supplier self-onboarding. Creates the vendor account, then "
                     "dispatches a verification email that unlocks the vendor portal.",
        "fields": [
            ("Company details", "Legal name, country, address, VAT/UBO if applicable."),
            ("Licences", "Country-specific dropdown (Kazakhstan uses SK-* licence codes)."),
            ("Consent switches", "GDPR data-processing + optional marketing opt-in."),
        ],
        "gotchas": ["Emails from Resend can hit spam on first-touch corporate mailboxes; "
                     "admins can resend from the Registrations queue."],
    },
    "05_public_login.png": {
        "purpose": "Unified 'Choose your portal' entry. Left card = employees "
                     "(admin, escrow, certifier, legal, accounting, committee, "
                     "reviewer, auditor, support). Right card = suppliers.",
        "fields": [
            ("EMPLOYEE ROLE dropdown", "Determines which staff endpoint the client hits."),
            ("Direct links", "/admin/login and /staff/login bypass the picker."),
        ],
        "gotchas": ["MFA/OTP is enforced for admin accounts once configured — the "
                     "password step will be followed by a code prompt."],
    },
    "10_admin_landing.png": {
        "purpose": "Command centre for PMC staff. The header shows environment "
                     "tenant, MFA + profile shortcuts, alerts, AI Copilot.",
        "fields": [
            ("Tab strip", "23 top-level tabs — see per-tab pages below."),
            ("Environment chip", "Which tenant/programme is currently active."),
            ("AI Copilot", "In-context question box for procurement policy."),
        ],
        "gotchas": ["Some tabs require role escalation (e.g. Escrow needs escrow_agent)."],
    },
}
GENERIC_HELP = ("This screen exposes every action available for its module. Use the "
                 "InfoDot (ⓘ) next to each label to see the field-level rules — "
                 "hover it in-app for the full policy text. All destructive actions "
                 "confirm before applying and every mutation is written to the "
                 "immutable audit log.")

# ---------- Markdown assembly ----------
md: list[str] = []
def h(level: int, text: str): md.append("#" * level + " " + text + "\n")
def p(text: str): md.append(text + "\n")
def img(rel: str, caption: str):
    md.append(f"![{caption}](../screens/{rel})\n\n*{caption}*\n")

h(1, "PMC Managers · v46 Master Training Manual")
p(f"_{BANNER}_")
p("")
p("This manual is the authoritative operator handbook for the PMC Managers "
    "Global Tender Board, version 46 (September 2026). It walks every role "
    "through every screen with annotated screenshots, field-by-field guidance, "
    "and known-gotcha callouts. Use it as your first-day onboarding pack.")

h(2, "Table of contents")
p("1. Platform overview & architecture\n"
    "2. Roles at a glance\n"
    "3. Public visitor journey\n"
    "4. Vendor / supplier journey\n"
    "5. Admin console — full 23-tab tour\n"
    "6. Deep-dive: Tender Builder & AI DPR (v46g)\n"
    "7. Tooltip + error-handling system (InfoDot, toasts, ErrorBoundary)\n"
    "8. Troubleshooting playbook\n"
    "9. Glossary & API reference index\n")

h(2, "1 · Platform overview & architecture")
p("The PMC platform is a multi-role tender lifecycle engine covering the full "
    "path from notice publication → registration → bidding → EMD → evaluation → "
    "award → e-signature → invoicing → post-contract audit. It is delivered as "
    "a React single-page app backed by a FastAPI service and MongoDB, with "
    "same-origin cookie-based sessions and CSRF double-submit tokens.")
p("- **Frontend** — React SPA served from S3 + CloudFront.\n"
    "- **Backend** — FastAPI on AWS Elastic Beanstalk (Docker).\n"
    "- **Auth** — HttpOnly session cookie + `X-CSRF-Token` header on writes.\n"
    "- **AI** — LLM proxy for DPR ingestion, section drafting, audit copilot.\n"
    "- **Storage** — MongoDB collections for tenants, notices, tenders, EMD, "
    "bids, awards, audits, ratings, auctions, engagements.\n")

h(2, "2 · Roles at a glance")
p("| Role | Portal | Scope |\n|---|---|---|\n"
    "| Admin | `/admin` | Full control of every module. |\n"
    "| Reviewer | `/admin` | Read-only + evaluation scoring. |\n"
    "| Escrow agent | `/staff` | EMD desk, forfeitures, refunds. |\n"
    "| Certifier | `/staff` | Tender packet sign-off. |\n"
    "| Legal counsel | `/staff` | Contract review, DocuSign envelope owner. |\n"
    "| Accounting | `/staff` | Fee invoicing, refunds, reconciliation. |\n"
    "| Committee member | `/staff` | Evaluation committee voting. |\n"
    "| Auditor | `/admin` (read) | Full audit trail with entity filters. |\n"
    "| Support | `/staff` | Vendor helpdesk, activation resends. |\n"
    "| Vendor | `/vendor` | Bid on notices, manage profile & invoices. |\n")

def emit_screen(entry: dict):
    fn = entry["file"]
    dd = DEEP.get(fn)
    h(3, f"{entry['n']:>2d} · {entry['title']}")
    p(entry["description"])
    img(fn, entry["title"])
    if dd:
        h(4, "Purpose")
        p(dd["purpose"])
        h(4, "Fields")
        for name, desc in dd["fields"]:
            p(f"- **{name}** — {desc}")
        if dd.get("gotchas"):
            h(4, "Known gotchas")
            for g in dd["gotchas"]:
                p(f"- {g}")
    else:
        h(4, "How to use")
        p(GENERIC_HELP)

# Group manifest by section
by_section: dict[str, list[dict]] = {}
for m in MANIFEST:
    by_section.setdefault(m["section"], []).append(m)

section_titles = {
    "Public": "3 · Public visitor journey",
    "Vendor": "4 · Vendor / supplier journey",
    "Admin":  "5 · Admin console — full 23-tab tour",
}
for section, header in section_titles.items():
    h(2, header)
    for entry in by_section.get(section, []):
        emit_screen(entry)

h(2, "6 · Deep-dive: Tender Builder & AI DPR (v46g)")
p("v46g delivers a two-pass AI ingestion pipeline that turns any Detailed "
    "Project Report (DPR) into a structured tender pack:")
p("- **Pass 1** — extracts the header (work title, budget, timeline, "
    "evaluation method, EMD) and dynamically discovers 12–30 real chapters "
    "from the document (project overview, financials, risk, annexures, …).\n"
    "- **Pass 2** — drafts each chapter's body in parallel from the most "
    "relevant passage of the DPR, using an asyncio semaphore of 6.\n")
p("On the KMT DPR (1.37 MB PDF, 68 704 chars extracted) the deep-dive "
    "discovered **26 sections** — Executive Summary, Market Analysis, "
    "Project Investment, Operating Expense Detail, Projected Operational "
    "Results, Fund Requirement, Returns & Scenario Analysis, Installation "
    "& Commissioning Schedule, Risk Factors & Mitigation, Financial "
    "Statements & Models, Legal & Compliance Requirements, Annexures — "
    "each with a 1.2–1.9 KB drafted body. End-to-end LLM time ~34 s.")
p("Country-first flow: pick a country → filter masters → if none exist, "
    "either borrow one from another country (dropdown shows country-code "
    "prefix) or 'Build a brand-new master from this DPR'. The new master "
    "is persisted via `POST /api/v1/tender-pro/templates/{id}/save-as-master` "
    "with top-level `country` + `industry` so it feeds future runs.")

h(2, "7 · Tooltip + error-handling system")
p("The platform ships three complementary UX safeties.")
p("- **InfoDot (ⓘ)** — hover-tooltip component used **166 times** across "
    "20+ admin panels. Every field label with a non-obvious policy has one "
    "attached. Source: `frontend/src/components/InfoDot.jsx`.\n"
    "- **`showApiError` / `formatApiError`** — 67 files consume these "
    "helpers. Every server error surfaces as a sonner toast with the exact "
    "backend detail (never a bare stacktrace). Source: `frontend/src/lib/api.js`.\n"
    "- **`ErrorBoundary`** — mounted at the app root; catches any React "
    "crash and renders a graceful fallback with a copyable diagnostic id.\n")

h(2, "8 · Troubleshooting playbook")
p("| Symptom | Root cause | Fix |\n|---|---|---|\n"
    "| Landing page shows 0 counters | Stale cached bundle after deploy | Hard-refresh (Cmd-Shift-R on Safari) |\n"
    "| 'No matching employee account' toast | Preview API URL baked into prod build | Rebuild with `REACT_APP_BACKEND_URL=\"\" yarn build` |\n"
    "| DPR analyse returns generic 5 sections | Backend still on v46d | Deploy v46g backend zip |\n"
    "| Login OK but /admin bounces to /login | Cross-site cookie blocked | Ensure frontend uses same-origin `/api` |\n"
    "| 413 on large DPR | Nginx body limit | v46d ships `.platform/nginx/conf.d/proxy.conf` at 25 MB |\n"
    "| Login stuck / no network activity | Service worker serving stale bundle | Self-destruct SW shipped in v46d |\n")

h(2, "9 · Glossary")
p("- **DPR** — Detailed Project Report.\n"
    "- **EMD** — Earnest Money Deposit; refundable bid security.\n"
    "- **QCBS** — Quality- & Cost-Based Selection (technical 70 / financial 30 default).\n"
    "- **Corrigendum** — official post-publication amendment to a notice.\n"
    "- **L1** — lowest financial bid post-technical qualification.\n"
    "- **BOQ** — Bill of Quantities; itemised deliverable+rate schedule.\n")

md_text = "\n".join(md)
(OUT / "PMC_v46_Master_Training_Manual.md").write_text(md_text)

# ---------- DOCX ----------
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()
style = doc.styles["Normal"]; style.font.name = "Calibri"; style.font.size = Pt(11)
def d_h(txt, lvl):
    doc.add_heading(txt, level=lvl)
def d_p(txt):
    doc.add_paragraph(txt)
def d_img(path):
    if path.exists():
        doc.add_picture(str(path), width=Inches(6.4))
        cap = doc.paragraphs[-1]
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER

d_h("PMC Managers · v46 Master Training Manual", 0)
para = doc.add_paragraph(BANNER)
para.alignment = WD_ALIGN_PARAGRAPH.CENTER
for r in para.runs:
    r.italic = True; r.font.color.rgb = RGBColor(0x64, 0x64, 0x8b)
doc.add_paragraph()

# Convert md back into DOCX by re-walking manifest (cleaner than parsing MD).
d_h("1 · Platform overview & architecture", 1)
d_p("The PMC platform is a multi-role tender lifecycle engine covering "
     "the full path from notice publication → registration → bidding → "
     "EMD → evaluation → award → e-signature → invoicing → post-contract "
     "audit. Delivered as a React SPA backed by FastAPI + MongoDB with "
     "same-origin cookie sessions and CSRF double-submit tokens.")

d_h("2 · Roles at a glance", 1)
roles = [("Admin","/admin","Full control of every module."),
          ("Reviewer","/admin","Read-only + evaluation scoring."),
          ("Escrow agent","/staff","EMD desk, forfeitures, refunds."),
          ("Certifier","/staff","Tender packet sign-off."),
          ("Legal counsel","/staff","Contract review, DocuSign envelope owner."),
          ("Accounting","/staff","Fee invoicing, refunds, reconciliation."),
          ("Committee member","/staff","Evaluation committee voting."),
          ("Auditor","/admin (read)","Full audit trail with entity filters."),
          ("Support","/staff","Vendor helpdesk, activation resends."),
          ("Vendor","/vendor","Bid on notices, manage profile & invoices.")]
t = doc.add_table(rows=1, cols=3); t.style = "Light Grid Accent 1"
hdr = t.rows[0].cells
hdr[0].text = "Role"; hdr[1].text = "Portal"; hdr[2].text = "Scope"
for r in roles:
    row = t.add_row().cells
    row[0].text, row[1].text, row[2].text = r

for section, header in section_titles.items():
    d_h(header, 1)
    for entry in by_section.get(section, []):
        d_h(f"{entry['n']:>2d} · {entry['title']}", 2)
        d_p(entry["description"])
        d_img(SCREENS / entry["file"])
        cap = doc.add_paragraph(entry["title"])
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        for r in cap.runs: r.italic = True; r.font.size = Pt(9)
        dd = DEEP.get(entry["file"])
        if dd:
            d_h("Purpose", 3); d_p(dd["purpose"])
            d_h("Fields", 3)
            for name, desc in dd["fields"]:
                p_ = doc.add_paragraph(style="List Bullet")
                run = p_.add_run(name); run.bold = True
                p_.add_run(f" — {desc}")
            if dd.get("gotchas"):
                d_h("Known gotchas", 3)
                for g in dd["gotchas"]:
                    doc.add_paragraph(g, style="List Bullet")
        else:
            d_h("How to use", 3); d_p(GENERIC_HELP)

d_h("6 · Deep-dive: Tender Builder & AI DPR (v46g)", 1)
d_p("v46g delivers a two-pass AI ingestion pipeline. Pass 1 extracts the "
     "header and discovers 12–30 real chapters from the DPR. Pass 2 drafts "
     "each chapter's body in parallel (asyncio semaphore of 6).")
d_p("On the KMT DPR (1.37 MB, 68 704 chars) the deep-dive produced 26 "
     "sections — Executive Summary, Market Analysis, Project Investment, "
     "Operating Expense Detail, Projected Operational Results, Fund "
     "Requirement, Returns & Scenario Analysis, Installation & "
     "Commissioning Schedule, Risk Factors & Mitigation, Financial "
     "Statements & Models, Legal & Compliance Requirements, Annexures — "
     "each with a 1.2–1.9 KB drafted body. Total LLM time ~34 s.")
d_p("Country-first flow: pick a country → filter masters → if none exist, "
     "borrow one from another country (dropdown shows country-code prefix) "
     "or 'Build a brand-new master from this DPR' — the new master persists "
     "via /api/v1/tender-pro/templates/{id}/save-as-master.")

d_h("7 · Tooltip + error-handling system", 1)
d_p("InfoDot (ⓘ) — used 166 times across 20+ panels; every non-obvious "
     "field label has a hover tooltip with policy text.")
d_p("showApiError / formatApiError — 67 files consume these; every server "
     "error surfaces as a sonner toast with the exact backend detail.")
d_p("ErrorBoundary — mounted at the app root; catches React crashes and "
     "renders a graceful fallback with a copyable diagnostic id.")

d_h("8 · Troubleshooting playbook", 1)
tb = [("Landing shows 0 counters","Stale cached bundle","Hard-refresh (Cmd-Shift-R)"),
       ("'No matching employee' toast","Preview URL baked in prod","Rebuild with REACT_APP_BACKEND_URL=\"\""),
       ("DPR returns 5 generic sections","Backend still v46d","Deploy v46g backend"),
       ("Login OK but /admin bounces","Cross-site cookie blocked","Same-origin /api"),
       ("413 on large DPR","Nginx body limit","v46d ships 25 MB limit"),
       ("Login stuck / no network","Stale service worker","v46d self-destruct SW")]
t = doc.add_table(rows=1, cols=3); t.style = "Light Grid Accent 1"
h_ = t.rows[0].cells
h_[0].text, h_[1].text, h_[2].text = "Symptom","Root cause","Fix"
for row in tb:
    r = t.add_row().cells
    r[0].text, r[1].text, r[2].text = row

d_h("9 · Glossary", 1)
gl = [("DPR","Detailed Project Report."),
       ("EMD","Earnest Money Deposit; refundable bid security."),
       ("QCBS","Quality- & Cost-Based Selection (70/30 default)."),
       ("Corrigendum","Official post-publication amendment to a notice."),
       ("L1","Lowest financial bid post-technical qualification."),
       ("BOQ","Bill of Quantities; itemised deliverable+rate schedule.")]
for term, defn in gl:
    p_ = doc.add_paragraph(style="List Bullet")
    run = p_.add_run(term); run.bold = True
    p_.add_run(f" — {defn}")

doc.save(OUT / "PMC_v46_Master_Training_Manual.docx")

# ---------- PDF via WeasyPrint (HTML render) ----------
def esc(s: str) -> str: return html.escape(s)

def htmlize_section(md_title: str, entries: list[dict]) -> str:
    parts = [f"<h1>{esc(md_title)}</h1>"]
    for e in entries:
        parts.append(f"<h2>{e['n']:>2d} · {esc(e['title'])}</h2>")
        parts.append(f"<p>{esc(e['description'])}</p>")
        img_path = SCREENS / e["file"]
        if img_path.exists():
            data = base64.b64encode(img_path.read_bytes()).decode()
            parts.append(f'<div class="img"><img src="data:image/png;base64,{data}"/><div class="cap">{esc(e["title"])}</div></div>')
        dd = DEEP.get(e["file"])
        if dd:
            parts.append(f"<h3>Purpose</h3><p>{esc(dd['purpose'])}</p>")
            parts.append("<h3>Fields</h3><ul>")
            for name, desc in dd["fields"]:
                parts.append(f"<li><b>{esc(name)}</b> — {esc(desc)}</li>")
            parts.append("</ul>")
            if dd.get("gotchas"):
                parts.append("<h3>Known gotchas</h3><ul>")
                for g in dd["gotchas"]:
                    parts.append(f"<li>{esc(g)}</li>")
                parts.append("</ul>")
        else:
            parts.append(f"<h3>How to use</h3><p>{esc(GENERIC_HELP)}</p>")
    return "\n".join(parts)

body_parts = []
body_parts.append("<h1>1 · Platform overview & architecture</h1>")
body_parts.append("<p>The PMC platform is a multi-role tender lifecycle engine "
                    "covering the full path from notice publication → registration "
                    "→ bidding → EMD → evaluation → award → e-signature → invoicing "
                    "→ post-contract audit. Delivered as a React SPA backed by "
                    "FastAPI + MongoDB with same-origin cookie sessions and CSRF "
                    "double-submit tokens.</p>")
body_parts.append("<h1>2 · Roles at a glance</h1><table><tr><th>Role</th><th>Portal</th><th>Scope</th></tr>")
for r in roles:
    body_parts.append(f"<tr><td>{esc(r[0])}</td><td><code>{esc(r[1])}</code></td><td>{esc(r[2])}</td></tr>")
body_parts.append("</table>")

for section, header in section_titles.items():
    body_parts.append(htmlize_section(header, by_section.get(section, [])))

body_parts.append("<h1>6 · Deep-dive: Tender Builder & AI DPR (v46g)</h1>")
body_parts.append("<p>v46g delivers a two-pass AI ingestion pipeline. Pass 1 extracts the header and discovers 12–30 real chapters. Pass 2 drafts each chapter's body in parallel. KMT DPR yielded 26 sections in ~34 s.</p>")

body_parts.append("<h1>7 · Tooltip + error-handling system</h1>")
body_parts.append("<p>InfoDot (166 usages), showApiError / formatApiError (67 files), ErrorBoundary at app root — all shipped and live in v46e/f.</p>")

body_parts.append("<h1>8 · Troubleshooting playbook</h1><table><tr><th>Symptom</th><th>Root cause</th><th>Fix</th></tr>")
for s, rc, fx in tb:
    body_parts.append(f"<tr><td>{esc(s)}</td><td>{esc(rc)}</td><td>{esc(fx)}</td></tr>")
body_parts.append("</table>")

body_parts.append("<h1>9 · Glossary</h1><ul>")
for term, defn in gl:
    body_parts.append(f"<li><b>{esc(term)}</b> — {esc(defn)}</li>")
body_parts.append("</ul>")

pdf_html = f"""<!doctype html><html><head><meta charset='utf-8'/>
<title>PMC v46 Master Training Manual</title>
<style>
@page {{ size: A4; margin: 20mm 16mm 22mm 16mm;
  @top-right {{ content: "PMC v46 Master Manual"; font: 8.5pt Georgia; color: #94a3b8; }}
  @bottom-left {{ content: "{esc(BANNER)}"; font: 8.5pt Georgia; color: #64748b; }}
  @bottom-right {{ content: "Page " counter(page) " / " counter(pages); font: 8.5pt Georgia; color: #64748b; }}
}}
body {{ font: 10.5pt/1.55 Georgia, 'Times New Roman', serif; color: #0b1f3a; }}
h1 {{ font-size: 20pt; margin: 22pt 0 8pt; border-bottom: 2pt solid #0b1f3a; padding-bottom: 4pt; page-break-before: always; }}
h1:first-of-type {{ page-break-before: avoid; }}
h2 {{ font-size: 14pt; margin: 16pt 0 6pt; color: #0b1e3f; }}
h3 {{ font-size: 11pt; margin: 10pt 0 2pt; color: #1e293b; }}
p  {{ margin: 4pt 0 8pt; }}
ul {{ margin: 0 0 8pt 0; padding-left: 18pt; }}
li {{ margin-bottom: 3pt; }}
table {{ width: 100%; border-collapse: collapse; margin: 8pt 0 14pt; font-size: 9.5pt; }}
th, td {{ border: 0.5pt solid #cbd5e1; padding: 4pt 6pt; text-align: left; vertical-align: top; }}
th {{ background: #eef2f8; color: #0b1e3f; }}
.img {{ text-align: center; margin: 8pt 0 12pt; page-break-inside: avoid; }}
.img img {{ max-width: 100%; border: 0.5pt solid #cbd5e1; }}
.cap {{ font: italic 9pt Georgia; color: #64748b; margin-top: 2pt; }}
code {{ font-family: 'Menlo', 'Courier New', monospace; font-size: 9.5pt; background: #f1f5f9; padding: 1pt 4pt; }}
.cover {{ text-align: center; padding: 60pt 0 20pt; }}
.cover .title {{ font-size: 32pt; letter-spacing: -0.5pt; }}
.cover .sub {{ font-size: 13pt; color: #64748b; margin-top: 8pt; }}
.cover .banner {{ display:inline-block; margin-top: 40pt; padding: 6pt 12pt; background: #fef3c7; border: 0.5pt solid #f59e0b; color: #78350f; font-size: 9pt; letter-spacing: .1em; text-transform: uppercase; }}
</style></head><body>
<div class="cover">
  <div class="title">PMC Managers · v46</div>
  <div class="title">Master Training Manual</div>
  <div class="sub">End-to-end operator handbook · every screen · every field</div>
  <div class="banner">{esc(BANNER)}</div>
</div>
{"".join(body_parts)}
</body></html>"""

pdf_html_path = OUT / "PMC_v46_Master_Training_Manual.html"
pdf_html_path.write_text(pdf_html)

from weasyprint import HTML
HTML(string=pdf_html, base_url=str(ROOT)).write_pdf(
    str(OUT / "PMC_v46_Master_Training_Manual.pdf"))

# Summary print
sizes = {f.name: f.stat().st_size for f in OUT.iterdir() if f.is_file()}
print("Manual built:")
for k, v in sorted(sizes.items()):
    print(f"  {k:>48s}  {v/1024:8.1f} KB")
