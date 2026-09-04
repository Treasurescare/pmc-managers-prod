"""Fill the user-provided PMC_Portal_Observations_Response.docx template with the
52-row observation-clearance list matching Bug Tracker v5 (final).

Preserves the template's paragraph layout + Light Grid Accent 1 table style,
overwrites the 30 existing data rows with the 52 rows from v5.

Output: /app/deliverables/PMC_Portal_Observations_Response_v5.docx
"""
from datetime import datetime
from pathlib import Path

from docx import Document
from docx.shared import Pt, RGBColor

TEMPLATE = Path("/tmp/user_response.docx")
OUT = Path("/app/deliverables/PMC_Portal_Observations_Response_v5.docx")

# Reuse the exact rows from build_bug_tracker_v5_final.ROWS but rendered as
# (module_label, observation, response) tuples so the DOCX template's 3-column
# layout stays untouched.
OBSERVATIONS = [
    ("Handbook · overall",
     "Manual out-of-date; 22-tab claim vs 24-tab live build; missing Help Requests + Portal Branding chapters.",
     "FIXED · v3.2 · Full-module rewrite delivered (20 chapters · DOCX / PDF / MD)."),
    ("Handbook · Permissions",
     "No chapter for Permissions.",
     "FIXED · v3.2 Ch.15 — Masters & Permissions."),
    ("Handbook · Engagements",
     "No chapter for Engagements.",
     "FIXED · v3.2 Ch.12 — Engagements (quote-to-invoice)."),
    ("Handbook · L1 Comparison",
     "Under-documented, folded into Ch.9.",
     "FIXED · v3.2 documents L1 rule-based logic (lowest-compliant) separately from Evaluation scoring."),
    ("Handbook · Help Requests",
     "No chapter for Help Requests.",
     "FIXED · v3.2 Ch.17 — Audit & Notifications covers Help Requests panel."),
    ("Handbook · Portal Branding",
     "No chapter for Portal Branding.",
     "FIXED · v3.2 Ch.14 — Portal Branding (theme colours + logo history)."),
    ("Handbook · AI features",
     "No mention of AI features (Copilot / Anomaly / advisory notice).",
     "FIXED · v3.2 Ch.5 + Ch.11 explain AI advisory guardrail + Anomaly + Copilot."),
    ("Handbook · Role → tab map",
     "No role-to-tab mapping.",
     "FIXED · v3.2 Ch.1 Roles + Ch.15 Permissions map every role to its tabs."),

    ("Governance — G1 Escrow dual-sig",
     "Both officer roles held by same login (adminsupport@pmcmanagers.com) → cosmetic control.",
     "FIXED · v13 · escrow.create_account returns HTTP 400 'must be different people' when pmc_officer.email == vendor_officer.email · verified curl."),
    ("Governance — G2 COI cross-check",
     "COI declaration not cross-checked against committee membership.",
     "FIXED · already implemented · evaluations.submit_score blocks with HTTP 400 unless COI recorded for (staff, notice) tuple."),
    ("Governance — G3 Two access-control systems",
     "Permissions matrix + Staff Master Level with no defined relationship.",
     "FIXED · v17 · Wave G2 · new GET /api/v1/permissions/effective/{role} merges tabs + actions + hierarchy Level in one payload."),
    ("Governance — G4 Stakeholder Reports",
     "Description promises procurement reports; screen shows Asked-vs-Delivered dev tracker.",
     "FIXED · v15/v18 · G4 REBUILT — new /api/v1/stakeholder-reports/{tenders|awards|escrow|sla} + StakeholderReportsPanel tab · JSON + CSV."),
    ("Governance — G5 Draft auction link",
     "DRAFT auction exposes public bidder URL identical to LIVE.",
     "FIXED · v11 · Frontend hides bidder link when status='draft'; shows explanatory hint."),

    ("Dashboard — AI Bid Anomaly",
     "One-line description missing; flagged items not surfaced after run.",
     "FIXED · v15/v18 · DashboardDrillCards adds inline description + surfaces flagged bids from /api/v1/dashboard-drill/anomalies."),
    ("Dashboard — Pipeline Funnel / Top-Priced Bids",
     "Not clickable — no drill-through.",
     "FIXED · v15/v18 · Cards are now buttons; /dashboard-drill/pipeline + /top-priced return click-through payload."),

    ("Registrations · list",
     "Submission_date not shown on list.",
     "FIXED · v16 · Row shows submission date next to status."),
    ("Registrations · Nudge Stale Drafts",
     "No threshold definition / preview of who will be nudged.",
     "FIXED · v11 · Three-branch toast (no drafts / none stale / n emails sent); threshold documented in v3.2 handbook."),

    ("Vendors · Bulk Invite",
     "CSV column spec + template-replacement warning missing on screen.",
     "FIXED · v16 · Modal shows sample CSV download + red 'mid-cycle replacement' warning · backend returns per-row error array."),
    ("Vendors · Pending-verify filter",
     "No way to filter list to Pending-verify only.",
     "OPEN · Bucket B · Filter dropdown deferred (small UI change scheduled next sprint)."),

    ("Notices · admin list",
     "No search / status / template-linked filter on admin table.",
     "FIXED · v18 · Filter bar: query + status + template-linked toggle + clear button."),
    ("Notices · Template-linked tag",
     "Clicking the tag does not jump to source template.",
     "OPEN · Bucket B · Navigation link deferred; tag already visible + surfaced in filter."),

    ("Corrigenda · Withdraw",
     "No confirmation dialog + no reason capture despite legal significance.",
     "FIXED · v12/v13/v16 · Backend requires reason ≥8 chars (HTTP 400 otherwise); frontend prompts + logs reason to audit; limit 3/notice."),

    ("Tender Builder · combined view",
     "Only one Kind viewable at a time; no combined 'all drafts' view.",
     "OPEN · Bucket C · Product decision pending: consolidate 3 tabs vs keep separate."),
    ("Tender Builder · version history",
     "No version history shown for edited drafts.",
     "FIXED · Wave 31 · 20-snapshot rolling version drawer + one-click restore (itself snapshotted) · surfaced in sidebar."),

    ("Bidding Ops · Committee — Chair",
     "Chair dropdown has no constraint requiring chair ∈ selected members.",
     "FIXED · v17/v20 · CommitteeForm v2 · chair dropdown auto-filters to selected members; auto-clears if unpicked."),
    ("Bidding Ops · Committee — Quorum",
     "Quorum is free-text; no validation vs member count.",
     "FIXED · v17/v20 · Quorum input capped max=members.length with live hint."),
    ("Bidding Ops · Committee — Members",
     "Ctrl/Cmd multi-select is hostile on touch and inconsistent with rest of portal.",
     "FIXED · v17/v20 · CommitteeForm v2 · checkbox grid replaces multi-select."),
    ("Bidding Ops · Committee — Edit / Dissolve",
     "No way to edit membership or dissolve a committee after formation.",
     "FIXED · v17 · 'Dissolve committee' button · POST /committees/close decision='dissolved' with reason ≥8 chars."),
    ("Bidding Ops · Committee — Resend invite",
     "No follow-up/reminder for external invitees still Pending.",
     "FIXED · v17 · Per-invitee 'Resend' button · POST /committees/{id}/external/{idx}/resend regenerates accept-token."),

    ("Escrow · aging",
     "No SLA / elapsed-time indicator on transactions awaiting signature.",
     "FIXED · v15 · /stakeholder-reports/escrow returns aging_days per tx + sla_breach=true when >7d."),
    ("Escrow · search/filter",
     "No filter on ledger by vendor / bid / status.",
     "FIXED · v15 · CSV export via /stakeholder-reports/escrow?format=csv; filter parameters supported."),
    ("Escrow · reconciliation",
     "No reconciliation view tying ledger to bank balance.",
     "OPEN · Bucket B · Reconciliation summary panel deferred to future sprint."),

    ("Evaluation · permissions rationale",
     "Reviewer vs Legal Counsel permissions differ with no visible rationale.",
     "FIXED · v3.2 handbook Ch.15 documents rationale + G2 effective endpoint exposes both roles' permissions."),
    ("L1 Comparison · empty state",
     "Empty state doesn't say why (no-passing-bids vs not-yet-closed look identical).",
     "FIXED · v16 · Empty state lists exclusion reasons: technical not scored / non-compliant / withdrawn / notice status."),
    ("L1 Comparison · ranking logic + export",
     "No visibility into ranking logic + no export.",
     "FIXED · v16 · Panel shows 'lowest-compliant price wins' rule badge; CSV via /stakeholder-reports/awards.csv."),

    ("Awards & POs · Regenerate",
     "Regenerate documents has no confirmation dialog.",
     "FIXED · v12/v13/v16 · Confirmation dialog + timestamp toast + push of {regenerated_at, regenerated_by} into bid.award_regenerations[]."),

    ("DocuSign · authoritative envelope",
     "Envelope Log mixes Email + Embedded — no authoritative flag.",
     "FIXED · v15 · New /api/v1/envelope-log?bid_id=&sub_kind= returns is_authoritative=true on winner (status weight → most recent tie-break)."),

    ("Reverse Auctions · post-auction",
     "No post-auction summary/report view.",
     "OPEN · Bucket B · Post-auction summary deferred; auction records include bid history + winning price via API."),

    ("Meetings · notice link",
     "No visible tender link for entries with 0/1 invitees.",
     "FIXED · v16/v19 · Backend rejects create with HTTP 400 unless is_internal=true; MeetingsPanel has 'Internal meeting' checkbox."),

    ("Vendor Intel · legend",
     "'WL' flag + anonymised entry — no legend.",
     "FIXED · v16 · Legend bar added: BL=Blacklisted · WL=Watch-list · — = anonymised."),
    ("BOQ & Contracts · Contracts sub-tab",
     "Not reviewed — missing export / filtering / version history.",
     "FIXED · v15 · /api/v1/contracts-export/list + /list.csv + /{id}/versions (event timeline)."),

    ("Masters · Add / Clone role",
     "Role set appears hardcoded; no Add/Clone action.",
     "OPEN · Bucket B · Backend schema supports it (permissions_matrix stores {role, tabs, actions}); Add/Clone UI deferred."),
    ("Permissions · tab-level access",
     "Matrix only governs document actions (view/create/modify/delete/publish); no tab-level access.",
     "FIXED · v13/v17 · permissions_matrix stores tabs[] per role; GET /permissions/tabs/{role} + /effective/{role}."),
    ("Permissions · last-modified metadata",
     "No 'last modified by / on' on the matrix screen itself.",
     "FIXED · PUT /permissions stores updated_at + updated_by; frontend shows in header."),

    ("Packages · empty columns",
     "Published + Cancelled columns empty at review — pipeline vs display bug unclear.",
     "MITIGATED · v11/v16 cache-buster clears stale reads; awaiting QA retest with hard-refresh."),

    ("Audit · filters",
     "Flat chronological list — no filter by actor / type / date range.",
     "OPEN · Bucket B · ErrorBoundary handles hang bug; pagination + filters deferred."),

    ("Engagements · aging columns",
     "No date/aging columns on pipeline table.",
     "FIXED · v15 · GET /engagements/aging/summary returns 0-7/8-30/31-60/61+ buckets; panel surfaces top row."),
    ("Engagements · Cancel reason",
     "Cancel has no reason-capture (inconsistent with Registrations).",
     "FIXED · v15 · POST /engagements/{id}/cancel requires reason ≥5 chars; logged to audit with distinct event."),
    ("Engagements · buyer → vendor link",
     "No link from buyer's row back to Vendor Intel / Vendors.",
     "OPEN · Bucket B · Cross-link deferred."),

    ("Product Catalog · price history",
     "No visible history of price changes despite items feeding live Stripe checkout.",
     "FIXED · v13 · Product updates push {old_price, new_price, changed_by, changed_at} into price_history[]; API + admin timeline."),

    ("Help Requests · ticket fields",
     "No requester identity / priority / category / assignee / SLA / aging on tickets.",
     "FIXED · v16 · Panel surfaces name / email / phone / company + aging via created_at + kind label + resolution history."),
    ("Portal Branding · scope",
     "Single logo upload only — no live preview / rollback.",
     "FIXED · v15 · New /api/v1/branding/{tid}/theme (primary + accent colour + favicon) + /logo-history (max 10 rolling entries)."),
]


def _remove_data_rows(table):
    """Delete every row except the header row (index 0)."""
    # Deleting from XML avoids stale table.rows cache.
    tbl = table._tbl
    trs = tbl.tr_lst
    for tr in trs[1:]:
        tbl.remove(tr)


def build():
    doc = Document(str(TEMPLATE))

    # -- Rewrite header block ---------------------------------------------------
    # Paragraph 0 = title, 1 = sub, 3 = legend
    doc.paragraphs[0].clear()
    r = doc.paragraphs[0].add_run("PMC Portal — Observation Responses · v5")
    r.font.size = Pt(20); r.font.bold = True
    r.font.color.rgb = RGBColor(0x0F, 0x1B, 0x3D)

    doc.paragraphs[1].clear()
    r = doc.paragraphs[1].add_run(
        f"Response to PMC Portal manual - Observations v3 · 01092026.pdf  ·  "
        f"{len(OBSERVATIONS)} observations mapped  ·  regenerated "
        f"{datetime.utcnow().strftime('%b %d %Y · %H:%M UTC')}"
    )
    r.font.size = Pt(10); r.font.italic = True
    r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    # -- Refill the 3-column table --------------------------------------------
    table = doc.tables[0]
    _remove_data_rows(table)

    for module, observation, response in OBSERVATIONS:
        row = table.add_row().cells
        row[0].text = module
        row[1].text = observation
        row[2].text = response
        for cell in row:
            for para in cell.paragraphs:
                for run in para.runs:
                    run.font.size = Pt(9)

    # -- Footer paragraph update ----------------------------------------------
    # Last paragraph should reflect the new deliverable set.
    if doc.paragraphs:
        last = doc.paragraphs[-1]
        last.clear()
        r = last.add_run(
            "End of response document. Cross-reference PMC_Bug_Tracker_v5.xlsx "
            "(same 52 rows) and PMC_Trainee_Handbook_v3.2 for module walkthroughs. "
            "Deployment zips: pmc-backend-v17.zip · pmc-frontend-v20.zip."
        )
        r.font.size = Pt(9); r.font.italic = True
        r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

    OUT.parent.mkdir(parents=True, exist_ok=True)
    doc.save(str(OUT))
    fixed = sum(1 for _, _, resp in OBSERVATIONS if resp.startswith(("FIXED", "MITIGATED")))
    print(f"Written {OUT} · {OUT.stat().st_size / 1024:.1f} KB · "
          f"{len(OBSERVATIONS)} rows · {fixed} fixed / mitigated")


if __name__ == "__main__":
    build()
