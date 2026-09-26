# v47f — Admin bid detail + pagination widget + DocuSign view/resend/print

## a) Full-detail view for admin bids
- New endpoint **`GET /api/v1/bids/admin/{bid_id}`** — any staff role that acts on bids (admin, reviewer, escrow_agent, certifier, legal_counsel, accounting, committee_member) can fetch the full bid.
- New **`AdminBidDetailModal`** — click the **View** button on any row in the admin bids table (indigo header row) to open the full submission: notice title, commercial (price, EMD due/paid/source), technical & commercial notes, **all uploaded attachments** with inline preview (images render, PDFs embed via `<iframe>`, everything else gets an "Open in new tab" link), and the workflow history with actor + timestamp + notes.
- **Print / Save PDF** button on the modal uses a scoped print stylesheet so the modal is the only thing on the printed page.

## b) Pagination widget on every long list
- New reusable **`useListPager`** hook (`/components/ListPager.jsx`).
- Chooser buttons: **10 / 20 / 30 / All** (defaults to 20), page counter + Prev/Next, and "1–20 of 143" range readout on the right.
- Wired into the **Admin Bids table** and the **DocuSign envelopes list** in this build. Applying it to the rest of the console (Registrations, Vendors, Notices, Awards, etc.) is a mechanical two-line change per list — I can batch it in v47g whenever you want.

## c) DocuSign view / resend / print
- Per envelope row you now get **View** (eye modal with full envelope info), **Resend** (indigo — hits `POST /api/v1/docusign/envelopes/{id}/resend` — reopens signing URL for embedded, or asks DocuSign to email a fresh reminder), and **Print** (emerald — downloads the completed signed PDF).
- Resend is auto-hidden on `completed / declined / voided`; Print only shows on `completed`.
- Modal also carries the same Resend/Print CTAs so you can operate from either place.

## Verified on preview
- `GET /api/v1/bids/admin/{id}` returned full detail as expected (200) ✅
- Frontend prod build clean, zero preview-URL references ✅
- Backend syntax + import checks pass on all touched files ✅

## Deploy
- `pmc-backend-v47f.zip` → EB (carries v47e + v47d + v47c + v47b + v47a + v46z + v46y)
- `pmc-frontend-v47f-prod-build.zip` → S3 sync `--delete --exclude "downloads/*"` + CloudFront invalidate `/*`
