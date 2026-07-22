# PMC Managers — Training Video Script

**Target length:** ~9 minutes
**Audience:** New vendors, buyers, and PMC administrators
**Tone:** Confident, institutional, procurement-officer-friendly
**Recording setup:** Chrome full-screen at 1920×1080, cursor visible, no OS chrome. Screen at https://tender-hub-57.emergent.host

---

## Chapter 0 · Cold Open (00:00 – 00:20)

**On screen:** Landing page hero — the navy split with the port image, "Procurement that *travels borders*." headline visible.

**Narration:**
> Meet PMC Managers — the global tender board built for enterprises and vetted vendors. Register your company once, comply with jurisdiction-specific IDs, and bid across continents from a single unified dashboard.

**Cursor action:** Slow pan over the frosted-glass Live Tenders Board card (Open Tenders / Vetted Vendors / Board Liquidity). Zoom on the pulsing green ACTIVE dot.

---

## Chapter 1 · The Landing (00:20 – 00:50)

**On screen:** Scroll landing page top-to-bottom.

**Narration:**
> Every open tender, every vetted vendor, every currency, live from four continents. Registration is free. Compliance verification runs automatically in the background. Whether you're a buyer publishing a request for proposal or a vendor submitting a bid, your workflow is one click away.

**Cursor action:**
1. Click on the "Register as vendor" primary CTA — cut to Register page.

---

## Chapter 2 · Vendor Registration (00:50 – 02:00)

**On screen:** Register page (split navy with port image).

**Narration:**
> Vendor onboarding takes about ten minutes. Choose "Vendor," sign up with Google or an email address, then complete the six-step KYC profile. We ask for the standard basics — legal name, country of incorporation, business ID — then bank details, business capability, KYC documents, and finally a signed declaration.

**Cursor action:**
1. Toggle **VENDOR** button (data-testid `register-role-vendor`) — highlight.
2. Fill demo values: `Global Supplies Inc.` / `demo-vendor@example.com` / `Vendor@123`
3. Click Continue → land on `/vendor` dashboard.
4. Click **Company Profile** in sidebar → the 6-step wizard opens.
5. Slow pan the numbered chip stepper — Section A · B · C · D/E.
6. Fill Step 1 quickly, then jump ahead by clicking Step 6 to show the signature block.

---

## Chapter 3 · Registration Fee via Stripe (02:00 – 02:30)

**Narration:**
> Once your profile is submitted, PMC Compliance reviews the file within a business day. A one-time registration fee of one hundred US dollars is payable through Stripe — the platform handles receipts, tax invoices, and refunds automatically.

**Cursor action:**
1. Click **Registration Fee** sidebar link.
2. Click the "Pay registration fee" button → Stripe checkout page (do NOT complete — press Back).

---

## Chapter 4 · Buyer Workflow · Publishing a Tender (02:30 – 04:00)

**On screen:** Log out. Sign in as `buyer@pmcmanagers.com` / `Buyer@123`. Land on `/buyer`.

**Narration:**
> Buyers publish work in three flavours: a Tender for general procurement, an RFP for consulting or complex scopes, and an RFQ for line-item quotations. The form is identical, only the required fields adapt.

**Cursor action:**
1. Click **New RFP** in sidebar.
2. Fill in title: "Kazakhstan Substation Design 2026"
3. Category: "Consulting & Advisory"
4. Budget: 250,000 USD
5. Delivery country: KZ
6. Deadline: 30 days from now
7. Scroll to **Governance** panel — highlight:
   - **Department** dropdown (select "Medical Facilities")
   - **SBD template** dropdown (mention: "if we've uploaded a Standard Bidding Document, it auto-attaches")
   - **Force Contracts Committee approval** checkbox
   - **EMD required** — toggle on, set amount 5,000 USD
8. Scroll to **Evaluation framework** — highlight:
   - Two-envelope sealed bidding checkbox — click it.
9. Add two evaluation criteria (Technical 60%, Experience 40%).
10. Click **Publish RFP**.

**Narration:**
> Because we selected a department with budget thresholds, this RFP now goes to Contracts Committee review — vendors will not see it in the live feed until an administrator signs it off.

---

## Chapter 5 · Admin Approval (04:00 – 04:30)

**On screen:** Log out. Sign in as `admin@pmcmanagers.com` / `Admin@123`. Land on `/admin`.

**Narration:**
> Approvals are role-driven. Admins see any pending tender at a glance.

**Cursor action:**
1. Open **All Tenders** or navigate to the RFP just created.
2. Show the **Approval Panel** — highlight numbered chain with "Contracts Committee" step pending.
3. Click **Approve · Contracts Committee**.
4. Confirm the RFP now shows status **OPEN**.

---

## Chapter 6 · The Live Feed & SSE (04:30 – 05:00)

**On screen:** Right-rail Tender Feed.

**Narration:**
> Every vendor sees new tenders arrive live — no refresh, no polling. It's a Server-Sent Event stream. Filter by RFP, RFQ, tender, your country, or unread only.

**Cursor action:**
1. Click each filter chip (**ALL / RFP / RFQ / TENDER / MY COUNTRY / UNREAD**).
2. Click on the newly-published RFP in the feed → open tender detail.

---

## Chapter 7 · Vendor Bidding (05:00 – 06:30)

**On screen:** Log out. Sign in as `vendor@example.com` / `Vendor@123`. Navigate to the RFP.

**Narration:**
> Vendors see everything at a glance — budget in their local currency, deadline countdown, required licenses, and a clarifications panel where they can ask questions publicly.

**Cursor action:**
1. Point at the **FX chip** — click the currency dropdown, switch USD→KZT, then EUR.
2. Ask a question in the Q&A panel: "Is remote design work acceptable?" — Submit.
3. Scroll to the bid form. Fill in:
   - Technical proposal (2–3 sentences)
   - Commercial proposal / price
   - Delivery days: 45
   - EMD reference: `TRXN-2026-DEMO`
4. Click **Submit bid**.

**Narration:**
> Because this is a two-envelope RFP, the buyer will open technical envelopes first, qualify us on technical merit, then reveal our commercial bid. The Earnest Money Deposit we referenced will be automatically refunded if we lose the award.

---

## Chapter 8 · Two-Envelope Evaluation (06:30 – 07:30)

**On screen:** Log out. Log in as `buyer@pmcmanagers.com`. Navigate to the RFP.

**Cursor action:**
1. Show the **Two-envelope Panel** — Stage 1 · Sealed.
2. Click **Open Technical Envelopes** → Stage 2 badge appears.
3. In the scoring matrix, click **Qualify** on the vendor bid.
4. Click **Open Commercial Envelopes**.
5. Fill in technical scores, save.
6. Click **Award**.

**Narration:**
> The audit trail records every one of these actions with a SHA-256 hash chain. Let's look at it.

---

## Chapter 9 · Audit Trail (07:30 – 08:00)

**On screen:** Log in as admin. Navigate to **Audit Trail** sidebar link.

**Narration:**
> Every governance action is written to an immutable ledger. Tender creation, approval, addenda, Q&A answers, bid awards, EMD refunds — each row carries a SHA-256 hash of the previous row's hash. If any past event is altered, the chain breaks.

**Cursor action:**
1. Click **Verify chain integrity**.
2. Show the green "Chain intact · N events checked" badge.
3. Filter by `bid.award` — highlight the row from the previous chapter.

---

## Chapter 10 · Vendor Performance (08:00 – 08:30)

**On screen:** Log out. Log in as vendor. Click **Performance** in sidebar.

**Narration:**
> Vendors monitor their bidding health here — win rate, average price, delivery accuracy, EMD forfeitures, and category-level trends over the last twelve months.

**Cursor action:**
1. Slow pan over the 4 KPI cards.
2. Point at the category-progress bars.
3. End on the "Suggestions" block.

---

## Chapter 11 · Close (08:30 – 09:00)

**On screen:** Fade back to landing page with the Live Tenders Board.

**Narration:**
> That's PMC Managers — a global tender board built on jurisdictional trust, procurement transparency, and real-time compliance. Register today at tender-hub-57.emergent.host — your first tender is one workflow away.

**End card:** Logo + tagline "Procurement that *travels borders*."

---

## Screen recording checklist
- [ ] 1920×1080, 30fps, MP4/H.264
- [ ] Cursor size 2x, click ripple ON, keystroke overlay OFF
- [ ] Chrome bookmarks/toolbar HIDDEN (F11 fullscreen)
- [ ] Browser cache cleared before recording
- [ ] Demo data seeded — run `curl` recipes in `/app/memory/test_credentials.md` if needed
- [ ] Chapters separated with 0.5s fades
- [ ] Music bed: institutional/orchestral, -18 LUFS under narration
