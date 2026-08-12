"""Comprehensive Testing Flowchart — SVG generator for the QA testing plan.

Companion to _flowchart.py (architecture) and _userguide.py (user journey).
This one is a swim-lane diagram of the entire QA test suite by persona so a
QA engineer or investor can see exactly what to test and in what order.
"""


def build_testing_flowchart_svg() -> str:
    """Returns a swim-lane SVG (~1600 x 2000) covering 8 test phases across
    Public / Vendor / Admin / Staff (Escrow/Certifier/Legal/Accounting) /
    Committee lanes. ~55 numbered test steps."""

    # ------------------------------------------------------------------
    # SVG boilerplate: markers, styles, and lane backgrounds
    # ------------------------------------------------------------------
    header = """<?xml version='1.0' encoding='UTF-8'?>
<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 1600 2100'
     width='1600' height='2100' preserveAspectRatio='xMidYMid meet'
     font-family='Calibri, Arial, sans-serif' font-size='13'>
  <defs>
    <marker id='tf-arr' viewBox='0 0 10 10' refX='9' refY='5' markerUnits='strokeWidth'
            markerWidth='9' markerHeight='9' orient='auto'>
      <path d='M 0 0 L 10 5 L 0 10 z' fill='#0b1f3a'/>
    </marker>
    <style>
      .lane-bg      { fill: #f8fafc; stroke: #cbd5e1; stroke-width: 1; stroke-dasharray: 4 3; }
      .lane-label   { fill: #0b1f3a; font-weight: 700; font-size: 15px; }
      .phase-band   { fill: #eef2ff; stroke: #4f46e5; stroke-width: 1; }
      .phase-title  { fill: #1e1b4b; font-weight: 700; font-size: 14px; }
      .box          { fill: #ffffff; stroke: #0b1f3a; stroke-width: 1.4; rx: 6; }
      .box-public   { fill: #f3f4f6; stroke: #374151; }
      .box-vendor   { fill: #d1fae5; stroke: #065f46; }
      .box-admin    { fill: #ede9fe; stroke: #6b21a8; }
      .box-staff    { fill: #fef3c7; stroke: #92400e; }
      .box-comm     { fill: #ffe4e6; stroke: #9f1239; }
      .box-title    { font-weight: 700; fill: #0b1f3a; font-size: 12.5px; }
      .box-sub      { fill: #475569; font-size: 11px; }
      .step-num     { fill: #94a3b8; font-weight: 800; font-size: 18px; }
      .arrow        { stroke: #0b1f3a; stroke-width: 1.4; fill: none; }
      .header-title { fill: #0b1f3a; font-weight: 700; font-size: 22px; }
      .header-sub   { fill: #475569; font-size: 12px; }
      .pill         { fill: #0b1f3a; }
      .pill text    { fill: #ffffff; font-weight: 700; font-size: 11px; }
      .critical     { fill: #dc2626; font-weight: 700; }
    </style>
  </defs>

  <rect x='0' y='0' width='1600' height='2100' fill='#ffffff'/>

  <text x='60' y='42' class='header-title'>PMC Managers v2 — Comprehensive Testing Flowchart</text>
  <text x='60' y='62' class='header-sub'>55 numbered test scenarios across 8 phases and 5 personas · investor-demo QA kit</text>
"""

    # ------------------------------------------------------------------
    # Lane backgrounds (persona rows)
    # ------------------------------------------------------------------
    lanes = [
        ("Public / Anonymous",   85,  330, "#374151"),
        ("Vendor",              335,  350, "#065f46"),
        ("Admin",               690,  365, "#6b21a8"),
        ("Staff (Escrow · Certifier · Legal · Accounting)", 1080, 380, "#92400e"),
        ("Committee",          1470,  220, "#9f1239"),
    ]
    lane_svg = ""
    for label, y, h, colour in lanes:
        lane_svg += f"""
  <rect class='lane-bg' x='60' y='{y}' width='1480' height='{h}'/>
  <text x='75' y='{y + 20}' class='lane-label' fill='{colour}'>{label}</text>
"""

    # ------------------------------------------------------------------
    # Phase bands (vertical divisions) - short titles to fit 170px width
    # ------------------------------------------------------------------
    phases = [
        ("1 · Discovery",         100),
        ("2 · Register",          280),
        ("3 · Publish",           450),
        ("4 · Bid + EMD",         620),
        ("5 · Evaluate",          810),
        ("6 · Award",            1010),
        ("7 · Auctions",         1200),
        ("8 · Escrow",           1390),
    ]
    phase_svg = ""
    for title, x in phases:
        phase_svg += f"""
  <rect class='phase-band' x='{x}' y='80' width='170' height='22'/>
  <text x='{x + 8}' y='96' class='phase-title'>{title}</text>
"""

    # ------------------------------------------------------------------
    # Test-step boxes (num, x, y, w, h, lane_class, title, sub)
    # ------------------------------------------------------------------
    boxes = [
        # Public
        (1,  100, 120, 160, 55, "box-public", "Notice Board loads",       "GET /notices/public · 3 col grid renders"),
        (2,  100, 190, 160, 55, "box-public", "Notice search + filter",   "keyword, org, status, deadline"),
        (3,  280, 120, 160, 55, "box-public", "Notice detail + docs",     "download attachments, corrigenda banner"),
        (4,  280, 190, 160, 55, "box-public", "Q&A public thread",        "vendor question → admin reply visible"),
        (5,  450, 120, 160, 55, "box-public", "Public roadmap",           "/roadmap read-only status pills"),

        # Vendor lane
        (6,  280, 355, 160, 55, "box-vendor", "Register Sections A–E",    "vendor self-registration, uploads"),
        (7,  280, 425, 160, 55, "box-vendor", "Email verification",       "click link, set password"),
        (8,  280, 495, 160, 55, "box-vendor", "Login + MFA setup",        "/vendor/login, TOTP QR scan"),
        (9,  280, 565, 160, 55, "box-vendor", "Update profile / GDPR",    "export data JSON download"),
        (10, 620, 355, 160, 55, "box-vendor", "Submit bid + line items",  "/vendor/bid/new/:noticeRef"),
        (11, 620, 425, 160, 55, "box-vendor", "Pay EMD via Stripe",       "test card 4242 4242 4242 4242"),
        (12, 620, 495, 160, 55, "box-vendor", "Pay EMD sandbox (PP/Kaspi)","in-app demo checkout"),
        (13, 620, 565, 160, 55, "box-vendor", "Envelope open (Two-cover)","technical envelope only"),
        (14, 1200,355, 160, 55, "box-vendor", "Join reverse auction",    "/vendor/auction/:aid, submit bid"),
        (15, 1200,425, 160, 55, "box-vendor", "Enable auto-bid rule",     "set floor + decrement"),
        (16, 1200,495, 160, 55, "box-vendor", "Join Zoom / Jitsi meeting","/meet/:token public join"),
        (17, 1010,565, 160, 55, "box-vendor", "Sign contract (embedded)", "DocuSign iframe, embedded delivery"),
        (18, 1010,635, 160, 55, "box-vendor", "Download signed PDF",      "/mine/envelopes/{id}/combined-pdf"),

        # Admin lane
        (19, 100, 700, 160, 55, "box-admin",  "Admin login",              "/admin/login, session cookie"),
        (20, 100, 770, 160, 55, "box-admin",  "Dashboard KPIs render",    "notices, bids, vendors counters"),
        (21, 280, 700, 160, 55, "box-admin",  "Approve vendor reg",       "Section A–E review, activate"),
        (22, 280, 770, 160, 55, "box-admin",  "Bulk invite vendors",      "CSV → email dispatch"),
        (23, 450, 700, 160, 55, "box-admin",  "Publish tender",           "Tender Template Builder wizard"),
        (24, 450, 770, 160, 55, "box-admin",  "Publish corrigendum",      "auto-numbered, deadline update"),
        (25, 450, 840, 160, 55, "box-admin",  "Answer Q&A",               "admin reply → public"),
        (26, 620, 700, 160, 55, "box-admin",  "Financial envelope open",  "post-technical shortlist"),
        (27, 620, 770, 160, 55, "box-admin",  "L1 comparison table",      "auto-rank by amount"),
        (28, 810, 700, 160, 55, "box-admin",  "Setup evaluation rubric",  "criteria + weights"),
        (29, 810, 770, 160, 55, "box-admin",  "Nominate committee",       "internal + external members"),
        (30, 810, 840, 160, 55, "box-admin",  "Assign certifier",         "site inspection dispatch"),
        (31, 1010,700, 160, 55, "box-admin",  "Award bid",                "auto-generate PO/SLA/Contract"),
        (32, 1010,770, 160, 55, "box-admin",  "Send DocuSign envelope",   "pick delivery embedded/email"),
        (33, 1010,840, 160, 55, "box-admin",  "Envelope status live",     "webhook updates panel"),
        (34, 1200,700, 160, 55, "box-admin",  "Start reverse auction",    "min-decrement, anti-snipe"),
        (35, 1200,770, 160, 55, "box-admin",  "Schedule meeting",         "Zoom/Jitsi + calendar dispatch"),
        (36, 1390,700, 160, 55, "box-admin",  "Audit Copilot query",      "AI insights on any timeframe"),
        (37, 1390,770, 160, 55, "box-admin",  "Export ledger + reports",  "flowchart, comparative, XLSX"),

        # Staff lane
        (38, 620,1085, 160, 55, "box-staff",  "Escrow: accept EMD",       "confirm payment reconciled"),
        (39, 810,1085, 160, 55, "box-staff",  "Certifier: site inspect",  "checklist + photo evidence"),
        (40, 810,1155, 160, 55, "box-staff",  "Certifier: verify vendor", "KYC + doc match"),
        (41, 810,1225, 160, 55, "box-staff",  "Legal: KYC clearance",     "MFA-gated approval"),
        (42, 1010,1085,160, 55, "box-staff",  "Accounting: sign-off",     "MFA-gated financial approve"),
        (43, 1390,1085,160, 55, "box-staff",  "Escrow: release funds",    "vendor bank details verified"),
        (44, 1390,1155,160, 55, "box-staff",  "Escrow officer public",    "magic-link /escrow/officer/:token"),

        # Committee lane
        (45, 810,1480, 160, 55, "box-comm",   "Committee accept invite",  "/committee/accept/:token"),
        (46, 810,1550, 160, 55, "box-comm",   "Score bid on rubric",      "per-criterion 0-10"),
        (47, 810,1620, 160, 55, "box-comm",   "Bid pack rendering",       "line items, docs, vendor intel"),

        # Cross-phase / observability
        (48, 100, 850, 160, 55, "box-admin",  "Notifications bell",       "role-scoped, live poll"),
        (49, 100, 920, 160, 55, "box-admin",  "Impersonate role dropdown","support flow diagnosis"),
        (50, 280, 840, 160, 55, "box-admin",  "Add tenant + skin",        "?tenant=DEMO-CORP color test"),
        (51, 100, 990, 160, 55, "box-admin",  "Mobile responsive audit",  "375px, 768px, 1024px probes"),
        (52, 280, 910, 160, 55, "box-admin",  "i18n switch EN/RU/KK",     "all admin panels render"),

        # Auto-gen / audit / regression
        (53, 1390,1225,160, 55, "box-comm",   "Regen SoT docs",           "POST /reports/snapshot"),
        (54, 1390,1480,160, 55, "box-comm",   "Test-plan endpoint",       "GET /reports/test-plan.pdf"),
        (55, 1390,1550,160, 55, "box-comm",   "Test-IDs registry",        "GET /reports/test-ids.txt"),
    ]
    box_svg = ""
    for num, x, y, w, h, cls, title, sub in boxes:
        box_svg += f"""
  <rect class='box {cls}' x='{x}' y='{y}' width='{w}' height='{h}'/>
  <text x='{x + 8}' y='{y + 18}' class='box-title'>{title}</text>
  <text x='{x + 8}' y='{y + 36}' class='box-sub'>{sub}</text>
  <text x='{x + w - 22}' y='{y + h - 6}' class='step-num'>{num:02d}</text>
"""

    # Simple arrows connecting phase-to-phase within each persona lane
    arrows_svg = """
  <path class='arrow' d='M 260 145 L 285 145' marker-end='url(#tf-arr)'/>
  <path class='arrow' d='M 440 145 L 460 145' marker-end='url(#tf-arr)'/>
  <path class='arrow' d='M 440 380 L 620 380' marker-end='url(#tf-arr)'/>
  <path class='arrow' d='M 800 380 L 1010 380 L 1010 610' marker-end='url(#tf-arr)'/>
  <path class='arrow' d='M 1180 725 L 1200 725' marker-end='url(#tf-arr)'/>
  <path class='arrow' d='M 180 725 L 100 725' marker-end='url(#tf-arr)' opacity='0'/>
"""

    footer = """
  <text x='60' y='2050' class='header-sub'>
    Legend — gray: Public · green: Vendor · purple: Admin · yellow: Staff · pink: Committee.
    Every box maps to a data-testid attribute in the frontend. Run each box top-to-bottom, left-to-right.
    Report failures with the step number.
  </text>
  <text x='60' y='2075' class='header-sub'>
    Boot the QA session with adminsupport@pmcmanagers.com / Admin@123 (rotate before demo) · seeded staff + vendor accounts in test_credentials.md.
  </text>
</svg>"""

    return header + lane_svg + phase_svg + box_svg + arrows_svg + footer
