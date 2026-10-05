"""Stage current-theme screenshots under the legacy filenames the v7 manual
builder references. New shots from manual_v51u_shots are copied in;
pass-2 extras already land here with legacy names. Any legacy filename
without a fresh equivalent falls back to the old shot (logged loudly).
"""
from pathlib import Path
import shutil

NEW = Path("/app/deliverables/manual_v51u_shots")
STAGE = Path("/app/deliverables/manual_v7_screenshots")
STAGE.mkdir(parents=True, exist_ok=True)

# legacy filename -> pass-1 shot
MAP = {
    "01_public-landing-page.png":             "01_public_landing.png",
    "02_public-tender-board.png":             "02_public_tender_board.png",
    "03_vendor-registration-—-start.png":     "03_registration_start.png",
    # 04 (check-status) captured in pass 2 directly
    "05_admin-login-page.png":                "05_admin_login.png",
    "06_analytics.png":                       "10_admin_dashboard.png",
    "07_registrations.png":                   "12_admin_registrations.png",
    "08_vendors.png":                         "11_admin_vendors.png",
    "09_notices.png":                         "13_admin_notices.png",
    "10_corrigenda.png":                      "15_admin_corrigenda.png",
    "11_tender-builder.png":                  "14_admin_tender_builder.png",
    "12_bidding.png":                         "21_admin_bidding_ops.png",
    # 13_auctions captured in pass 2
    "14_escrow.png":                          "22_admin_escrow.png",
    "15_evaluation.png":                      "24_admin_evaluation.png",
    "16_awards.png":                          "26_admin_awards.png",
    "17_boq.png":                             "16_admin_boq.png",
    "18_meetings.png":                        "20_admin_engagements.png",
    # 19_l1 captured in pass 2
    "20_docusign.png":                        "27_admin_docusign.png",
    "21_vendor-intel.png":                    "19_admin_vendor_intel.png",
    "22_products.png":                        "18_admin_catalog.png",
    "23_engagements.png":                     "20_admin_engagements.png",
    "24_masters.png":                         "30_admin_masters.png",
    "25_permissions.png":                     "28_admin_permissions.png",
    "26_audit.png":                           "31_admin_audit.png",
    # 27/28/30 captured in pass 2
    "29_help.png":                            "35x_admin_help.png",
}

for legacy, fresh in MAP.items():
    src = NEW / fresh
    if not src.exists():
        src = STAGE / fresh  # pass-2 shots already staged under these names
    dst = STAGE / legacy
    if src.exists():
        shutil.copy2(src, dst)
        print(f"  ✓ {legacy}  <- {src.name}")
    else:
        print(f"  ! MISSING fresh shot for {legacy}")

# Vendor chapter shots referenced by v2 builder (legacy vendor filenames)
VENDOR_MAP = {
    "30_vendor_landing.png":   "50_vendor_home.png",
    "31_vendor_tenders.png":   "51_vendor_tenders.png",
    "32_vendor_bids.png":      "52_vendor_mybids.png",
    "33_vendor_rate.png":      "37x_vendor_emd.png",
    "34_vendor_signatures.png":"53_vendor_signatures.png",
}
for legacy, fresh in VENDOR_MAP.items():
    src = NEW / fresh
    if not src.exists():
        src = STAGE / fresh
    dst = STAGE / legacy
    if src.exists():
        shutil.copy2(src, dst)
        print(f"  ✓ {legacy}  <- {src.name}")
    else:
        print(f"  ! MISSING fresh shot for {legacy}")

print(f"\nStaged {len(list(STAGE.glob('*.png')))} screenshots in {STAGE}")
