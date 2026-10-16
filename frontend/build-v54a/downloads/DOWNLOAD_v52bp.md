# PMC Managers — Release v52bp (10 Oct 2026)

## 📦 Download Links

- **Frontend (S3 / CloudFront)**: [`/downloads/pmc-frontend-v52bp-prod-build.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52bp-prod-build.zip)
- **Backend (AWS Elastic Beanstalk)**: [`/downloads/pmc-backend-v52bp.zip`](https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52bp.zip)

## 🎯 What's in v52bp

1. **Corrigendum PDF now downloadable without auth** — the diff-PDF endpoint `GET /api/v1/notices/<ref>/corrigenda/<cid>/pdf` is **public**; and admin-uploaded **corrigendum attachments** now ship under the `/api/v1/uploads/public-files/<key>` scope (`corrigendum-attachments`), so bidders no longer get the 401 "Not authenticated" error when clicking the attachment chip.
2. **Visible "Download diff PDF" button** — added on both the Admin Corrigenda row and every active corrigendum card on the public notice page. One click → opens the one-page diff PDF in a new tab.
3. **Vendor Notification Bell deep link** — publishing a corrigendum now also inserts a vendor-bell `notifications` record for every active bidder with `related_url = /api/v1/notices/<ref>/corrigenda/<cid>/pdf` + the notice ref. The vendor bell renders an **"📄 Open PDF"** button + a "View notice" button next to each corrigendum alert.

4. **Tender Builder filters actually filter now** — the Search / Country / Industry / Sort controls previously applied only to the Drafts list, and the Country dropdown was empty (built only from templates that had a country set). Now:
   - the same filters apply to the **Master Library** too,
   - the Country dropdown is seeded from the **country master** (31 ISO codes) union template-derived values, so it always has real options,
   - verified end-to-end: country=UZ shrinks masters 1→0 and drafts 5→0; search "Standard PSU" narrows both lists; name-A→Z sort reorders drafts.

### Earlier questions reconfirmed
- **Engagements meetings** → already shipped in **v52bl**. Admins can "Schedule meeting" on any engagement (date/time, duration, agenda, buyer / supplier / both, optional link). Backend `POST /engagements/{eid}/meetings`. Buyer email best-effort via Resend. Printable agenda.
- **Public corrigendum pill shows the latest** → shipped in **v52bo**. Verified: PMC-NOT-2026-0020 hero shows **"Corrigendum 4 · 10 Oct"** and hides itself when no active corrigenda exist.

## 🚀 Deploy

- Backend (Elastic Beanstalk): upload `pmc-backend-v52bp.zip`.
- Frontend (S3 / CloudFront):
  ```bash
  aws s3 sync build/ s3://<your-frontend-bucket>/ --delete
  aws cloudfront create-invalidation --distribution-id <dist-id> --paths "/*"
  ```
