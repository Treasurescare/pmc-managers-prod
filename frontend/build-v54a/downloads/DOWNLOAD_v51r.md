# PMC Managers — Release v51r (cumulative, supersedes v51o–v51q)

## Fixes in this build (vendor portal → Start bid, mobile)

1. **"Submit & pay EMD" button no longer hidden under the bottom menu.**
   The Start-bid page had no bottom clearance, so the fixed mobile tab
   bar covered the pay button at the end of the form. The page now pads
   160px at the bottom on phones — the button always scrolls fully into
   view above the menu.
2. **Uploaded files are visible and viewable.** A global theme remap
   (meant for dark pages) was forcing the uploaded-file text to cream on
   a near-white background — invisible. The Start-bid page now keeps
   dark slate text, and every uploaded document renders as a clear white
   chip showing `TECHNICAL · filename.pdf (size)` with a working
   **View** link (opens the file in a new tab) and Remove.
3. **Upload slots and payment-gateway options stack vertically** on
   phones instead of 3 squeezed columns.
4. Submit button tap target enlarged.

### Also included (v51o–v51q)
- Bidding Ops mobile: tabs wrap, counts match visible rows, row-card
  checkbox alignment.
- Admin drawer scrolls to Masters / Events on iOS (100dvh fix).
- Admin Vendors: toolbar wraps 2-up; giant-button padding bug fixed.
- Admin Vendors: tapping a row expands the KPI/KYC detail inline below
  the row on mobile; desktop keeps the right column.
- Masters: all 13 tabs visible as wrapping chips; active chip solid navy.

## Deploy
- Frontend: `pmc-frontend-v51r-prod-build.zip` → S3, then CloudFront
  invalidate `/*`. Deploy this one only.
- Backend: unchanged since v51n (`pmc-backend-v51r.zip` identical,
  included for convenience).
