#!/usr/bin/env python3
"""Bulk-add live-data hook imports + calls to each remaining Option-E page."""
import re
from pathlib import Path

APP = Path("/app/frontend/src/apps")

# (file, hookName, needsBidIdParam)
WIRING = [
    ("vendor-portal-e/VendorFindTendersE.jsx", "useVendorFindTendersLive", False),
    ("vendor-portal-e/VendorEmdE.jsx",         "useVendorEmdLive",         False),
    ("vendor-portal-e/VendorSignaturesE.jsx",  "useVendorSignaturesLive",  False),
    ("vendor-portal-e/VendorAccountE.jsx",     "useVendorAccountLive",     False),
    ("vendor-portal-e/VendorAlertsE.jsx",      "useVendorAlertsLive",      False),
    ("vendor-portal-e/VendorReviewsE.jsx",     "useVendorReviewsLive",     False),
    ("vendor-portal-e/VendorBidWorkspaceE.jsx","useVendorBidWorkspaceLive",True),
    ("admin-console-e/AdminProgrammeE.jsx",    "useAdminProgrammeLive",    False),
    ("admin-console-e/AdminAuditE.jsx",        "useAdminAuditLive",        False),
    ("admin-console-e/AdminCorrigendaE.jsx",   "useAdminCorrigendaLive",   False),
    ("admin-console-e/AdminWorkPackagesE.jsx", "useAdminWorkPackagesLive", False),
    ("admin-console-e/AdminCatalogE.jsx",      "useAdminCatalogLive",      False),
    ("admin-console-e/AdminRegistrationsE.jsx","useAdminRegistrationsLive",False),
    ("admin-console-e/AdminVendorKycE.jsx",    "useAdminVendorKycLive",    False),
    ("admin-console-e/AdminVendorIntelE.jsx",  "useAdminVendorIntelLive",  False),
    ("admin-console-e/AdminBiddingOpsE.jsx",   "useAdminBiddingOpsLive",   False),
    ("admin-console-e/AdminEscrowE.jsx",       "useAdminEscrowLive",       False),
    ("admin-console-e/AdminBillingE.jsx",      "useAdminBillingLive",      False),
    ("admin-console-e/AdminEvaluationListE.jsx","useAdminEvaluationsLive", False),
    ("admin-console-e/AdminEvaluationE.jsx",   "useAdminEvaluationsLive",  False),
    ("admin-console-e/AdminAwardsE.jsx",       "useAdminAwardsLive",       False),
    ("admin-console-e/AdminL1AwardE.jsx",      "useAdminAwardsLive",       False),
    ("admin-console-e/AdminDocuSignE.jsx",     "useAdminDocuSignLive",     False),
    ("admin-console-e/AdminEventsE.jsx",       "useAdminEventsLive",       False),
    ("admin-console-e/AdminEngagementsE.jsx",  "useAdminEngagementsLive",  False),
    ("admin-console-e/AdminTenderBuilderE.jsx","useAdminTenderBuilderLive",False),
    ("admin-console-e/AdminBoqContractsE.jsx", "useAdminBoqLive",          False),
    ("admin-console-e/AdminPermissionsE.jsx",  "useAdminPermissionsLive",  False),
]

fixed = 0
for rel, hook, needs_bid in WIRING:
    p = APP / rel
    if not p.exists():
        print("skip (missing):", rel)
        continue
    src = p.read_text()
    if hook in src:
        continue
    # Insert import line right after `useUiTheme` import
    new_src = src.replace(
        'import { useUiTheme } from "@/context/UiThemeContext";',
        f'import {{ useUiTheme }} from "@/context/UiThemeContext";\n'
        f'import {{ {hook} }} from "@/lib/pmcELiveData";',
        1,
    )
    # Insert hook call right after `const { isE } = useUiTheme();`
    if needs_bid:
        param = '{ enabled: isE, bidId: (window.location.pathname.split("/").pop() || "") }'
    else:
        param = '{ enabled: isE }'
    new_src = new_src.replace(
        'const { isE } = useUiTheme();',
        f'const {{ isE }} = useUiTheme();\n  {hook}({param});',
        1,
    )
    if new_src == src:
        print("no anchor found:", rel)
        continue
    p.write_text(new_src)
    fixed += 1
    print(f"  wired: {rel} -> {hook}")
print(f"\nTotal wired: {fixed}")
