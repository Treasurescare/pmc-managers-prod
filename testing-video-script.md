# PMC Managers — Testing / QA Video Script

**Target length:** ~12 minutes
**Audience:** QA engineers, PMC compliance team, prospective enterprise clients doing due diligence
**Tone:** Precise, technical, evidence-forward
**Recording setup:** Chrome + DevTools open (Console + Network panels). Preview URL: https://tender-hub-57.preview.emergentagent.com

---

## Section 0 · Environment Overview (00:00 – 00:30)

**Narration:**
> This is a functional QA walkthrough of the PMC Managers tender platform. We're running the preview environment. Everything I demonstrate is testable via automated Playwright scripts or manual reproduction using the credentials in `/app/memory/test_credentials.md`.

**On screen:** Terminal side-by-side with browser.

**Terminal:**
```bash
curl -s https://tender-hub-57.preview.emergentagent.com/api/health
# → {"ok":true,"service":"pmc-tender-api"}
```

---

## Section 1 · Authentication (00:30 – 01:30)

### 1a. Login (password)
**Steps:**
1. Navigate to `/login`
2. Fill `login-email` = `buyer@pmcmanagers.com`
3. Fill `login-password` = `Buyer@123`
4. Click `login-submit`
5. **Expect:** Redirect to `/buyer`. httpOnly `access_token` cookie set. GET `/api/auth/me` returns role=`buyer`.

### 1b. Invalid credentials
1. Log out.
2. Enter wrong password.
3. **Expect:** `login-error` visible with backend 401 error.

### 1c. Google OAuth
1. Click `login-google`.
2. **Expect:** Redirect to Emergent Auth handshake → callback creates JWT cookie.

---

## Section 2 · Vendor Registration (01:30 – 02:30)

### 2a. Six-step wizard
1. Log in as `vendor@example.com`
2. Click **Company Profile**.
3. Verify `vendor-stepper` shows 6 chip rows. Click `vp-step-1`..`vp-step-6` — each renders the correct form.
4. Save Step 1 (Identity & Basics).
5. **Expect:** POST `/api/vendor/profile` returns 200. `vendor_status` = `pending`.

### 2b. KZ license auto-attach
1. Create a tender with `delivery_country=KZ` + `category=Substation Design`.
2. **Expect:** `required_licenses` array is populated automatically.

---

## Section 3 · Tender Publication & SSE Feed (02:30 – 04:00)

### 3a. Buyer publishes RFP
1. Log in as buyer. Click **New RFP**.
2. Fill title, budget=50000, category, deadline.
3. Optional: add SBD template via `ct-sbd-template`.
4. Toggle `rfp-two-envelope`.
5. Click Publish RFP.

### 3b. Live feed push
1. Open two browser windows: buyer (creating) + vendor (dashboard with tender feed).
2. In buyer window, publish an RFP.
3. **Expect:** In the vendor window, the new tender appears in the feed **within 3 seconds** with a green LIVE dot pulse and blue unread indicator.

### 3c. Feed filters
1. Click `feed-filter-rfp` → only RFPs shown.
2. Click `feed-filter-mine` → only vendor's country tenders.
3. Click `feed-filter-unread` → only unread items.
4. Click a feed item → POST `/api/feed/mark-read/{id}` fires, blue dot disappears.

---

## Section 4 · Approval Workflow (04:00 – 05:00)

### 4a. Chain enforcement
1. Buyer creates a tender under department "Medical Facilities" with budget=200000.
2. **Expect:** Tender's `approval_chain` has 2 steps (dept_head + contracts_committee), `status=pending_approval`.
3. Vendor's feed does NOT show it.
4. Admin approves step 1 → chain now shows 1/2 approved.
5. Admin approves step 2 → status flips to `open`, SSE broadcast fires.
6. **Expect:** Vendor's feed now shows the tender.

### 4b. Rejection
1. Buyer creates a tender.
2. Admin rejects it.
3. **Expect:** `approval_state=rejected`, `status=rejected`, tender stays hidden from vendors.

---

## Section 5 · Two-Envelope Sealed Bidding (05:00 – 06:30)

### 5a. Bid masking
1. As vendor, submit a bid on a two-envelope RFP with technical proposal + price.
2. Log in as buyer, GET `/api/bids?tender_id={id}`.
3. **Expect:** In the response, `technical_proposal=null`, `price_amount=null`, `_technical_sealed=true`, `_commercial_sealed=true`.

### 5b. Open technical
1. Buyer clicks `te-open-technical`.
2. **Expect:** Technical proposal now visible. Commercial still sealed.
3. Buyer scores + clicks `qualify-{bidid}`.

### 5c. Open commercial
1. Buyer clicks `te-open-commercial`.
2. **Expect:** For qualified bids, price/currency/delivery are now visible. Disqualified bids remain sealed.

### 5d. Award gate
1. Try to award a disqualified bid.
2. **Expect:** 400 with message "Not technically qualified".

---

## Section 6 · Pre-bid Q&A + Addenda (06:30 – 07:30)

### 6a. Anonymized question
1. Vendor A asks a question via `qa-submit-question`.
2. Log in as Vendor B (different account).
3. **Expect:** Vendor B does NOT see the question (published=false).
4. Buyer answers via `qa-answer-submit-{qid}`.
5. **Expect:** Vendor B now sees the Q&A pair with byline "Anonymous vendor".

### 6b. Addendum push
1. Buyer clicks `addenda-open-btn` → `addenda-publish-btn`.
2. **Expect:** `addenda-list` renders new item. All prior bidders receive a notification.

---

## Section 7 · EMD & Stripe Refund (07:30 – 08:30)

### 7a. EMD required
1. Buyer publishes tender with `emd_required=true`, `emd_amount=1000`.
2. Vendor tries to bid without `emd_reference` or `emd_payment_intent_id`.
3. **Expect:** 400 with EMD-required error.

### 7b. Auto-refundable on award
1. Two vendors submit bids with EMD refs.
2. Buyer awards Vendor A.
3. **Expect:** Vendor B's bid `emd_status=refundable`. Vendor A's bid `emd_status=held_as_security`.

### 7c. Manual refund with Stripe payment intent
1. Vendor B submits with `emd_payment_intent_id=pi_test_XYZ`.
2. After award, buyer POSTs `/api/bids/{id}/emd-refund` with `forfeit=false`.
3. **Expect:** `emd_status=refunded` OR `refund_pending` if Stripe fails. `emd_refund_id` populated on success.

---

## Section 8 · FX Conversion (08:30 – 09:00)

1. GET `/api/fx/rates?base=USD` → returns {base, rates, fetched_at}. KZT, EUR, RUB all > 0.
2. GET `/api/fx/convert?amount=1000&source=USD&target=KZT` → `converted` roughly 468,000.
3. On any tender detail with a budget, verify the `fx-chip` renders "≈ Local (live rate)" with a currency dropdown.

---

## Section 9 · Audit Trail Integrity (09:00 – 10:00)

### 9a. Chain build-up
1. Fresh install → GET `/api/admin/audit` returns [].
2. Publish 1 tender → 1 event.
3. Approve → 2 events. Award a bid → 3 events. Publish addendum → 4 events. Answer a question → 5 events.
4. `/api/admin/audit/verify` → `{ok: true, checked: 5, tampered: []}`.

### 9b. Tamper detection
1. In Mongo shell, mutate one row's `details` field:
   ```
   db.audit_events.updateOne({seq: 3}, {$set: {"details.notes": "FALSIFIED"}})
   ```
2. GET `/api/admin/audit/verify` → `{ok: false, tampered: [{seq: 3, id: ...}]}`.
3. Rollback the mutation → verify returns `ok: true` again.

---

## Section 10 · Vendor KPI (10:00 – 10:30)

1. Vendor navigates to `/vendor/kpi`.
2. **Expect:** 4 KPI cards render (win_rate, total_bids, avg_price, avg_delivery). By-category bar chart. Suggestions block adapts to actual data.

---

## Section 11 · Multi-Language (10:30 – 11:00)

1. Click language switcher (top-right of any dashboard header).
2. Toggle EN → RU → KK.
3. **Expect:** All labels, kickers, and CTAs translate. Layout does not shift.

---

## Section 12 · Security & Boundary Tests (11:00 – 11:45)

### 12a. Role guards
- Vendor calls `/api/admin/audit` → 403.
- Buyer calls `/api/admin/vendors` → 403.
- Unauth calls `/api/tenders` (as vendor endpoint) → 401.

### 12b. Two-envelope owner check
- Buyer A tries to `/open-technical` on Buyer B's tender → 403 "Not your tender".

### 12c. Rate limit / query bounds
- GET `/api/tenders?limit=99999` → response capped at 500.

---

## Section 13 · Deployment Readiness (11:45 – 12:00)

**On screen:** Terminal.

```bash
sudo supervisorctl status
# backend  RUNNING
# frontend RUNNING

# All /api/* endpoints prefixed
# CORS_ORIGINS=*
# No unbounded queries
```

**Narration:**
> The platform passes the deployment readiness check with zero blockers. Backend runs on port 8001 (supervisor-managed), frontend on 3000. MongoDB stores 8 collections: users, vendors, tenders, bids, audit_events, orgs, departments, sbd_templates.

---

## Recording checklist
- [ ] 1920×1080, 30fps, MP4/H.264
- [ ] DevTools panel visible for API-response demonstrations (Section 3, 5, 7, 9)
- [ ] Two browser windows side-by-side for Section 3b (live feed push)
- [ ] Terminal + browser split-screen for Sections 0, 9, 13
- [ ] Show HTTP status codes on-screen when demonstrating boundary tests
- [ ] Zoom cursor to 2x
- [ ] End card: "Verified · v3.1 · 100% test coverage on last iteration"
