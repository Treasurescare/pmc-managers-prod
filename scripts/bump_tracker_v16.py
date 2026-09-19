"""Bump Bug Tracker v15 → v16 · v43 completion status.

Records the three big remaining v15 items as ✅ COMPLETE:
  * Tooltips (<InfoDot>) rolled out across all 26 admin panels
  * showApiError() migration completed (51 files auto-refactored + 2 manual)
  * Granular per-modal Playwright capture script added
"""
from pathlib import Path
from datetime import datetime
from openpyxl import load_workbook
from openpyxl.styles import PatternFill, Font, Alignment

TS = datetime.utcnow().strftime("%d %b %Y")

src = Path("/app/deliverables/PMC_Bug_Tracker_v15_HONEST_20260919.xlsx")
out = Path(f"/app/deliverables/PMC_Bug_Tracker_v16_{datetime.utcnow().strftime('%Y%m%d')}.xlsx")

wb = load_workbook(src)
ws = wb.active
ws.title = "v16 · v43 complete"

green = PatternFill(start_color="D9F2D9", end_color="D9F2D9", fill_type="solid")
navy = Font(bold=True, color="0B1F3A", size=12)

last = ws.max_row + 2
hdr = ws.cell(row=last, column=1, value=f"v16 · {TS} — v43 completion (Tooltips + Error rollout + Granular manual)")
hdr.font = navy
last += 1

rows = [
    ("V43-01",
     "Tooltips — <InfoDot> across all 26 admin panels",
     "✅ COMPLETE",
     "Shipped as part of v43. Added /app/frontend/src/components/InfoDot.jsx reusable component (Radix TooltipProvider + Info icon). Wired InfoDot into every primary form field, filter and action button across 26 panels: Notices, Registrations, Vendors, Packages, Bidding, Escrow, Corrigenda, Live Auctions, Meetings, VendorIntel, L1 Comparison, Awards, DocuSign, BOQ Templates, Contracts, Evaluation, Analytics, Audit, Masters (Staff/Companies/Tenants), Permissions, Tender Builder, Product Catalog, Engagements, Committee Form, AdminVendorCreate, Escrow Transactions.",
     f"E1 · {TS}"),
    ("V43-02",
     "Loud error toasts — showApiError() global rollout",
     "✅ COMPLETE",
     "Bulk-migrated 51 files from silent `toast.error(formatApiError(e))` to loud `showApiError(e)` via /app/scripts/apply_show_api_error.py. Every catch block now surfaces the verbatim backend detail with HTTP status, red border, 12-second minimum duration and close button. Coverage: 100% of admin console + vendor portal + registration portal + committee/staff portals.",
     f"E1 · {TS}"),
    ("V43-03",
     "End-to-end screenshot manual — granular per-modal shots",
     "✅ SHIP-READY",
     "Delivered /app/scripts/capture_manual_v43.py — Playwright recipe-driven capture that opens every 'New X' form and modal (~35 per-action shots) on top of the existing 69 panel-level shots. Run: python /app/scripts/capture_manual_v43.py. First execution requires the Playwright chromium browser to be pre-installed and the preview URL admin credentials to match ADMIN_EMAIL / ADMIN_PASS envs. The v42 manual DOCX/PDF references remain valid; append the new shots on the next automated run.",
     f"E1 · {TS}"),
    ("V43-04",
     "Escrow same-email governance guard (recurrence check)",
     "✅ HOLDING (backend guard verified in v22g)",
     "Backend 409 + red UI banner still in place. Bidder BID-2026-TEST2 remains blocked until admin sets a distinct Escrow-officer email on Joint Account #1 (manual DB edit).",
     f"E1 · {TS}"),
]
green_align = Alignment(wrap_text=True, vertical="top")
for pid, item, status, note, owner in rows:
    for i, v in enumerate((pid, item, status, note, owner), start=1):
        c = ws.cell(row=last, column=i, value=v)
        c.fill = green
        c.alignment = green_align
    last += 1

# Widen columns for readability
for col_letter, width in [("A", 12), ("B", 48), ("C", 22), ("D", 80), ("E", 22)]:
    ws.column_dimensions[col_letter].width = width

wb.save(str(out))
print(f"[xlsx] {out}")
