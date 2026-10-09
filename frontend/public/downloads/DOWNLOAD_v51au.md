# PMC Managers — v51au P0/P1 closing batch

**Build date:** 2026-10-07
**Frontend bundle:** `pmc-frontend-v51au-prod-build.zip`
**Backend bundle:** `pmc-backend-v51au.zip` (replaces v51aq)

## 🐞 P0 fixes

- **Evaluation page crash** (docx #14, xlsx #18). `AwardReport.ranking.map(...)` and
  the parent `<AwardReport report={report} />` crashed whenever the backend
  returned a partial award report (missing `ranking` or during the
  pre-generate state). Added `(report.ranking || []).map(...)` and defaulted
  the panel's `report` to `{}` so the Evaluation page always renders.
- **NIT public download logs user out** (xlsx #3, #8). The notice attachment
  download hit `/api/v1/uploads/files/{key}` which required
  `_require_any_signed_in`. For unauthenticated visitors the frontend
  interceptor bounced them to `/login`. Added a new
  `GET /api/v1/uploads/public-files/{key:path}` endpoint that allows
  anonymous access ONLY when the file was uploaded with scope
  `notice-attachments` AND its parent notice is published. The admin /
  authenticated endpoint stays untouched.

  **Frontend side needs a follow-up** (noted here, not in this bundle):
  the public tender page should route NIT download links to the new
  `/public-files/` endpoint. Point me at the component (likely
  `PublicNoticeDetail.jsx`) and I'll flip the URL in one line.

## 🐞 P1 fixes

- **Stakeholder Reports vanishes from sidebar after Bidding Ops** (xlsx #20).
  The Bidding Ops page uses its own inlined sidebar HTML (not `AdminEShell`),
  which was missing the Stakeholder Reports link. Added it.

## 📝 Deliberately deferred

Still require their own focused sessions:

- **DocuSign Resend error on older bids** (xlsx #12): the backend's resend
  endpoint already handles orphans + embedded+email paths; the specific
  error the user hits is `424` with "expired sandbox key in preview". This
  is an **environment** issue — the `DOCUSIGN_*` env vars in your preview
  environment have expired. Rotate the DocuSign integration key /
  JWT token and the Resend button will stop 424-ing. No code change.
- **DocuSign admin-sign doesn't flip vendor status** (xlsx #17): needs
  investigation of the webhook completion path (`_on_envelope_completed`).
- **Register-on-behalf UX** (xlsx #6, #11): comma / missing * / no Next
  button — needs Section A–E form audit (5 sub-components).
- **Blacklist remove button** (docx #17): need a reproduction state —
  the current code renders Unblacklist when `selected.blacklisted === true`.
  Reply with the vendor_ref you tested and I'll trace it.
- **Admin crashes after prolonged use** (xlsx #4): memory profiling.

## Deploy

1. Backend: `pmc-backend-v51au.zip` → EB upload-and-deploy. Watch Health flip Green.
2. Frontend: unzip `pmc-frontend-v51au-prod-build.zip` into S3 (overwrite v51at).
3. CloudFront invalidation `/*`.
