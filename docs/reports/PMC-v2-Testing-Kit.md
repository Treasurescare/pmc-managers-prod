# PMC Managers v2 — Comprehensive Testing Kit

Hand this file to any QA engineer (human or AI) and they can drive the entire investor demo end-to-end.

## Environment

- **Production URL**: https://d2h9tkca2zjofy.cloudfront.net (Chapter 6 pending: `www.pmcmanagers.com`)
- **API base**: `https://d2h9tkca2zjofy.cloudfront.net/api/v1`
- **Health**: `GET /api/v1/meta/health` → `{"ok":true,"service":"pmc-tender-v2-api","phase":"pilot"}`

## Credentials

| Persona | Email | Password | Route |
|---|---|---|---|
| Master Admin | `adminsupport@pmcmanagers.com` | `Admin@123` | `/admin/login` |
| Owner (real inbox) | `kannan@emeraldcorporates.com` | `Owner@123` | `/admin/login` |
| Escrow agent | `escrow@pmcmanagers.com` | `Escrow@123` | `/staff/login` (role: escrow_agent) |
| Certifier | `certifier@pmcmanagers.com` | `Certify@123` | `/staff/login` (role: certifier) |
| Legal counsel | `legal@pmcmanagers.com` | `Legal@123` | `/staff/login` (role: legal_counsel) |
| Accounting | `accounts@pmcmanagers.com` | `Accts@123` | `/staff/login` (role: accounting) |
| Committee chair | `committee@pmcmanagers.com` | `Bid@1234` | `/staff/login` (role: committee_member) |
| Vendor | self-register at `/register` | (chosen at verify) | `/vendor/login` |

⚠️ **Rotate `Admin@123` before investor demo.**

## Payment sandbox

- **Stripe**: card `4242 4242 4242 4242` · any future expiry · any CVC
- **PayPal**: in-app demo checkout (no real PayPal creds)
- **Kaspi Pay**: in-app demo checkout (no real Kaspi creds)

## Reference documents (all downloadable through the admin console)

| Doc | URL (admin-only) |
|---|---|
| Asked vs Delivered — PDF | `/api/v1/reports/comparative-statement.pdf` |
| Asked vs Delivered — DOCX | `/api/v1/reports/comparative-statement.docx` |
| Asked vs Delivered — XLSX | `/api/v1/reports/comparative-statement.xlsx` |
| Platform architecture flowchart — SVG | `/api/v1/reports/flowchart.svg` |
| Platform architecture flowchart — PDF (A3 landscape) | `/api/v1/reports/flowchart.pdf` |
| User-journey flowchart — SVG | `/api/v1/reports/user-guide.svg` |
| User-journey flowchart — PDF (A3 portrait) | `/api/v1/reports/user-guide.pdf` |
| **QA Testing flowchart — SVG (NEW)** | `/api/v1/reports/testing-flowchart.svg` |
| **QA Testing flowchart — PDF (A2 portrait) (NEW)** | `/api/v1/reports/testing-flowchart.pdf` |
| Test-Plan doc — MD | `/api/v1/reports/test-plan.md` |
| Test-Plan doc — PDF | `/api/v1/reports/test-plan.pdf` |
| Test-ID registry (data-testid catalog) | `/api/v1/reports/test-ids.txt` |

To regenerate all snapshot artefacts at once: `POST /api/v1/reports/snapshot` (admin auth).

## The 55 test scenarios (see the Testing Flowchart)

Print the testing flowchart PDF (A2 portrait), tape it on a wall, and run each numbered box top-to-bottom, left-to-right. Every box maps to a `data-testid` attribute. Report failures with the box number + browser dev-tools screenshot.

### Phase 1 — Landing & discovery (Public)
1. Notice Board loads at `/` — 3-col grid renders `notice-card-{ref}` tiles
2. Notice search + filter — keyword, org, status, deadline dropdowns
3. Notice detail + docs — attachments download, corrigenda banner visible if any
4. Q&A public thread — vendor question → admin answer visible
5. Public roadmap — `/roadmap` renders status pills for all 20 areas

### Phase 2 — Registration & onboarding (Vendor)
6. Register Sections A–E — vendor self-registration, uploads (each section validates before Next)
7. Email verification — click link, land on `/vendor/verify/{token}`, set password
8. Login + MFA setup — `/vendor/login`, scan TOTP QR
9. Update profile + GDPR export — download data JSON

### Phase 3 — Tender publication & Q&A (Admin)
23. Publish tender via Tender Template Builder — 8-section wizard
24. Publish corrigendum — auto-numbered, deadline auto-update on parent notice
25. Answer Q&A — admin reply makes vendor thread visible to public

### Phase 4 — Bidding + EMD payment (Vendor + Admin)
10. Submit bid + line items — `/vendor/bid/new/:noticeRef`
11. Pay EMD via Stripe — test card 4242 4242 4242 4242
12. Pay EMD sandbox (PayPal / Kaspi) — in-app demo checkout
13. Two-cover envelope — technical envelope opens first
26. Admin opens financial envelope after technical shortlist
27. L1 comparison table auto-ranks by amount

### Phase 5 — Evaluation & committee (Admin + Committee)
28. Setup evaluation rubric — criteria + weights
29. Nominate committee — internal + external members
30. Assign certifier for site inspection
45. Committee accept invite via `/committee/accept/:token`
46. Committee scores bid on rubric — per-criterion 0-10
47. Bid pack rendering — line items, docs, vendor intel loads for scorer

### Phase 6 — Award & post-award docs (Admin + Vendor)
31. Award bid — auto-generate PO, SLA, Contract PDFs
32. Send DocuSign envelope — pick delivery `embedded` vs `email`
33. Envelope status live-updates via webhook
17. Vendor signs contract (embedded delivery, in-app iframe)
18. Vendor downloads signed PDF from `/mine/envelopes/{id}/combined-pdf`

### Phase 7 — Reverse auctions + meetings (Admin + Vendor)
34. Admin starts reverse auction — min-decrement, anti-snipe extends on last-second bids
14. Vendor joins auction at `/vendor/auction/:aid`
15. Vendor enables auto-bid rule — floor + decrement
35. Admin schedules meeting — Zoom S2S OAuth or Jitsi
16. Vendor joins meeting via `/meet/:token` public link

### Phase 8 — Escrow release + audit (Staff + Admin)
38. Escrow agent accepts EMD (payment reconciled)
39. Certifier files site inspection with checklist + photos
40. Certifier verifies vendor documents
41. Legal counsel MFA-gated KYC clearance
42. Accounting MFA-gated financial sign-off
43. Escrow releases funds (vendor bank details verified)
44. Escrow officer public magic-link portal `/escrow/officer/:token`
36. Admin runs Audit Copilot query
37. Admin exports ledger + all comparative reports

### Cross-cutting
20. Admin dashboard KPIs (notices / bids / vendors counters)
21. Approve vendor registration
22. Bulk invite vendors via CSV upload
48. Notifications bell — role-scoped, live poll
49. Impersonate role dropdown for support flow
50. Add tenant `?tenant=DEMO-CORP` — brand colours flip
51. Mobile responsive audit — 375px, 768px, 1024px
52. i18n switch EN/RU/KK — all admin panels render
53. Regen SoT docs — `POST /api/v1/reports/snapshot`
54. Test-plan endpoint download
55. Test-IDs registry download

## Smoke test (5-minute investor demo boot check)

Run these 5 curls in order. All should return 200:

```bash
BASE=https://d2h9tkca2zjofy.cloudfront.net

# 1. Health
curl -f $BASE/api/v1/meta/health

# 2. Public notices
curl -f $BASE/api/v1/notices/public | head -c 400

# 3. Public roadmap JSON
curl -f $BASE/api/v1/reports/public/roadmap | head -c 400

# 4. Admin login (should return 200 + a JWT)
curl -f -X POST $BASE/api/v1/admin/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"adminsupport@pmcmanagers.com","password":"Admin@123"}'

# 5. Frontend HTML
curl -f $BASE | head -c 400
```

If all 5 return 200, production is healthy. Move on to browser-based scenario testing.

## Known ⚠️ current constraints

- `STRIPE_API_KEY` = `sk_test_emergent` (placeholder — real Stripe checkout will 401; UI still renders)
- `LLM_API_KEY` is valid — Audit Copilot works
- PayPal / Kaspi Pay are mocked sandbox — no real merchant creds
- Firebase / APNs push not configured
- Live KYC provider not connected — falls back to deterministic stub
- Resend email delivery mocked — emails logged, not sent

## Reporting failures

For each failed test box, capture:
1. **Step number** (from testing flowchart)
2. **User account used** (email + role)
3. **Browser + OS**
4. **Screenshot** with dev-tools Network tab visible
5. **cURL repro** if possible (right-click network row → Copy → Copy as cURL)

Post to the ops channel or file an issue on the fresh production repo.
