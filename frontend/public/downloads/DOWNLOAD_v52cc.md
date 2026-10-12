# PMC Managers — Frontend v52cc (12 Oct 2026)

## What's in this build (Tender Builder clarity pack — user Q&A follow-up)

### 1. Critical Dates — auto-fill + ordering validation
- **Clone as draft** now stamps a FRESH schedule anchored to today instead of
  copying the master's stale dates:
  Publish = today · Doc sale = today → +7d · Clarification = today → +10d ·
  Bid submission = +1d → +21d · Bid opening = +22d.
- **Save is blocked** with a plain-English toast when dates are out of order:
  Publish ≤ Doc Sale Start · Doc Sale Start ≤ End · Clarification Start ≤ End ·
  Submission Start ≤ End · Submission End ≤ Bid Opening.

### 2. Tender Documents section — clarity relabel
- Renamed to **"Tender Documents — schedule (bidders' checklist)"** with an
  in-section hint: it is a document *index* (names/descriptions/sizes printed
  in the tender PDF), not a file upload — actual files go through the
  **Choose Files** bulk-upload block below or per-section attachment buttons,
  and rows persist only after **Save**.

### 3. Mandatory fields marked + Draft → Notice bridge
- The fields a Notice needs are now starred in the tender header form:
  **Title \*, Work Description \*, Tender Value in ₹ \*, Product Category \*,
  Bid Submission End Date \***.
- New **⇢ CREATE NOTICE** button (`tb-create-notice`) on every draft:
  - Refuses with a specific "Fill the mandatory (*) fields first: …" toast
    until all starred fields are filled.
  - On success, opens **Admin → Notices → New notice** pre-filled (title,
    description, budget INR amount, EMD fixed amount, submission deadline,
    linked tender template) — the admin only attaches the primary tender
    document and hits Create & Publish.
  - This closes both the "why can't I publish from Tender Builder" and the
    "my draft isn't in Notices → Drafts" gaps.

## Deploy
- Backend: unchanged from v52bz.
- Frontend: sync this zip to S3, invalidate CloudFront `/*`.

File: `pmc-frontend-v52cc-prod-build.zip`
