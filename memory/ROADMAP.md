# PMC Managers v2 — Roadmap (as of 2026-09-19)

## ✅ Just cleared (Batch #9 — v37/v22e, awaiting AWS push)
- #76 P0, #15/#28/#29/#49/#52/#63/#84 P1, #20/#21/#30/#46 P2 — all verified in preview

## 🔵 P2 · Optional DNS safeguard
- Route 53 SOA min-TTL: 86400s → 60s (prevents 24h negative caching for future misconfigurations)

## 🟡 P2 · Translations backlog (partially closed with Batch #9)
- Master Training Manual — Turkish translation
- Master Training Manual — Russian translation
- Master Training Manual — Kazakh translation
- Additional admin panels still with hardcoded English strings: BOQContractsPanel, EscrowPanel, PackagesPanel, AwardsPanel, LiveAuctionsPanel, MeetingsPanel, L1ComparisonPanel, DocuSignPanel, EngagementsPanel, PermissionsPanel, ProductCatalogPanel, TenderBuilderPanel (VendorsPanel + RegistrationsPanel + NoticesPanel + AnalyticsPanel + Masters + VendorIntel + Evaluation already covered)

## 🟢 P2 · Integrations awaiting live keys
- Firebase Cloud Messaging + APNs push notifications setup (dev only)
- KYC live provider integration (currently mocked)
- PayPal live integration (currently mocked)
- Kaspi Pay live integration (currently mocked)

## 🟡 P1 · Languages (2026-11-06)
- Finish localized help videos (550 remaining) after LLM key top-up: PMC_BASE=... PMC_ADMIN_EMAIL/PW PMC_VENDOR_EMAIL/PW python3 scripts/help_videos/make_videos.py --lang=<l>; then re-run scripts/build_manual_i18n.py (cached) and rebuild
- Deploy v60h and submit sitemap in Google Search Console
- Native-speaker review of all 13 languages via Translation review screen
- Translation rate limit uses spoofable X-Forwarded-For (global daily cap 30k in place)
- Sentence fragments split by links/<em> translate awkwardly (e.g. About hero); consider whole-sentence translation

## 🟣 Future / Backlog
- Multi-tenant portal template gallery expansion
- Phase-2 vendor KPI: bid win-rate, avg turnaround, packages awarded (needs AWS + PostgreSQL migration per placeholder in `/api/v1/vendors/{ref}/kpi`)
- Advanced Vendor Intel: sanctions-list webhook feed
- AI Audit Copilot: cross-tender anomaly detection (batch mode)
