"""PMC v46p — comprehensive Testing Manual generator.

Produces a self-contained PDF (+ HTML) with:
  * one test-plan section per module (public notice board, registration,
    admin console tabs, vendor portal, staff portal, committee, escrow,
    reverse auctions, DPR, evaluation, awards, contracts, DocuSign,
    reports/snapshot, PWA)
  * per module: happy-path, edge cases, negative cases, expected UI,
    expected errors + HTTP codes, test data + credentials
"""
from pathlib import Path
from weasyprint import HTML
import html as _html

OUT = Path("/app/deliverables/v46_manual/build")
OUT.mkdir(parents=True, exist_ok=True)

BANNER = "PMC Managers · Confidential — Internal Use Only"

def esc(s): return _html.escape(str(s))


# One tuple per test-case: (id, title, precondition, steps, expected_ui, expected_api, data)
def tc(idx, title, pre, steps, ui, api, data=""):
    return {
        "id": idx, "title": title, "pre": pre, "steps": steps,
        "ui": ui, "api": api, "data": data,
    }


MODULES = [
    # -------------------------------------------------------------------
    ("A · Public Notice Board", "No auth required — anyone on the internet can browse open tenders.", [
        tc("A-01", "Landing page renders with 3 KPI cards",
           "None. Open incognito.",
           ["Navigate to /", "Wait for hero + stats cards to load"],
           ["Hero shows 'Global Tender Board' headline, gold kicker, gold CTA.",
            "Three StatCards render: notices published, suppliers approved, packages total.",
            "5-portal login CTA visible in header + hero as 'Portal gateways'."],
           ["GET /api/v1/meta/public/stats → 200 JSON",
            "GET /api/v1/notices?limit=... → 200 items[]"],
           "Preview URL from frontend .env REACT_APP_BACKEND_URL"),
        tc("A-02", "Filter notices by document type",
           "Landing loaded.",
           ["Click 'Tender' filter chip", "Click 'RFP' filter chip", "Click 'All' to reset"],
           ["Notice list re-renders instantly, only rows with matching document_type shown.",
            "Selected chip becomes solid navy; others revert to white/navy border."],
           ["GET /api/v1/notices?document_type=tender → 200"],
           "Any published notice"),
        tc("A-03", "Filter by country",
           "Landing loaded, ≥ 1 notice.",
           ["Open country dropdown", "Pick 'KZ' (Kazakhstan)"],
           ["List filters to KZ notices only. Dropdown label updates."],
           ["GET /api/v1/notices?country=KZ → 200"],
           ""),
        tc("A-04", "Notice detail page opens",
           "≥ 1 published notice.",
           ["Click any notice row card"],
           ["Route to /notices/{notice_ref}",
            "Detail renders: title, category, budget, deadline countdown, description, attachments panel.",
            "'Days left' badge red when ≤ 14, otherwise navy."],
           ["GET /api/v1/notices/{ref} → 200"],
           "PMC-NOT-2026-0001 or equivalent"),
        tc("A-05", "Q&A section on detail page",
           "Notice detail open, admin has published a Q&A.",
           ["Scroll to Q&A section", "Expand any published question"],
           ["Q&A rows show question text + admin answer + published_at ISO date."],
           ["GET /api/v1/notices/{ref}/qa → 200 items[]"],
           ""),
        tc("A-06", "About Us / Vision pages",
           "Public site.",
           ["Click 'About us' in top nav", "Click 'Vision' in top nav"],
           ["Both pages render with sovereign navy hero + editorial content in EN/RU/KK per locale."],
           ["No auth calls."],
           ""),
    ], "public"),

    # -------------------------------------------------------------------
    ("B · Vendor Registration", "Multi-step wizard with magic-link resume. Bug-blitz gate (v46p) enforces Section A completion before advancing.", [
        tc("B-01", "Start registration",
           "None.",
           ["Go to /register", "Enter email 'qatest+{{uuid}}@example.com'",
            "Optional: company name", "Pick country KZ", "Submit"],
           ["Toast success 'Draft created'",
            "Auto-redirect to /register/resume?token=<mMQ4...>"],
           ["POST /api/v1/registrations → 200 {id, magic_token}"],
           "Random email each run to avoid duplicate."),
        tc("B-02", "Section A gate — cannot jump to step B while incomplete",
           "Draft created (B-01).",
           ["On /register/resume, click stepper button 'B'",
            "Observe toast + no navigation"],
           ["Step B/C/D/directors/E buttons show aria-disabled + opacity-40 cursor-not-allowed.",
            "Clicking any raises sonner toast 'Please fill Identity & Basic Info first. Missing: <fields>'.",
            "Section-a-gaps counter renders red under Next."],
           ["No API call made."],
           "Bug-blitz (a) verification — v46p."),
        tc("B-03", "Complete Section A → gate opens",
           "Draft created.",
           ["Fill company_name, registered_address, country, registration_number, legal_entity_type",
            "Click Save draft", "Click stepper 'B'"],
           ["Stepper buttons become clickable; navigation advances to Section B."],
           ["PATCH /api/v1/registrations/{id}?token=<t> → 200"],
           ""),
        tc("B-04", "Submit final requires directors + all declarations",
           "Sections A–D complete.",
           ["Click 'Submit final' with no director row"],
           ["Toast error 'At least one director / beneficial owner required'.",
            "directors-gap red hint visible."],
           ["No POST /register/submit until fixed."],
           ""),
        tc("B-05", "Magic-link resume from email",
           "Draft exists.",
           ["Open /register/resume?token=<stored_token>"],
           ["Draft state fully restored (all fields, stepper resumes at correct step)."],
           ["GET /api/v1/registrations/resume?token=<t> → 200"],
           ""),
        tc("B-06", "Duplicate email rejected",
           "Vendor already active with same email.",
           ["Go to /register, enter existing email, submit"],
           ["Toast error 'A vendor with this email already exists'. Form stays populated."],
           ["POST /api/v1/registrations → 409"],
           ""),
    ], "registration-portal"),

    # -------------------------------------------------------------------
    ("C · 5-Portal Login", "Sovereign gateway picker (Admin, Management, Partners, Agents, Vendors).", [
        tc("C-01", "Portal grid renders",
           "None.",
           ["Go to /login"],
           ["Five gradient portal cards visible.",
            "Each has kicker, name, description, ENTER PORTAL CTA."],
           ["No API calls."],
           ""),
        tc("C-02", "Admin credential flow",
           "Portal grid.",
           ["Click 'System Administrator' card",
            "Login with adminsupport@pmcmanagers.com / Admin@12345"],
           ["Redirect to /admin/console.",
            "Response includes Bearer token + X-CSRF-Token (both required for subsequent admin endpoints)."],
           ["POST /api/v1/admin/auth/login → 200 {token, csrf_token}"],
           "test_credentials.md"),
        tc("C-03", "Vendor credential flow",
           "Portal grid.",
           ["Click 'Registered Vendors' card",
            "Login with manualvendor@pmcmanagers.com / Vendor@12345"],
           ["Redirect to /vendor/dashboard."],
           ["POST /api/v1/vendor/auth/login → 200"],
           ""),
        tc("C-04", "Wrong password path",
           "Portal grid.",
           ["Click any portal card, submit wrong password 3×"],
           ["Toast error 'Invalid credentials' on each attempt.",
            "After 5 attempts within 10 minutes, rate-limit banner appears."],
           ["POST /login → 401 · repeated 401 → 429 after threshold"],
           ""),
    ], "shared"),

    # -------------------------------------------------------------------
    ("D · Admin Console — Notices tab", "Draft, publish, corrigenda, Q&A.", [
        tc("D-01", "Create a new notice from Tender Builder template",
           "Admin logged in. At least one master template exists.",
           ["Admin → Notices → New notice",
            "Pick template PMC-KZ-CONSTR-001",
            "Fill required fields (title, country, deadline, budget)",
            "Click Publish now"],
           ["Modal closes. New row appears at top of Notices list with 'PUBLISHED' pill.",
            "Public /notices/{ref} shows the notice within ~30 s (CloudFront cache)."],
           ["POST /api/v1/notices → 201",
            "GET /api/v1/notices — new row present"],
           ""),
        tc("D-02", "EMD auto-compute honours slab",
           "New Notice modal open, tender value entered.",
           ["Click EMD Compute widget",
            "Verify applied slab preview + computed EMD"],
           ["Applied slab shows band + percent + floor + ceiling.",
            "Computed EMD non-editable unless override reason provided."],
           ["POST /api/v1/masters/emd/compute → 200 {computed, slab}"],
           ""),
        tc("D-03", "Publish a corrigendum",
           "Published notice exists.",
           ["Open notice → Corrigenda tab → New corrigendum",
            "Enter reason + change body → Publish"],
           ["Corrigendum row appears with is_active=true.",
            "Vendors get an email via Resend within 2 min."],
           ["POST /api/v1/corrigenda → 201"],
           ""),
        tc("D-04", "Withdraw a notice",
           "Published notice with no bids yet.",
           ["Open notice → 'Withdraw' action → confirm dialog"],
           ["Notice status flips to WITHDRAWN. Public detail returns 410."],
           ["DELETE /api/v1/notices/{ref} → 200",
            "GET public → 410 gone"],
           ""),
        tc("D-05", "Q&A publish path",
           "Vendor has submitted a public question on a notice.",
           ["Admin → Notices → open notice → Q&A queue",
            "Draft answer, mark 'Publish publicly', save"],
           ["Answer appears on public /notices/{ref} within 30 s."],
           ["POST /api/v1/notices/{ref}/qa/answer → 200"],
           ""),
    ], "admin-console"),

    # -------------------------------------------------------------------
    ("E · Admin Console — Tender Builder", "Master + draft library, AI section drafter, DPR ingestion.", [
        tc("E-01", "Clone a master to a new draft",
           "Admin logged in, ≥ 1 master template.",
           ["Admin → Tender Builder → Master library",
            "Click 'Clone as draft' on any master",
            "Confirm new draft appears in 'Your drafts'"],
           ["New draft opens with prefilled sections. Save button initially disabled (no edits)."],
           ["POST /api/v1/tender-templates/clone → 201"],
           ""),
        tc("E-02", "AI per-section drafter (v46o hotfix)",
           "Draft open.",
           ["Click 'Build with AI' inside any section",
            "Wait ≤ 20 s"],
           ["Section body auto-fills with 280-360 word HTML draft.",
            "Toast success 'AI draft generated'."],
           ["POST /api/v1/tender-templates/{tid}/sections/{code}/ai-draft → 200 body[]",
            "Backend proxies via the managed AI key → AI gateway endpoint"],
           "Regression check: prod uses the managed AI key (sk-*), no legacy LLM_API_KEY."),
        tc("E-03", "Async DPR ingestion (unlimited size · v46l)",
           "Draft open. Sample 100 MB PDF/DOCX.",
           ["Click 'Analyse DPR' → upload file",
            "Poll status card until 'completed'"],
           ["Progress bar advances through phases: extract → chunk map → reduce → draft.",
            "On completion, every section body is populated from the DPR text."],
           ["POST /api/v1/tender-pro/dpr/analyze-async → 202 {job_id}",
            "GET /api/v1/tender-pro/dpr/jobs/{job_id} → 200 {progress, phase, status}"],
           "Use any KMT DPR ≥ 500 pages."),
        tc("E-04", "Save-as-master",
           "Draft with all sections filled.",
           ["Click 'Save as master' → confirm"],
           ["Draft copied into masters library. Original draft remains editable."],
           ["POST /api/v1/tender-templates/{tid}/save-as-master → 201"],
           ""),
        tc("E-05", "Version snapshot + restore",
           "Draft with ≥ 3 edits.",
           ["Click History icon → pick prior snapshot → Restore"],
           ["Current draft saved as new snapshot, then reverted. Toast 'Restored older snapshot'."],
           ["POST /api/v1/tender-templates/{tid}/versions/{v}/restore → 200"],
           ""),
    ], "admin-console"),

    # -------------------------------------------------------------------
    ("F · Admin Console — Evaluation", "Rubric, scoring, envelope locking, award report.", [
        tc("F-01", "Enter valid rubric",
           "Admin logged in. Notice with bids exists.",
           ["Admin → Evaluation → enter notice_ref",
            "Adjust rubric so weights sum to 1.00",
            "Click Save rubric"],
           ["Toast 'Rubric saved'. Save button re-enabled after modification."],
           ["POST /api/v1/evaluations/rubric → 200"],
           ""),
        tc("F-02", "Rubric max gate (bug-blitz c)",
           "Rubric editor open.",
           ["Type commercial_weight = 1.5",
            "Click Save (or press Enter programmatically)"],
           ["Save button disabled + red opacity-40.",
            "rubric-errors list shows 'Commercial weight must be between 0 and 1'.",
            "Even a keyboard/programmatic click fires the veto: no 'Rubric saved' toast, no POST."],
           ["No POST /api/v1/evaluations/rubric"],
           "v46p defensive guard."),
        tc("F-03", "Lock technical envelope",
           "Rubric saved, ≥ 1 technical score submitted.",
           ["Click 'Lock Technical'"],
           ["Button flips to 'Technical · Sealed 🔒' with timestamp.",
            "Green banner records sealer + at-time.",
            "Further technical scoring rejected server-side with 409."],
           ["POST /api/v1/evaluations/lock-envelope?kind=technical → 200",
            "Attempted score after lock → 409"],
           ""),
        tc("F-04", "Locked-eval reopen (bug-blitz d)",
           "Both envelopes locked on notice PMC-NOT-2026-0020.",
           ["Close panel, reopen, re-enter same notice_ref"],
           ["Envelope status banner shows sealed at + by.",
            "locked-eval-notice banner appears.",
            "AwardReport auto-loads.",
            "BidScoreList inputs disabled + Save Technical / Save Commercial disabled."],
           ["GET /api/v1/evaluations/lock-state/{ref} → 200",
            "GET /api/v1/evaluations/award-report/{ref} → 200 {ranking, recommendation}"],
           "Verifies (d) fix."),
        tc("F-05", "Generate award report",
           "Both envelopes locked, all scores in.",
           ["Click 'Generate report'"],
           ["Recommendation banner + ranking table.",
            "Any bid below minimum_technical shows Qualifies=—."],
           ["POST /api/v1/evaluations/award-report/{ref} → 200"],
           ""),
        tc("F-06", "COI declaration",
           "Rubric saved.",
           ["Tick 'I have a conflict', enter details, click Declare COI"],
           ["Toast 'COI recorded'. Row appears in audit trail."],
           ["POST /api/v1/evaluations/coi → 200"],
           ""),
    ], "admin-console"),

    # -------------------------------------------------------------------
    ("G · Admin Console — Escrow", "EMDs, joint accounts, transaction lifecycle.", [
        tc("G-01", "Create joint escrow account",
           "Admin logged in.",
           ["Admin → Escrow → New account",
            "Enter PMC officer + vendor officer emails + name",
            "Create"],
           ["Row appears with status 'pending'. Both officers get invite email via Resend."],
           ["POST /api/v1/escrow/accounts → 201"],
           ""),
        tc("G-02", "Post EMD receipt",
           "Active joint account, bid submitted.",
           ["Escrow → New transaction → link to bid → enter amount, currency, receipt refs",
            "Save"],
           ["Transaction row shows state 'held', aging 0 d.",
            "Vendor portal EMD tracker updates within 1 poll cycle."],
           ["POST /api/v1/escrow/transactions → 201"],
           ""),
        tc("G-03", "Refund EMD",
           "EMD held, bid not awarded.",
           ["Open transaction → 'Initiate refund' → both officers sign",
            "Refund confirmed on payment rail"],
           ["State transitions held → refund_pending → refunded.",
            "Aging clock resets. Audit row for each signature."],
           ["PATCH /api/v1/escrow/transactions/{id}/refund → 200"],
           ""),
        tc("G-04", "Forfeit EMD (needs legal sign-off)",
           "EMD held, vendor withdrew after deadline.",
           ["Open transaction → 'Forfeit' → attach legal memo → both officers sign"],
           ["State transitions held → forfeited.",
            "Amount routes to sponsor holding account per Kazakhstan policy."],
           ["PATCH /api/v1/escrow/transactions/{id}/forfeit → 200"],
           ""),
    ], "admin-console"),

    # -------------------------------------------------------------------
    ("H · Admin Console — Reverse Auctions", "Draft, start, close, invite, live bidding.", [
        tc("H-01", "Draft an auction",
           "Notice PMC-NOT-2026-XXXX exists with bids.",
           ["Admin → Live Auctions → New auction",
            "Fill notice_ref, title, prices, decrement, duration, anti-snipe",
            "Click 'Draft'"],
           ["Row created with status 'draft'. Bidder link hidden."],
           ["POST /api/v1/reverse-auctions → 201"],
           ""),
        tc("H-02", "Start auction",
           "Draft exists.",
           ["Click 'Start' on the row"],
           ["Status flips to 'live', end_at populated, bidder URL exposed.",
            "Bulk-invite email fires to eligible bidders."],
           ["POST /api/v1/reverse-auctions/{id}/start → 200"],
           ""),
        tc("H-03", "Close auction manually",
           "Auction is live, ≥ 1 valid bid.",
           ["Click 'Close' → confirm"],
           ["Winner banner shows alias + winning_price.",
            "State becomes 'closed'."],
           ["POST /api/v1/reverse-auctions/{id}/close → 200 {winner}"],
           ""),
        tc("H-04", "View summary on mobile (bug-blitz e)",
           "Closed auction, viewport 390 × 844.",
           ["Open Admin → Live Auctions on iPhone SE emulator",
            "Tap 'View summary' on closed row"],
           ["Toolbar wraps cleanly (flex-wrap gap-y-2).",
            "'View summary' button fully inside card, no horizontal overflow.",
            "Summary panel renders below with start/floor/winning/savings columns."],
           ["No new API call — data already in row."],
           "v46p mobile fix."),
    ], "admin-console"),

    # -------------------------------------------------------------------
    ("I · Vendor Portal", "Vendor-facing dashboard, KYC, licences, bids, EMDs.", [
        tc("I-01", "Vendor dashboard loads",
           "Logged in as manualvendor@pmcmanagers.com.",
           ["Navigate to /vendor/dashboard"],
           ["KPIs render: bids submitted, bids awarded, EMD held, next deadline.",
            "Trust-badge widget renders scorecard band."],
           ["GET /api/v1/vendor/me → 200",
            "GET /api/v1/vendor/dashboard → 200"],
           ""),
        tc("I-02", "Submit a bid",
           "Logged in, open notice exists.",
           ["Vendor → Tenders → open notice → Bid",
            "Fill price, upload technical + commercial docs, submit"],
           ["Bid row appears in vendor's My Bids with status 'submitted'.",
            "EMD requirement banner appears if not yet posted."],
           ["POST /api/v1/bids → 201"],
           ""),
        tc("I-03", "Track bid status",
           "≥ 1 submitted bid.",
           ["Vendor → My Bids"],
           ["Each bid row shows status timeline: submitted → under review → eval-locked → awarded/rejected.",
            "Awarded bid shows PO number + LOA link."],
           ["GET /api/v1/vendor/bids → 200 items[]"],
           ""),
        tc("I-04", "Auction join (masked identity)",
           "Vendor invited to live auction.",
           ["Follow auction invite link → /vendor/auction/{id}"],
           ["Alias assigned (never real company name).",
            "Countdown clock live. Bid input allows only below current * (1 - decrement)."],
           ["POST /api/v1/reverse-auctions/{id}/register → 200 {alias}"],
           ""),
    ], "vendor-portal"),

    # -------------------------------------------------------------------
    ("J · Reports & Snapshot", "Stakeholder reports + on-demand snapshot to repo.", [
        tc("J-01", "Fetch stakeholder-report/tenders JSON",
           "Admin auth token in header.",
           ["curl -H 'Authorization: Bearer <t>' -H 'X-CSRF-Token: <c>' GET /api/v1/stakeholder-reports/tenders"],
           ["200 JSON with generated_at + items[]. Each item has notice_ref, bids_total, active_corrigenda, days_since_publish."],
           ["200"],
           ""),
        tc("J-02", "Fetch stakeholder-report/escrow CSV",
           "Same auth.",
           ["curl -X GET /api/v1/stakeholder-reports/escrow?format=csv"],
           ["Content-Type text/csv; two sections: --- accounts --- and --- transactions ---."],
           ["200"],
           ""),
        tc("J-03", "Save reports snapshot to disk (bug-blitz b)",
           "Same auth.",
           ["POST /api/v1/reports/snapshot"],
           ["Always returns valid JSON (ok, generated_at, files[], errors[]).",
            "Even on WeasyPrint failure the response parses cleanly — no HTML 500."],
           ["200 JSON (never text/html)"],
           "v46p safety wrapper."),
    ], "reports"),

    # -------------------------------------------------------------------
    ("K · PWA (v46p)", "Installable on Android + iOS. Offline app shell.", [
        tc("K-01", "Manifest served",
           "Preview URL up.",
           ["curl -s /manifest.json | jq ."],
           ["JSON with name, short_name, icons (192 + 512), start_url, display=standalone, theme_color."],
           ["200 application/json"],
           ""),
        tc("K-02", "iOS meta tags present",
           "None.",
           ["curl -s / | grep apple-mobile-web-app"],
           ["apple-mobile-web-app-capable=yes, status-bar-style=black-translucent, apple-touch-icon linked."],
           ["200"],
           ""),
        tc("K-03", "Install on Android (Chrome)",
           "Chrome ≥ 90, HTTPS.",
           ["Open the URL, wait 30 s (engagement heuristic)",
            "Chrome menu → 'Install app'"],
           ["App installs, launches in standalone window with PMC crest and navy splash."],
           [""],
           ""),
        tc("K-04", "Install on iOS (Safari 16.4+)",
           "iOS 16.4+.",
           ["Open URL in Safari → Share → 'Add to Home Screen'"],
           ["Icon on homescreen. Tap opens in standalone view; no Safari chrome."],
           [""],
           ""),
        tc("K-05", "Service worker caches app shell",
           "PWA installed.",
           ["Open DevTools → Application → Service Workers"],
           ["SW status = activated + running.",
            "Cache Storage lists 'pmc-shell-v46p' with HTML/CSS/JS and PMC crest."],
           [""],
           ""),
        tc("K-06", "API requests bypass cache",
           "Any online session.",
           ["Watch DevTools Network while browsing notices"],
           ["/api/* requests never marked 'from ServiceWorker'.",
            "Bid data always fresh from backend."],
           [""],
           ""),
        tc("K-07", "Offline shell shows",
           "PWA installed.",
           ["Toggle DevTools 'Offline'",
            "Reload the page"],
           ["App shell renders. Data endpoints show reconnect banner.",
            "Once back online, banner auto-clears within 1 poll cycle."],
           [""],
           ""),
    ], "pwa"),
]


CATEGORIES = [
    ("Public surfaces", ["A · Public Notice Board"]),
    ("Vendor onboarding", ["B · Vendor Registration"]),
    ("Auth", ["C · 5-Portal Login"]),
    ("Admin — content", ["D · Admin Console — Notices tab", "E · Admin Console — Tender Builder"]),
    ("Admin — decision", ["F · Admin Console — Evaluation"]),
    ("Admin — money", ["G · Admin Console — Escrow"]),
    ("Admin — auctions", ["H · Admin Console — Reverse Auctions"]),
    ("Vendor daily", ["I · Vendor Portal"]),
    ("Reporting", ["J · Reports & Snapshot"]),
    ("PWA (v46p)", ["K · PWA (v46p)"]),
]


def build_html():
    parts = []
    parts.append("""<!doctype html><html><head><meta charset='utf-8'>
<title>PMC Testing Manual v3</title>
<style>
  @page :first { background: #0B132B; margin: 0; }
  @page { size: A4; margin: 20mm 16mm 22mm 16mm;
    @top-right { content: "PMC Testing Manual v3"; font: 8.5pt Georgia; color: #94a3b8; }
    @bottom-left { content: "Confidential — Internal Use Only"; font: 8.5pt Georgia; color: #64748b; }
    @bottom-right { content: "Page " counter(page) " / " counter(pages); font: 8.5pt Georgia; color: #64748b; }
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='800' height='800'><g transform='translate(400,400) rotate(-30)'><text x='0' y='0' text-anchor='middle' font-family='Georgia' font-size='60' fill='rgba(15,31,58,0.05)' font-weight='700' letter-spacing='6'>CONFIDENTIAL — INTERNAL USE ONLY</text></g></svg>");
    background-position: center; background-repeat: no-repeat;
  }
  body { font: 10.5pt/1.55 Georgia, 'Times New Roman', serif; color: #0b1f3a; }
  h1 { font-size: 20pt; margin: 22pt 0 8pt; border-bottom: 2pt solid #0b1f3a; padding-bottom: 4pt; page-break-before: always; }
  h1:first-of-type { page-break-before: avoid; }
  h2 { font-size: 14pt; margin: 16pt 0 6pt; color: #0b1e3f; }
  h3 { font-size: 11pt; margin: 10pt 0 2pt; color: #1e293b; }
  p { margin: 4pt 0 8pt; }
  ul, ol { margin: 0 0 8pt 0; padding-left: 18pt; }
  li { margin-bottom: 3pt; }
  table { width: 100%; border-collapse: collapse; margin: 8pt 0 14pt; font-size: 9.5pt; }
  th, td { border: 0.5pt solid #cbd5e1; padding: 4pt 6pt; text-align: left; vertical-align: top; }
  th { background: #eef2f8; color: #0b1e3f; }
  code { font-family: 'Menlo', 'Courier New', monospace; font-size: 9.5pt; background: #f1f5f9; padding: 1pt 4pt; }
  .tc { margin: 12pt 0; padding: 8pt; border-left: 3pt solid #D4AF37; background: #fbfaf5; page-break-inside: avoid; }
  .tc-id { font-family: 'Menlo', 'Courier New', monospace; color: #D4AF37; font-weight: 700; }
  .cover { text-align: center; color: #fff; padding: 140pt 20pt 40pt; height: 240mm; page-break-after: always; }
  .cover .crest { width: 96pt; height: 96pt; margin: 0 auto 30pt; border: 2pt solid #D4AF37; display: flex; align-items: center; justify-content: center; font: 700 44pt Georgia; color: #D4AF37; }
  .cover .title { font-size: 40pt; letter-spacing: -0.5pt; color: #fff; line-height: 1.05; }
  .cover .sub { font-size: 14pt; color: rgba(255,255,255,0.7); margin-top: 22pt; letter-spacing: 0.05em; }
  .cover .rule { width: 60pt; height: 2pt; background: #D4AF37; margin: 40pt auto; }
  .cover .banner { display:inline-block; margin-top: 20pt; padding: 6pt 14pt; background: rgba(212,175,55,0.12); border: 0.5pt solid #D4AF37; color: #D4AF37; font-size: 9pt; letter-spacing: .18em; text-transform: uppercase; }
</style></head><body>""")

    # cover
    parts.append(f"""<div class="cover">
  <div class="crest">PMC</div>
  <div class="title">Testing Manual</div>
  <div class="title" style="font-size:24pt;color:#D4AF37;margin-top:14pt;">v3 · Sovereign Edition</div>
  <div class="rule"></div>
  <div class="sub">Per-module test cases · happy paths · edge cases · expected errors · HTTP codes</div>
  <div class="banner">{esc(BANNER)}</div>
</div>""")

    # foreword
    parts.append("""<h1>0 · How to use this manual</h1>
<p>Every module has a fixed test-case format. Read the <b>Precondition</b> first — if you cannot satisfy it, either skip or arrange test data before continuing. Then follow <b>Steps</b> in order; do not paraphrase. Compare the actual UI against <b>Expected UI</b> and the network log against <b>Expected API</b>. Record any deviation on the tracker with the test-case ID.</p>
<p>Credentials live in <code>/app/memory/test_credentials.md</code>. Admin endpoints require <b>both</b> <code>Authorization: Bearer &lt;token&gt;</code> <b>and</b> <code>X-CSRF-Token: &lt;csrf_token&gt;</code>. The login response returns both.</p>
<p>Every AI-touched surface is advisory only; a failed AI call must never block a decision. If the AI proxy times out, the human path is always live.</p>
<h2>Global error codes</h2>
<table><tr><th>Code</th><th>Meaning</th><th>Action</th></tr>
<tr><td>400</td><td>Bad request — payload validation failed</td><td>Check the field-level error map returned in the body.</td></tr>
<tr><td>401</td><td>Missing / expired token</td><td>Log in again. If persistent, clear cookies.</td></tr>
<tr><td>403</td><td>Wrong role</td><td>Check the require_role gate on the endpoint. Impersonate the right role.</td></tr>
<tr><td>404</td><td>Entity not found</td><td>Confirm the ref/id exists.</td></tr>
<tr><td>409</td><td>Conflict — envelope locked, duplicate resource, race</td><td>Refresh state; do not force-retry.</td></tr>
<tr><td>413</td><td>Payload too large — DPR &gt; 200 MB</td><td>Split and use analyze-async endpoint.</td></tr>
<tr><td>422</td><td>Model validation error</td><td>Check request schema in the OpenAPI spec.</td></tr>
<tr><td>429</td><td>Rate-limited</td><td>Wait per Retry-After header.</td></tr>
<tr><td>502 / 504</td><td>Upstream (LLM, DocuSign, Stripe) hiccup</td><td>Retry with exponential backoff. Sev-3 alert if persistent.</td></tr>
</table>""")

    # index
    parts.append("<h1>1 · Module index</h1>")
    for cat, mods in CATEGORIES:
        parts.append(f"<h2>{esc(cat)}</h2><ul>")
        for m in mods:
            parts.append(f"<li>{esc(m)}</li>")
        parts.append("</ul>")

    # module sections
    for i, (title, blurb, cases, _slug) in enumerate(MODULES, start=2):
        parts.append(f"<h1>{i} · Module — {esc(title)}</h1>")
        parts.append(f"<p><i>{esc(blurb)}</i></p>")
        for c in cases:
            parts.append("<div class='tc'>")
            parts.append(f"<h3><span class='tc-id'>{esc(c['id'])}</span> · {esc(c['title'])}</h3>")
            parts.append(f"<p><b>Precondition.</b> {esc(c['pre'])}</p>")
            parts.append("<p><b>Steps</b></p><ol>")
            for s in c["steps"]:
                parts.append(f"<li>{esc(s)}</li>")
            parts.append("</ol>")
            parts.append("<p><b>Expected UI</b></p><ul>")
            for u in c["ui"]:
                parts.append(f"<li>{esc(u)}</li>")
            parts.append("</ul>")
            if c["api"]:
                parts.append("<p><b>Expected API</b></p><ul>")
                for a in c["api"]:
                    parts.append(f"<li><code>{esc(a)}</code></li>")
                parts.append("</ul>")
            if c["data"]:
                parts.append(f"<p><b>Test data / notes.</b> {esc(c['data'])}</p>")
            parts.append("</div>")

    # sign-off
    n = len(MODULES) + 2
    parts.append(f"<h1>{n} · Sign-off</h1><p>This testing manual is versioned under <code>/app/deliverables/v46_manual/build/</code>. Regenerate with <code>python3 /app/tools/manual/testing_manual.py</code> whenever a module changes materially. Every test-case ID is stable — do not renumber; add new cases with a new letter suffix (e.g. F-04a).</p>")

    parts.append("</body></html>")
    return "".join(parts)


def main():
    doc = build_html()
    html_path = OUT / "PMC_v3_Testing_Manual.html"
    html_path.write_text(doc)
    pdf_path = OUT / "PMC_v3_Testing_Manual.pdf"
    HTML(string=doc).write_pdf(str(pdf_path))
    print(f"Testing manual: {pdf_path.stat().st_size/1024:.1f} KB")


if __name__ == "__main__":
    main()
