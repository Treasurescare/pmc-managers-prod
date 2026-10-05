"""Assemble /app/deliverables/manual_v51u_shots/*.png into a themed PDF.

Theme matches the current app (Option E — forest navy #0F3B2E, cream
#F6F2E9, brass #B08E4A). Produces /app/deliverables/PMC_Master_Training_Manual_v6.pdf
"""
from __future__ import annotations
import re
from pathlib import Path
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (SimpleDocTemplate, Paragraph, Spacer, PageBreak,
                                 Image as RLImage, KeepTogether)
from PIL import Image as PILImage

SHOTS = Path("/app/deliverables/manual_v51u_shots")
OUT = Path("/app/deliverables/PMC_Master_Training_Manual_v6.pdf")

NAVY = colors.HexColor("#0F3B2E")
CREAM = colors.HexColor("#F6F2E9")
BRASS = colors.HexColor("#B08E4A")
INK = colors.HexColor("#0B1A14")
MUTE = colors.HexColor("#5A5A57")

ss = getSampleStyleSheet()
title_s = ParagraphStyle("T", parent=ss["Title"], fontName="Helvetica-Bold",
                          fontSize=28, leading=32, textColor=NAVY)
sub_s   = ParagraphStyle("S", parent=ss["Normal"], fontName="Helvetica",
                          fontSize=12, leading=16, textColor=MUTE)
h1 = ParagraphStyle("H1", parent=ss["Heading1"], fontName="Helvetica-Bold",
                    fontSize=22, leading=26, textColor=NAVY, spaceAfter=10, spaceBefore=16)
h2 = ParagraphStyle("H2", parent=ss["Heading2"], fontName="Helvetica-Bold",
                    fontSize=14, leading=18, textColor=BRASS,
                    spaceAfter=6, spaceBefore=12)
body = ParagraphStyle("B", parent=ss["BodyText"], fontName="Helvetica",
                      fontSize=10, leading=13.5, textColor=INK, spaceAfter=5)
cap = ParagraphStyle("Cap", parent=body, fontSize=9, textColor=MUTE,
                      alignment=0, spaceAfter=10)
eyebrow = ParagraphStyle("E", parent=body, fontName="Helvetica-Bold",
                          fontSize=8, textColor=BRASS, leading=10)

PAGE_METADATA = {
    # Public
    "01_public_landing":        ("Public landing page", "public", "The marketing home visitors see at pmcmanagers.com. The hero links straight through to the live tender board, the registration flow and both role sign-ins.", "public"),
    "02_public_tender_board":   ("Public tender board", "public", "Open tender listing — anyone can filter by sector, deadline, EMD band or region. Clicking a tile opens the public notice detail, with 'Register & bid' pulling the user into onboarding.", "public"),
    "03_registration_start":    ("Vendor registration — start", "public", "New supplier onboarding. All fields are KYC-validated client-side; the form posts to /api/v1/registrations which admins review in the Registrations panel.", "public"),
    "04_unified_login":         ("Unified sign-in", "public", "The single sign-in gate for suppliers and staff. The role chip chooses the right dashboard after auth. Admin, staff and vendor each have a reset-password flow served from here.", "public"),
    "05_admin_login":           ("Admin sign-in", "admin", "Dedicated admin login route. Returns an admin bearer token + CSRF token and gates every /api/v1/admin/* endpoint behind BOTH.", "public"),
    # Admin
    "10_admin_dashboard":       ("Admin dashboard", "admin", "The daily working view. Top KPIs: pending registrations, bids due today, EMD held, awards awaiting signature. 'Create' spawns new notices, tenders, meetings and events; the bell lists system alerts.", "admin"),
    "11_admin_vendors":         ("Vendors panel", "admin", "Live supplier directory with status filters (active / inactive / suspended / rejected). Tapping a vendor opens the KPI + KYC detail inline on mobile, or in the right column on desktop. Bulk-invite and Add & fill forms sit above the list.", "admin"),
    "12_admin_registrations":   ("Registrations review", "admin", "Submitted / Approved / Clarify / Rejected tabs for incoming registrations. Mobile taps the row to open the review panel inline (approve / clarify / reject + notes). Reminders can be sent to stale submissions in one click.", "admin"),
    "13_admin_notices":         ("Notices", "admin", "Standalone notices (independent of a tender) — public bulletins, corrigenda-less announcements, policy updates. Each row has reach + reads counters so comms can see what landed.", "admin"),
    "14_admin_tender_builder":  ("Tender builder", "admin", "The multi-step wizard: header → covers → BOQ → clauses → preview → publish. Covers are versioned (1,2,3…), DPR extraction fills covers from PDFs, and 'AI draft' seeds clauses from the template library.", "admin"),
    "15_admin_corrigenda":      ("Corrigenda", "admin", "Issue amendments to live tenders. Each corrigendum goes out as its own email + website banner and re-opens the clock when needed.", "admin"),
    "16_admin_boq":             ("BOQ library", "admin", "Reusable Bill of Quantities items — line items with units, codes and ceiling rates. Attach a BOQ to any tender from the builder; vendors see rate columns tied to these items.", "admin"),
    "17_admin_work_packages":   ("Work packages", "admin", "Group of related tenders under a single master programme — useful for multi-package construction or framework procurement.", "admin"),
    "18_admin_catalog":         ("Procurement catalogue", "admin", "Searchable catalogue of standard goods and services. Driven by the Categories master; vendors self-select from here when registering.", "admin"),
    "19_admin_vendor_intel":    ("Vendor intel", "admin", "Risk and performance signals per vendor — past wins, award value, average turnaround, anomaly scores from the AI outlier detector.", "admin"),
    "20_admin_engagements":     ("Engagements", "admin", "Vendor engagements tracker — pre-bid meetings, site visits, clarification windows. Each row logs who attended + when, with reminders out to assigned staff.", "admin"),
    "21_admin_bidding_ops":     ("Bidding operations", "admin", "The daily bid-clearance desk. Tabs: Needs PMC / Waiting on supplier / Awarded / All. Counts always match the rows actually shown. Row cards expose EMD state, next step and the flow pipeline.", "admin"),
    "22_admin_escrow":          ("Escrow", "admin", "EMD held by the designated escrow agent — hold / release / forfeit per bid, with the escrow-agent role scoped to this panel.", "admin"),
    "23_admin_billing":         ("Billing", "admin", "PMC's own invoicing — platform access fees, bid-success surcharge, Stripe reconciliation and refunds.", "admin"),
    "24_admin_evaluation":      ("Evaluation", "admin", "Score bids against the published evaluation matrix. Technical / commercial weights come from the tender header; the committee signs off scores from here.", "admin"),
    "25_admin_l1":              ("L1 shortlist", "admin", "Lowest-evaluated-bid shortlist after technical qualification. Ties are highlighted and the committee's L1 pick flows into Awards.", "admin"),
    "26_admin_awards":          ("Awards & LOI", "admin", "Issue Letter of Intent / Award. Pulls selected vendor + bid total, generates the award PDF, routes it to DocuSign and tracks acceptance.", "admin"),
    "27_admin_docusign":        ("DocuSign operations", "admin", "Admin view of every envelope: Draft / Sent / Delivered / Signed / Declined / Archived. Reassign, download the combined signed PDF, resend reminders. Preview DocuSign sandbox may return 424 upstream; production uses real credentials.", "admin"),
    "28_admin_permissions":     ("Roles & permissions", "admin", "Role → permission matrix for every staff seed. New role? Define its scope here and it flows through to all admin panels on next sign-in.", "admin"),
    "29_admin_events":          ("Events & alerts", "admin", "System-wide events feed: deadlines approaching, EMDs expiring, KYC due. Admins pin or acknowledge events; vendors see their slice on the alerts tab.", "admin"),
    "30_admin_masters":         ("Masters", "admin", "Reference-data home. 13 chips (visible all at once on mobile): Staff, Companies, Tenants, Approval matrix, Hierarchy, Rating & Fees, Charge Fee, Categories, Legal entity types, Vendor requests, Profile changes, EMD rules, Investor demo. Active chip is solid navy.", "admin"),
    "31_admin_audit":           ("Audit ledger", "admin", "Immutable action trail — every admin + vendor action with actor, IP, user agent and before/after diffs. Export CSV for compliance reviews.", "admin"),
    # Vendor
    "50_vendor_home":           ("Supplier home", "vendor", "Supplier dashboard with next action tiles: KYC / Bids due / Awards to accept / Unread alerts. The mobile bottom tab-bar carries Home · Tenders · My Bids · Sign · Account.", "vendor"),
    "51_vendor_tenders":        ("Find tenders", "vendor", "Supplier-side live tender list with the same filters as the public board — plus personalized sort (category match, past-win proximity). 'Start bid' from any row opens the bid workspace.", "vendor"),
    "52_vendor_mybids":         ("My Bids", "vendor", "Supplier's bid pipeline — drafts, submitted, awarded, declined. Each row carries EMD status and the next step the supplier owes.", "vendor"),
    "53_vendor_signatures":     ("Signatures (DocuSign)", "vendor", "Supplier-side DocuSign tray. Open an envelope, sign in-portal, download the signed PDF. The dot on the Sign icon in the bottom bar flags pending envelopes.", "vendor"),
    "54_vendor_company_kyc":    ("Company & KYC", "vendor", "Supplier's company profile — licences, incorporation docs, operating regions. Add a licence from here; the Cancel button no longer crashes (v51u scrim-scrub fix).", "vendor"),
    "55_vendor_account":        ("Account & security", "vendor", "Password + session controls + change requests. Change company name attaches the incorporation certificate (required). Change mobile sends a confirmation link to the current email before admin can approve.", "vendor"),
    "56_vendor_alerts":         ("Alerts", "vendor", "Supplier's inbox for system events — tender awards, DocuSign ready-to-sign, EMD refund processed, profile change decisions.", "vendor"),
    # Mobile
    "70_mobile_vendor_home":    ("Mobile — Supplier home", "mobile", "iPhone-width view of the supplier dashboard. 5-icon bottom tab bar (Home · Tenders · My Bids · Sign · Account) is pinned above the OS home indicator.", "mobile"),
    "71_mobile_vendor_mybids":  ("Mobile — My Bids", "mobile", "iPhone-width view of the bid pipeline. Row cards stack vertically; tapping the pay button on an EMD-due bid no longer gets hidden by the tab bar (v51r pb-40 fix).", "mobile"),
    "72_mobile_admin_bidding":  ("Mobile — Bidding operations", "mobile", "iPhone-width Bidding Ops. Tabs wrap to two rows and the count badges match the rows actually visible (v51o fix).", "mobile"),
    "73_mobile_admin_vendors":  ("Mobile — Admin Vendors", "mobile", "iPhone-width Admin Vendors. Toolbar wraps 2-up, tapping a vendor opens KPI + KYC detail inline directly below the row.", "mobile"),
}

def fit_image(img_path: Path, max_w: float, max_h: float):
    with PILImage.open(img_path) as im:
        iw, ih = im.size
    ratio = min(max_w / iw, max_h / ih)
    return iw * ratio, ih * ratio


def chapter_title(section_key: str) -> str:
    return {
        "public": "Chapter 1 — Public & onboarding",
        "admin":  "Chapter 2 — Admin console",
        "vendor": "Chapter 3 — Supplier portal",
        "mobile": "Chapter 4 — Mobile experience",
    }.get(section_key, "")


def main():
    doc = SimpleDocTemplate(str(OUT), pagesize=A4,
                             leftMargin=16*mm, rightMargin=16*mm,
                             topMargin=16*mm, bottomMargin=16*mm,
                             title="PMC Master Training Manual v6",
                             author="PMC Managers")
    story = []

    # Cover
    story.append(Spacer(1, 60*mm))
    story.append(Paragraph("PMC Managers v2", title_s))
    story.append(Paragraph("Master Training Manual", title_s))
    story.append(Spacer(1, 6*mm))
    story.append(Paragraph("Version 6 — regenerated 05 Oct 2026 from the live v51u build", sub_s))
    story.append(Spacer(1, 100*mm))
    story.append(Paragraph("Audience: PMC admins, trainers and onboarding leads. Every screenshot is from the current green / navy forest theme (Option E).", body))
    story.append(PageBreak())

    # Table of contents
    story.append(Paragraph("Contents", h1))
    chapters_seen = set()
    for stem in sorted(PAGE_METADATA.keys()):
        meta = PAGE_METADATA[stem]
        label, section = meta[0], meta[3]
        if section not in chapters_seen:
            chapters_seen.add(section)
            story.append(Paragraph(chapter_title(section), h2))
        story.append(Paragraph("• " + label, body))
    story.append(PageBreak())

    # Chapters
    last_section = None
    max_w = (A4[0] - 32*mm)
    max_h = (A4[1] - 32*mm) * 0.52  # leave room for caption + heading
    for stem in sorted(PAGE_METADATA.keys()):
        png = SHOTS / f"{stem}.png"
        if not png.exists():
            continue
        label, _, caption, section = PAGE_METADATA[stem]
        if section != last_section:
            story.append(PageBreak())
            story.append(Paragraph(chapter_title(section), h1))
            last_section = section
        story.append(Spacer(1, 4))
        story.append(Paragraph(label, h2))
        story.append(Paragraph(caption, body))
        try:
            w, h = fit_image(png, max_w, max_h)
            story.append(RLImage(str(png), width=w, height=h))
        except Exception as e:
            story.append(Paragraph(f"[screenshot unavailable: {e}]", cap))
        story.append(Paragraph(f"Figure: {label} · screenshot captured 05 Oct 2026 from the v51u build.", cap))

    doc.build(story)
    print(f"Built {OUT} ({OUT.stat().st_size // 1024} KB)")


if __name__ == "__main__":
    main()
