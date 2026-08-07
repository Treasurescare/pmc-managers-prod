# PMC Managers v2 · End-to-End Test Plan

**Version:** Wave 43 (2026-08-07) · DocuSign live, trilingual sweep, mobile responsive complete
**Preview:** https://tender-hub-57.preview.emergentagent.com
**Production:** https://tender-hub-57.emergent.host

Hand this file to a human tester or feed it directly to an AI testing agent (Playwright, Cypress, Testim, QA.tech, MagicTest, BrowserStack Test-O). Every test case names a **data-testid** wherever one exists so selectors are stable.

---

## 0 · Environments & Credentials

| Portal | URL | Login | Password |
|---|---|---|---|
| Public Notice Board | `/` | — | — |
| Public Roadmap | `/roadmap` | — | — |
| Unified Web Login (auto-detect) | `/login` | any of the below | see below |
| Mobile Unified Login | `/m` | any of the below | see below |
| Admin Console | `/admin/login` | `adminsupport@pmcmanagers.com` | `Admin@123` |
| Owner (real inbox) | `/admin/login` | `kannan@emeraldcorporates.com` | `Owner@123` |
| Staff — Escrow Agent | `/staff/login` (role dropdown) | `escrow@pmcmanagers.com` | `Escrow@123` |
| Staff — Site Certifier | `/staff/login` | `certifier@pmcmanagers.com` | `Certify@123` |
| Staff — Legal Counsel | `/staff/login` | `legal@pmcmanagers.com` | `Legal@123` |
| Staff — Accounting | `/staff/login` | `accounts@pmcmanagers.com` | `Accts@123` |
| Staff — Committee Chair | `/staff/login` | `committee@pmcmanagers.com` | `Bid@1234` |
| Vendor | `/vendor/login` | Self-register or admin-invited | — |

**Test payment cards (Stripe test mode):**
- Success: `4242 4242 4242 4242` · any future expiry · any 3-digit CVC
- Decline: `4000 0000 0000 0002`
- 3-D Secure: `4000 0027 6000 3184`

---

## 1 · Smoke Suite (run first — 5 min)

| # | Test | Expected | Selector / URL |
|---|---|---|---|
| 1.1 | GET `/` at 1440px + 375px | Renders hero + stat cards + notices list, zero horizontal scroll on 375 | `data-testid="stat-*"` |
| 1.2 | Language switcher → RU → KK → EN | UI copy swaps for every top-nav link, stat labels, footer | `data-testid="lang-toggle"` |
| 1.3 | POST `/api/v1/meta/health` | HTTP 200 + `{status: "ok", db: "up"}` | curl |
| 1.4 | Admin login with correct creds | 302 → `/admin`, `session` + `csrf_token` cookies set (HttpOnly, SameSite=Lax) | `data-testid="admin-login-submit"` |
| 1.5 | Admin login with wrong password × 6 | 6th attempt returns 429 (brute-force lockout) | curl |
| 1.6 | Admin dashboard @ 375px | Tab bar becomes `<select>`; email panel hidden; every function reachable | `data-testid="admin-tabs-select"` |
| 1.7 | GET `/api/v1/docusign/status` | Returns `configured:true, consent_ok:true, env:"sandbox"` | curl |

---

## 2 · Auth & RBAC

| # | Test | Steps | Expected |
|---|---|---|---|
| 2.1 | Admin session cookie tamper | Login → modify `session` cookie one byte → reload `/admin` | 302 → `/admin/login` |
| 2.2 | CSRF double-submit | POST to any state-changing endpoint without `X-CSRF-Token` header | HTTP 403 `CSRF token missing` |
| 2.3 | CSRF token mismatch | POST with random `X-CSRF-Token` value | HTTP 403 |
| 2.4 | Role escalation attempt | Login as `escrow_agent` → curl POST `/api/v1/notices` (admin-only) | HTTP 403 role denied |
| 2.5 | JWT decode leak | Copy `session` cookie → decode with `jwt.io` | Should have short TTL (24h max), no PII beyond email + roles |
| 2.6 | Vendor cannot see admin routes | Vendor login → GET `/api/v1/admin/*` | HTTP 401/403 on each |
| 2.7 | MFA enrollment | Admin → Security · 2FA → Start setup → scan QR → verify 6-digit → save recovery codes | 10 recovery codes shown once, MFA enabled |
| 2.8 | MFA login enforcement | Log out → log back in on an MFA-enabled account | 6-digit prompt appears; skip 5×, account locks |
| 2.9 | Recovery-code login | Log out → log in with a recovery code | Works; that code is invalidated |
| 2.10 | Multi-role hierarchy | Login as `committee@pmcmanagers.com` (has `committee_member, admin`) | Sees full admin console |
| 2.11 | Magic-link resume (vendor) | Start registration → close browser → open magic link | Draft resumes at correct step |
| 2.12 | Admin-invited vendor onboarding | Admin → Vendors → **Invite** → check email → click link → set password | Vendor lands logged-in |

**Hacks to try:**
- Session-fixation: pre-set `session` cookie before login → confirm server issues a NEW one on login success
- Password reuse: try creating a staff account with the same email as a vendor → should be rejected
- SQL/NoSQL injection: try `admin' or 1==1//` in login form → generic 401
- User enumeration: forgot-password on `random@example.com` vs `adminsupport@pmcmanagers.com` → responses **must be identical** (both should say "if account exists, email sent")

---

## 3 · Vendor Registration (Sections A–E)

| # | Test | Steps | Expected |
|---|---|---|---|
| 3.1 | Section A → E flow | Fill all 5 sections at `/register`, upload PDF for each doc slot | Submits, admin sees pending vendor |
| 3.2 | Draft auto-save | Fill Section A → refresh page | Data restored from server |
| 3.3 | Doc slot silent-draft | Admin `/admin/vendors/new` → pick a file BEFORE saving name | Draft created silently, upload succeeds |
| 3.4 | File magic-byte check | Upload `.exe` renamed `document.pdf` | Rejected — "file signature does not match PDF" |
| 3.5 | 5 MB upload cap | Upload 10 MB file | HTTP 413 |
| 3.6 | KZ license auto-map | Set category "Medical gas pipeline systems" | Required licenses list populates automatically |

**Hacks:**
- Path traversal in filename: `../../etc/passwd.pdf` → filename sanitised
- Content-Type spoof: send `text/html` as `Content-Type` but PDF magic bytes → still accepted if magic OK
- Race condition: fire 20 parallel POSTs on same registration → only one `vendor_ref` should exist

---

## 4 · Notices, Corrigenda & Two-Cover Bidding

| # | Test | Steps | Expected |
|---|---|---|---|
| 4.1 | Notice publish | Admin → Notices → New → fill + Publish | Public `/` shows notice; audit log has `notice.published` |
| 4.2 | Corrigendum publish | Admin → Corrigenda tab → pick notice → New → Publish | Public NoticeDetail shows amber banner "Corrigendum No. 1" |
| 4.3 | Corrigendum updates deadline | Publish with `new_submission_deadline` | Notice deadline updates automatically |
| 4.4 | Withdraw corrigendum | Admin → Corrigenda → Withdraw | Public banner disappears |
| 4.5 | Two-cover — commercial redaction | Vendor submits bid → login as `certifier` (tech-only) → view bid | `price_amount`, `commercial_notes`, `documents[kind=commercial]` all **hidden** |
| 4.6 | Financial open gate | Try `POST /bids/{id}/financial-open` before `technical-clear` | HTTP 412 |
| 4.7 | Financial open post-clear | technical-clear → financial-open | HTTP 200; commercial data unlocked to committee/accounting |
| 4.8 | KYC pre-bid gate | Vendor without passing KYC tries `POST /api/v1/bids` | HTTP 412 with clear error |
| 4.9 | KYC bypass override | Admin sets `kyc_bypass=true` on notice → same vendor retries | HTTP 200 |

**Hacks:**
- XSS in notice title: publish `<script>alert(1)</script>` → NoticeDetail must render as text (DOMPurify sanitisation)
- Race: 3 vendors submit last-second bids at deadline − 100 ms → server timestamps enforce cutoff correctly
- Bid tamper: modify `price_amount` in the outgoing POST → server-side revalidation must reject non-BOQ line items
- Deadline hack: change client clock forward → server checks its own clock, not client's

---

## 5 · Bidding Pipeline (Escrow → Admin → Certifier → Legal → Accounting → Committee)

| # | Test | Steps | Expected |
|---|---|---|---|
| 5.1 | EMD pay via Stripe test | Vendor submits bid → picks Stripe → completes checkout | Bid state `emd_paid`, escrow ledger row created |
| 5.2 | EMD pay via Kaspi sandbox | Same, pick Kaspi | State advances (sandbox flow) |
| 5.3 | Escrow accept | Login as `escrow@` → accept EMD | Advances to Admin queue |
| 5.4 | Skip Escrow via curl | POST `/bids/{id}/admin-review` without `escrow_accept` first | HTTP 412 pipeline out of order |
| 5.5 | Certifier inspection | Certifier → open bid → attach inspection PDF → mark passed | Advances to Legal |
| 5.6 | Legal clearance | Legal → open bid → mark cleared | Advances to Accounting |
| 5.7 | Accounting sign-off | Accounting → open → sign off | Advances to Committee |
| 5.8 | Committee award | Committee chair → award to bid | Bid `status=awarded`; auto-drafts PO+SLA+Contract PDFs |
| 5.9 | Concurrent award | Two committee members award competing bids simultaneously | One wins, other returns HTTP 409 |

**Hacks:**
- Direct-state jump: try to set bid status via mongo query → all endpoints server-side, no direct-write
- EMD forgery: send fake Stripe webhook `checkout.session.completed` with random session_id → HMAC signature check rejects

---

## 6 · Reverse Auction Live Room

| # | Test | Steps | Expected |
|---|---|---|---|
| 6.1 | Admin creates auction | Admin → Reverse Auctions → New → set start 1M, floor 700k, Δ 25k, duration 30 min | Draft auction listed |
| 6.2 | Start auction | Click Start | Status → `live`, bidder link copyable |
| 6.3 | Vendor registration | Vendor opens bidder link, clicks Join | Assigned alias `Bidder A/B/C…` |
| 6.4 | Manual bid | Bidder A bids 950k | Accepted, leaderboard updates |
| 6.5 | Bid below floor | Bidder A bids 699k (below 700k floor) | HTTP 422 |
| 6.6 | Bid without decrement | Current 950k, bidder tries 940k (Δ25k required, would need ≤925k) | HTTP 422 |
| 6.7 | Autobid cascade | Bidder B arms autobid floor 800k → Bidder A bids 900k | Server auto-drops B to 875k (900k − Δ25k) |
| 6.8 | Anti-snipe | With 5 seconds to end, bidder bids | End time extends by anti-snipe window (30s) |
| 6.9 | Masked identity | Public state endpoint | Only `Bidder A/B/C` visible, no company names |
| 6.10 | Close auction | Admin → Close | `winner` set to lowest bid; state `closed` |

**Hacks:**
- Identity leak: check network calls in browser dev tools — should never contain vendor company name
- Bid replay: replay same bid POST twice quickly → idempotency key on payload
- WS flood: open 100 WS connections from one IP → rate-limit / disconnect

---

## 7 · Evaluation & Contract Award

| # | Test | Steps | Expected |
|---|---|---|---|
| 7.1 | Rubric define | Admin → Evaluation → set weights (Tech 60, Comm 40) | Saved |
| 7.2 | COI declaration | Evaluator declares COI on notice | Recorded, evaluator locked out of that notice |
| 7.3 | Score entry | Evaluators enter tech scores | Aggregated across evaluators |
| 7.4 | Envelope lock | Lock technical → try to edit score | HTTP 423 (locked) |
| 7.5 | Award Report generation | Click "Generate Award Report" | PDF renders with weighted scores + ranking |
| 7.6 | L1 auto-comparison | Admin → L1 Comparison → run for notice | Automatic lowest-price ranking table |
| 7.7 | Post-award auto-docs | Force bid → awarded | PO / SLA / Contract PDFs generated automatically |
| 7.8 | Regenerate award docs | Awards tab → Regenerate | New PDFs, same award_ref, older versioned |
| 7.9 | Awarded vendor download | Login as awarded vendor → dashboard | 3 download buttons for PO/SLA/Contract |

---

## 8 · DocuSign eSignature (Wave 43)

| # | Test | Steps | Expected |
|---|---|---|---|
| 8.1 | Status check | GET `/api/v1/docusign/status` | `configured:true, consent_ok:true` |
| 8.2 | Send award envelope | Admin → DocuSign tab → pick bid + Contract → signer info → Send | HTTP 200, `envelope_id`, `signing_url` returned |
| 8.3 | Embedded signing | Open the returned `signing_url` | DocuSign iframe renders, sign in sandbox, click Sign |
| 8.4 | Return URL | After signing complete | Redirected to `/admin?ds_signed=1` |
| 8.5 | Webhook update | Complete signing → wait 30s | Envelope row status → `completed` |
| 8.6 | Get envelope | GET `/api/v1/docusign/envelopes/{env_id}` | Live status = `completed` |
| 8.7 | Envelope log | DocuSign tab → scroll to envelope table | Row shows completed chip |
| 8.8 | Bid ack envelope | Send envelope on a bid (not awarded) | Similar flow |
| 8.9 | Consent expiry | Revoke consent in DocuSign admin → try send | HTTP 428 with `consent_url` in detail |
| 8.10 | Expired signing URL | Save signing URL, wait 6 min, click | DocuSign shows "link expired"; re-request from panel |

**Hacks:**
- Envelope tampering: replay Connect webhook payload with modified envelope_id → HMAC (if configured) blocks it
- Confused signer: change `client_user_id` in signing view request → DocuSign 400
- CSRF on send: POST `/envelope` without CSRF header → 403

---

## 9 · Meetings (Jitsi + Zoom)

| # | Test | Steps | Expected |
|---|---|---|---|
| 9.1 | Create Jitsi meeting | Admin → Meetings → New → provider=Jitsi → save | `join_url` set to `https://meet.jit.si/…` |
| 9.2 | Create Zoom meeting | Same, provider=Zoom | Real Zoom URL from S2S OAuth |
| 9.3 | Invitees | Add 3 emails → save | Each gets a magic invite link |
| 9.4 | Minutes upload | Add minutes text | Persisted, viewable |
| 9.5 | Cancel meeting | Admin → cancel | Status=cancelled, invitees notified |
| 9.6 | CSRF | Test POST without CSRF header | 403 |

---

## 10 · Product Catalog, Engagements & Stripe Billing

| # | Test | Steps | Expected |
|---|---|---|---|
| 10.1 | Catalog view | `/services` (client) + `/vendor/services` (supplier) | 34 + 21 products render |
| 10.2 | Category filter | Filter by "Advisory" | Only matching products shown |
| 10.3 | Anonymous quote request | Non-logged user → Request Quote | Engagement created, admin sees it |
| 10.4 | Admin quotes engagement | Set amount + currency + notes | Row goes `quote_requested → quoted` |
| 10.5 | Generate pay-link | Click Invoice | Stripe checkout URL returned |
| 10.6 | Stripe test checkout | Open link → pay with 4242 test card | Row → `paid`; webhook fires |
| 10.7 | Stripe declined card | Retry with 4000 0000 0000 0002 | Row stays `invoiced`, no double-charge |
| 10.8 | Server-authoritative price | Modify amount in checkout intent (dev tools) | Server ignores, uses DB value |
| 10.9 | Webhook idempotency | Replay same `checkout.session.completed` event | Second event ignored (idempotency key) |

**Hacks:**
- Coupon injection: try `?coupon=FREE100` on checkout URL → server drops any client-side query
- Refund tampering: try `POST /billing/refund/{tx}` as vendor → 403

---

## 11 · Escrow (Joint EMD Account)

| # | Test | Steps | Expected |
|---|---|---|---|
| 11.1 | Create joint account | Admin → Escrow → Add account with 2 officers | Saved |
| 11.2 | Init inbound EMD | Accounting → Init transaction | Officer snapshot frozen on tx |
| 11.3 | Single-signature release attempt | Only PMC officer signs → try release | HTTP 409 (dual sig required) |
| 11.4 | Wrong-side sign | PMC officer tries to sign as escrow_institution side | Server rejects — side is derived, not user-supplied |
| 11.5 | Dual sig release | Both officers sign same action → release | HTTP 200, ledger updated |
| 11.6 | Magic-link portal | Admin issues token for one officer → officer opens `/escrow/officer/{token}` | Sees pending tx, can sign |
| 11.7 | Revoke magic token | Admin revokes → officer clicks link | HTTP 410 |
| 11.8 | Audit trail | Every action | Immutable `audit_trail[]` on tx + `audit_log` global |

---

## 12 · Reports & Governance

| # | Test | Steps | Expected |
|---|---|---|---|
| 12.1 | Comparative XLSX | Reports tab → Excel — Asked vs Delivered | Downloads .xlsx with colour-coded rows |
| 12.2 | Comparative DOCX/PDF | Same for Word / PDF | Both render, PDF has watermark |
| 12.3 | Flowchart SVG/PDF | Reports tab → Flow chart | Renders 7 lanes ending in "Wave 43 shipped" |
| 12.4 | Test-plan PDF | GET `/api/v1/reports/test-plan.pdf` | Downloads this file as PDF |
| 12.5 | Snapshot to repo | Reports tab → Save Snapshot | Writes 5 files to `/app/docs/reports/` |
| 12.6 | Public roadmap | GET `/roadmap` (no auth) | Lists all delivered/planned rows |
| 12.7 | Hash-chained audit log | Audit tab → Verify chain | HTTP 200 `ok:true`, N events checked |
| 12.8 | Audit tamper | Modify one event's hash in DB → verify | HTTP 200 `ok:false, at_seq:X, reason:...` |

---

## 13 · Multi-Tenant & i18n

| # | Test | Steps | Expected |
|---|---|---|---|
| 13.1 | Default tenant | Visit `/` on `tender-hub-57.preview.emergentagent.com` | Skin = PMC-KZ-01 (navy) |
| 13.2 | Tenant override | Add `?tenant=DEMO-CORP` | Skin flips to purple |
| 13.3 | Tenant chip | Login → check admin header | Shows current tenant name |
| 13.4 | Tenant isolation | Corporate tenant admin cannot see PMC vendors | HTTP 403 or empty list |
| 13.5 | RU switch persistence | Switch to RU → reload | Language persists |
| 13.6 | Missing translation | Any admin panel in RU/KK | No literal `panels.*.key` visible; if a key resolves to itself, log it |

---

## 14 · Mobile Responsive (375 & 768 viewport)

| # | Test | Viewport | Expected |
|---|---|---|---|
| 14.1 | Home | 375 & 768 | Zero horizontal scroll |
| 14.2 | Admin dashboard | 375 | Tabs collapse to `<select>`, email hidden |
| 14.3 | Admin dashboard | 768 | Tabs wrap on multiple lines |
| 14.4 | Notice detail | 375 | Attachments + banner readable |
| 14.5 | Vendor register | 375 | 5-section wizard usable |
| 14.6 | Reverse auction room | 375 | Countdown + leaderboard fit |
| 14.7 | DocuSign panel | 375 | Every button reachable, form usable |
| 14.8 | Report cards | 375 | Grid becomes single column |

---

## 15 · Security & Compliance Hacks

Run these against **preview only**, never against production without permission.

| # | Attack | How | Expected outcome |
|---|---|---|---|
| 15.1 | Reflected XSS | Insert `<script>alert(1)</script>` in every text input (notice title, bid notes, vendor name, meeting subject, etc.) | Rendered as text |
| 15.2 | Stored XSS | Same, save + reload | Sanitised on write and on read |
| 15.3 | CSRF on state-changing GET | Craft `<img src=".../delete-notice/X">` on external page → open while logged in as admin | Server rejects (state-changing must be POST) |
| 15.4 | SSRF via URL upload | Provide `http://169.254.169.254/latest/meta-data` as a URL field | Blocked by outbound allow-list |
| 15.5 | IDOR | Vendor A tries GET `/api/v1/bids/{bid_of_vendor_B}` | 403 |
| 15.6 | Directory listing | GET `/uploads/` or `/keys/` | 404 |
| 15.7 | Private key exposure | GET `/api/v1/docusign/status` and grep response for `-----BEGIN` | Should NEVER return the key |
| 15.8 | JWT signature swap | Change algorithm to `none` in header | Rejected |
| 15.9 | Timing attack on login | Time 100 wrong-password requests vs 100 valid-email-wrong-password | Timings within ±20ms (constant-time compare) |
| 15.10 | Rate-limit bypass | Retry from different IP | Login lockout is per-account, not per-IP; API rate limit is per-IP |

---

## 16 · Performance / Load

| # | Test | Tool | Target |
|---|---|---|---|
| 16.1 | Public home | k6 / Locust | 100 RPS, p95 < 400ms |
| 16.2 | Notice list | Same | 100 RPS, p95 < 500ms |
| 16.3 | Admin dashboard | Playwright + `page.evaluate(() => performance.timing)` | LCP < 2.5s |
| 16.4 | PDF generation (award) | 20 concurrent | p95 < 3s (WeasyPrint is CPU-bound) |
| 16.5 | Reverse auction WS | 50 concurrent bidders | No dropped messages, p95 broadcast latency < 500ms |
| 16.6 | Cold start | Restart backend | First request < 8s (WeasyPrint import) |

---

## 17 · Regression Checklist (before every deploy)

- [ ] All Smoke Suite (§1) green
- [ ] Login flows for every seeded account (§2.10)
- [ ] Bid lifecycle end-to-end (§5.1 → §5.8)
- [ ] Corrigendum publish + withdraw (§4.2 + §4.4)
- [ ] Reverse auction full run (§6.1 → §6.10)
- [ ] DocuSign envelope send + webhook complete (§8.2 → §8.6)
- [ ] Comparative report XLSX/DOCX/PDF render (§12.1 → §12.3)
- [ ] Audit chain verify (§12.7)
- [ ] Mobile smoke at 375px (§14.1 → §14.3)
- [ ] `Save to Github` picks up `/app/docs/reports/*`

---

## 18 · Suggested External Testing Tools

### Free / open source
| Tool | Best for | Notes |
|---|---|---|
| **Playwright (MS)** | E2E web + API | Best-in-class, TS/Py/JS, our `data-testid` selectors work out of the box. `npx playwright codegen` records flows |
| **Cypress** | E2E web + component | Great dev DX, screenshots + video on failure |
| **Postman + Newman** | API regression | Import curl commands from this doc, run in CI |
| **k6 (Grafana)** | Load / stress | JavaScript scripts, cloud-runnable |
| **Locust** | Load in Python | Distributed workers, WebSocket support |
| **OWASP ZAP** | Security scan | Free active/passive scanner, DAST |

### AI-assisted (paid or freemium)
| Tool | Best for | Notes |
|---|---|---|
| **Testim (Tricentis)** | Self-healing E2E | AI selector fallback, records browser flow, adjusts when DOM changes |
| **BrowserStack Test-O** | AI-generated tests from plain English | Paste this test plan directly |
| **Momentic** | AI test authoring | GPT-4 turns descriptions into runnable Playwright |
| **QA.tech** | Autonomous exploratory | AI explores app + logs bugs like a QA person |
| **MagicTest** | Natural language E2E | "Log in as admin, publish a notice, verify banner" → runnable test |
| **Applitools Eyes** | Visual regression | AI diff on screenshots — great for our mobile audit (§14) |
| **Rainforest QA** | On-demand human + AI | Real testers execute your plan, results in hours |
| **Katalon Studio** | Codeless + AI | Free tier good for small teams |

### Security-focused
| Tool | Best for |
|---|---|
| **Burp Suite (Community/Pro)** | Manual pentest of every §15 hack |
| **OWASP ZAP** | Automated DAST — point it at preview and run baseline scan |
| **Nuclei** | Templated vuln scanning (`nuclei -u https://tender-hub-57.preview.emergentagent.com -t cves/`) |
| **Semgrep** | Static analysis on the codebase itself |

### For AI testing agents specifically
Feed them **this exact file** plus:
1. The list of `data-testid` values (grep the frontend)
2. The credentials block from §0
3. A statement like *"You have permission to test the preview environment only. Do not run destructive tests on `/prod`. Report bugs with steps + expected + actual."*

Good candidates for full autonomous runs: **QA.tech**, **BrowserStack Test-O**, **MagicTest** — they'll consume this doc as-is.

---

## 19 · Bug-Report Template

Ask any tester to file every bug in this format so triage is fast:

```
Title: <one-line summary>
Environment: preview | production
Route / endpoint: /admin/docusign  OR  POST /api/v1/bids
Role logged in as: admin | escrow_agent | vendor | anonymous
Steps to reproduce:
  1. …
  2. …
  3. …
Expected: …
Actual: …
Severity: blocker | major | minor | cosmetic
Attachments: screenshot / HAR file / console log
```

---

*Last updated 2026-08-07 · Wave 43. Ping the admin console → Stakeholder Reports for the always-current Asked-vs-Delivered file.*
