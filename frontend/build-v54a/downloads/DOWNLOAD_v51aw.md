# PMC Managers — v51aw (balance batch)

**Build date:** 2026-10-09
**Frontend bundle:** `pmc-frontend-v51aw-prod-build.zip`
**Backend:** no changes — reuse `pmc-backend-v51au.zip`

## 🐞 Fixed

- **Register-on-behalf required-field marks sweep (xlsx #6 balance)**:
  after v51av added the `required` prop to `Field` and marked Section A,
  this batch finishes Sections B, C and E:
  - **B** — Contact name · Mobile · Contact email · Signatory name ·
    Signatory contact
  - **C** — Bank name · Account number · SWIFT
  - **E** — Signature name · Signature title · Signature date
  Section D keeps its existing amber "Required" inline badges on the
  declaration checkboxes (already self-marking).

## 📝 Not in this bundle (needs your input)

- **DocuSign admin-sign doesn't flip vendor status (xlsx #17)**: I traced
  the completion handler (`_on_envelope_completed` in
  `routers/docusign.py:382`) — it stamps the bid with
  `{sub_kind}_signed_at` and emails the signer, but I can't safely guess
  which field your vendor-facing "status" tile reads. One screenshot of
  the vendor Signatures page after PMC countersigns (with the stale
  status visible) and I'll wire the exact flip.
- **Engagements module: no "schedule meeting"** (docx #19, P2 feature)
  and **admin-published corrigendum not on public page** (docx #18,
  backend already attaches `corrigenda[]` to the public notice payload —
  likely an `is_active`/`is_published` flag mismatch on the specific
  corrigendum; share the notice_ref and I'll confirm).
- **Admin crashes after prolonged use** (xlsx #4): memory profiling
  session needed.

## Deploy

Unzip into S3 (overwrite v51av), CloudFront invalidation `/*`, backend
unchanged.
