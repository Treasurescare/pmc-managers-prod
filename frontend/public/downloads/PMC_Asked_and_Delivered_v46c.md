# PMC Managers v2 — Asked & Delivered log · v46 → v46c
**Prepared:** 24 Feb 2026 · **Preview:** verified · **Production:** deployment in progress (job `60f300ec-7443-4bb9-ae84-d2df7002707a`)

This document is a chronological record of every request you made during this
session and exactly what was shipped in response. Each block ends with the
verification status.

---

## Session 1 — Vendor Ratings & Reviews portal (v46)

### You asked
> "Peer vendors + PMC management should be able to rate/review vendors. Admin-managed criteria, cumulative score, trust badge on the public landing page. This is something that needs to be worked properly."
>
> **Reviewer policy chosen:** PMC management + verified peer vendors + public buyers.  **Reviewer identity:** Anonymous but verified.

### We delivered
**Backend — new router `/api/v1/vendor-ratings/*`**
| Endpoint | Access | Purpose |
| --- | --- | --- |
| `GET /public/rubric` | public | Default rating rubric so buyer form can render sliders |
| `GET /public/top?limit=` | public | Top-rated vendors for landing page listing |
| `GET /public/{vendor_ref}` | public | Anonymised aggregate + trust badge for one vendor |
| `POST /public/submit` | public | Public buyer review · pending moderation · 3/email/day rate-limit |
| `GET /directory` | vendor auth | Vendor-scoped peer directory (excludes self) |
| `POST /peer/submit` | vendor auth | Peer review · blocks self-rating · auto-approve if verified |
| `GET /peer/mine` | vendor auth | Reviewer's own review history |
| `POST /admin/submit` | admin+CSRF | PMC management review · auto-approved |
| `GET /admin/reviews` | admin+CSRF | Moderation queue with filters |
| `POST /admin/reviews/{id}/moderate` | admin+CSRF | Approve / hide |
| `DELETE /admin/reviews/{id}` | admin+CSRF | Delete a review permanently |
| `GET /admin/pending-count` | admin+CSRF | For the admin nav badge |

**Trust badges (from approved reviews only)**
- Platinum · avg ≥ 85 AND ≥ 10 reviews
- Gold · avg ≥ 70 AND ≥ 5 reviews
- Silver · avg ≥ 55 AND ≥ 3 reviews
- Bronze · ≥ 1 review
- None · no reviews yet

**Frontend**
- `components/VendorTrustBadge.jsx` — reusable badge (5 tiers)
- `shared/PublicVendorProfile.jsx` — `/vendors/:vendorRef` public profile with badge, criteria averages, moderated comments, buyer review form
- `shared/TrustedVendorsSection.jsx` — "Trusted vendors" strip on the notice-board landing page
- `vendor-portal/RateAVendor.jsx` — new "Rate a vendor" tab in the vendor dashboard (directory search, sliders, own review history)
- `admin-console/vendor/ReviewModerationSection.jsx` — pending / approved / hidden / all tabs with approve / hide / delete per row, embedded in the existing Vendor Intel panel
- Existing `VendorIntelPanel` gained a "Trust badge" column

### Verification
- pytest `test_v46_vendor_ratings.py` — **24 / 24 pass**
- testing_agent iterations 21 & 22 — backend 100 %, frontend 100 % after two blocker fixes (adding the public rubric endpoint + a vendor-scoped directory)

---

## Session 2 — DPR robustness confirmation

### You asked
> "DPR Robustness: Please share one PDF that still causes errors so I can refine OCR to apply only where needed."
>
> You uploaded **KMT DPR and Financials.pdf** (Kazakhstan Medical Township).

### We delivered — verification only
No code change was required. We ran the file through the existing `POST /api/v1/tender-pro/dpr/analyze-json` endpoint on the live preview:

| Field | Extracted value |
| --- | --- |
| `work_title` | Kazakhstan Medical Township (KMT) |
| `work_description` | Populated (full multi-line project brief) |
| `tender_value` | USD 6.0 B – 6.2 B |
| `budget_currency` | USD |
| `period_days` | 1 825 |
| `location` | Almaty & Astana, Kazakhstan |

**Conclusion**: The existing `pypdf` extraction path handles your KMT PDF cleanly. No OCR integration needed for this document class. If you later encounter a scanned-image PDF that fails, please share that specific file and I'll add OCR (via `integration_playbook_expert_v2`) only for that failure mode.

---

## Session 3 — Reverse-auction invitations + Fees end-to-end (v46b)

### You asked
> "Reverse Auction: Build the real-time bidding room with invites, countdown, and live participant view.
> Fee Types: Wire subscription, premium, transaction, and data-intelligence fees end-to-end into payments."

### We delivered
**Reverse auction — invitations**
| Endpoint | Access | Purpose |
| --- | --- | --- |
| `POST /api/v1/reverse-auctions/{aid}/invite` | admin+CSRF | Batch-invite bidders by email · dedupe with resent_at · returns per-email token |
| `GET /api/v1/reverse-auctions/{aid}/invitations` | admin | List invitations with `joined` status |
| `GET /api/v1/reverse-auctions/invite/resolve/{token}` | public | Resolve invitation → auction summary |
| `POST /api/v1/reverse-auctions/invite/accept/{token}` | vendor auth | Auto-register invitee as masked participant |

**Fee end-to-end — Stripe checkout from a fee master**
- `POST /api/v1/billing/fee-checkout` — takes `fee_master_id + tender_value + origin_url`, computes the slab (fixed or percentage) server-side, creates a real Stripe Checkout session, records to `payment_transactions`.
- All five fee kinds supported: `registration`, `subscription`, `premium_subscription`, `transaction`, `data_intel` (plus existing `emd` and `tender_fee`).

**Frontend**
- `admin-console/auction/AuctionInvitations.jsx` — inline widget under every non-closed auction row · textarea, note, Generate + Copy Link
- `vendor-portal/AuctionInviteAccept.jsx` — new route `/vendor/auction/invite/:token` with auction summary + Accept & Join
- `admin-console/masters/FeeCharger.jsx` — new "Charge Fee" tab under Masters with country / kind filter, master selector, preview + Charge

### Verification
- Curl smoke: batch-invited 4 emails → 3 valid + 1 skipped, vendor_ref auto-linked for the known vendor
- Curl smoke: fee-checkout returned real `cs_test_…` Stripe session URL (KZT 50 000 for a KZ EMD master, USD 25 for a small transaction)
- pytest `test_v46b_auction_invites_and_fees.py` — **20 / 20 pass**
- testing_agent iteration 23 — backend 100 %, frontend verified

---

## Session 4 — Spectator + Templates + Refunds + Deploy (v46c)

### You asked
> 1. "Live Auction Spectator: Add a public read-only spectator view so buyers can watch a reverse auction without registering."
> 2. "Invitation Templates: Let admin save a reusable invite email + auto-send via Resend instead of copy-paste."
> 3. "Fee Refunds: Wire Stripe refund flow so admin can reverse a fee checkout from the transactions list."
> 4. "Deploy v46b: Ship the current preview build (backend + frontend) to AWS Elastic Beanstalk + S3/CloudFront."

### We delivered
**1 · Public spectator**
- New route `/auctions/:aid/live` — no auth required. 2 s polling of the existing public `/state`. Shows countdown (`mm:ss`), current-lowest price, masked leader alias, participant count, masked bid feed with "auto" pill for automated bids, savings-vs-start pct on close.

**2 · Invitation templates**
| Endpoint | Access | Purpose |
| --- | --- | --- |
| `GET /api/v1/reverse-auctions/invite/tpl` | admin | List templates |
| `POST /api/v1/reverse-auctions/invite/tpl` | admin+CSRF | Create · optional `is_default` |
| `PATCH /api/v1/reverse-auctions/invite/tpl/{tid}` | admin+CSRF | Update |
| `DELETE /api/v1/reverse-auctions/invite/tpl/{tid}` | admin+CSRF | Delete |

Placeholders supported inside `subject` and `body_html`:
```
{{invite_url}} {{auction_title}} {{notice_ref}} {{vendor_email}}
{{starting_price}} {{currency}} {{admin_note}}
```
The `POST /{aid}/invite` endpoint now accepts `template_id + auto_send + origin_url` — when both are provided we render the template per-recipient and dispatch through the managed email proxy (`emails.send_email`, which is your existing infrastructure). Response includes `auto_sent: N`.

The Auction Invitations widget in the admin panel gained a template dropdown and an "Auto-send emails now" checkbox (disabled unless a template is picked).

**3 · Fee refunds**
- `POST /api/v1/billing/refund/{session_id}` — retrieves the Stripe checkout session, resolves its `PaymentIntent`, calls `stripe.Refund.create` with a `reason` metadata, marks `payment_transactions.payment_status = "refunded"` with `refund_id`, `refunded_by`, `refunded_at`.
- Refuses non-paid transactions with a clear HTTP 400 and refuses missing sessions with HTTP 404.
- New admin panel tab "Billing & Refunds" (`data-testid=admin-tab-billing`) with a transactions table and a per-row Refund button (with reason prompt).

**4 · Deployment**
- Dispatched to the deployer agent — job `60f300ec-7443-4bb9-ae84-d2df7002707a`.
- Deployer will push the backend to `pmc-backend-prod` (Elastic Beanstalk, eu-west-2) and the frontend to the S3 bucket behind CloudFront distribution `E2WZT1TMQ0EK9W`.
- Notes for the deployer: MongoDB collections created lazily on first write (no migrations); Stripe / email keys already in EB env; WAF `SizeRestrictions_BODY = Count` still in effect.

### Verification (preview)
- Curl smoke: created "Standard invite" template · invite with `auto_send=true` → `auto_sent: 1`
- Curl smoke: `POST /refund/{session}` on a pending transaction → HTTP 400 with the message *"Cannot refund a pending transaction — only paid transactions can be refunded"* (guard confirmed)
- Curl smoke: `GET /reverse-auctions/{aid}/state` (public) → 200 with masked bids

---

## What was NOT changed (guard-rails)

- No changes to your existing DPR extraction pipeline · already handles KMT
- No changes to tender-templates CRUD, EMD master schema, notice / bid / evaluation flows, escrow module, or the Approval-Matrix system
- No SDK version bumps (Stripe stays at 14.4.1, React / FastAPI unchanged)
- WAF configuration untouched — the current Count action on `SizeRestrictions_BODY` remains as-is
- `.env` protected variables unchanged

---

## Immediate next actions for you

1. Watch chat for the deployer agent's completion card (backend URL + frontend URL)
2. **Publish invite templates in production**: Admin → Auctions → Draft → Invitations → Templates → create your standard invite so real bidders get branded emails
3. **Test refund on prod**: Run one small fee-checkout, wait for `paid`, then refund from the Billing tab to confirm production Stripe keys are wired
4. *(optional hardening)* Set `PUBLIC_BASE_URL` env on EB so the Stripe webhook URL doesn't rely on request-derived host

---

## Suggested near-term backlog (from earlier hand-offs)

- P1 · OCR fallback for scanned / image-only DPRs (only if you encounter a failing file)
- P1 · LSEG / Refinitiv KYC live integration — needs API credentials
- P1 · Reverse-auction session monitoring dashboard (participant health, connection heartbeats)
- P2 · WhatsApp / Telegram bid notifications
- P2 · Turkish / Russian / Kazakh translations of the user manual
- P2 · Refactor `tender_pro.py` into focused routers (DPR / references / fees / ratings)
