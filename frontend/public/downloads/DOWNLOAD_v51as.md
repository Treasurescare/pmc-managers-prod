# PMC Managers — v51as Frontend-only patch (triaged from 07-Oct bug sheet)

**Build date:** 2026-10-07
**Bundle:** `pmc-frontend-v51as-prod-build.zip`
**Backend:** no changes — reuse `pmc-backend-v51aq.zip`

## 🐞 Bugs fixed from the 07-Oct bug sheet

- **BO review drawer empty (row 1 of xlsx + current screenshot)**: clicking
  the **Review** button on a Bidding Ops row used to navigate to a
  separate detail page that often showed nothing. It now opens the
  **inline right-hand clearance-path panel** on the same page (same code
  path as clicking the row itself) — users immediately see bid ref,
  stage, price, EMD, timeline and quick actions. Shift/Cmd/Ctrl-click
  still opens the standalone `/admin/bids/{id}` page in the new tab for
  deep-review flows.
- **"Invited undefined" toast on vendor invite (row 13 of xlsx)**:
  `VendorsPanel.invite()` previously rendered the response object
  blindly; when the backend returns a 202 (queued) with no email echo the
  toast showed *"Invited undefined · undefined"*. Now falls back to the
  email entered in the invite form and shows "pending" for the vendor_ref
  until the next refresh fills it in.

## 📝 Bugs triaged but still open

The remaining 22 items in the sheet span many modules and were not safe
to batch into one pass. Agreed order to address next (see below for
grouping):

**P0 (blocking) — ~2 hrs backend + ~1 hr frontend each**
- $0 EMD flow regressions (xlsx row 14) — my v51al fix (free EMD auto
  completes) needs a sanity screenshot since customer still reports it.
- Vendor approval not reflecting in frontend after admin approves
  (xlsx row 15) — likely a stale cache in VendorsPanel.load().
- Download NIT logs user out (xlsx row 8) + tender-download redirects to
  signin (row 3) — public endpoint presign-url likely missing public
  bucket policy; backend audit required.
- Evaluation page + L1 Award page both crash with "Something crashed"
  (docx items 14 & 15) — error-boundary fallback is firing; need the
  component stack from Sentry to locate the throw.

**P1 (UX)**
- File-type validation (only PDF for tech/commercial) — row 2
- Register-on-behalf: missing * marks + no Next button — row 6
- Comma not accepted in "Register on Behalf of Supplier" — row 11
- DocuSign "Resend" error on older bids — row 12
- DocuSign admin-sign doesn't flip vendor status — row 17
- Stakeholder Reports disappears from sidebar after Bidding Ops — row 20
- Blacklist "Remove" button disabled when reason present — row 17 (docx)
- Admin crashes after prolonged use — needs profiling

**P2 (missing features)**
- Engagements module has no "schedule meeting" action — row 19 (docx)
- Admin corrigendum published but not shown on public tender page — row
  22

## Deploy

Unzip into S3 bucket, overwrite v51ar, run CloudFront invalidation `/*`.
