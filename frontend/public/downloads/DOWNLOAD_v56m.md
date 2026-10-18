# PMC Managers — Release v56m

## What changed
The public marketing site is now fully clickable. Previously most controls were
placeholders (`href="#"` / unwired forms). Now wired end-to-end:

- **Hero search** — keyword + country dropdown + **Find tenders** → `/tenders/live`
  with the search prefilled and filtered.
- **Popular chips** (Closing this week, Civil works & MEP, Medical equipment,
  IT & digital health) → prefiltered tenders list.
- **Platform stat cards** (notices / suppliers / work packages / audit ledger)
  are clickable → tenders list / register / trust page.
- **Programme category cards** (Modular medical, Education, Hostels, Utilities) →
  tenders list.
- **Trust & Security page** — "Verify" → Contact; "Report a concern" → Contact.
- **Contact page** — "Send message" no longer reloads; shows a confirmation.
- **Top nav + footer links** on every public page now route correctly
  (Tenders, For suppliers/buyers, Trust, Sign in, Register, About, Vision,
  Contact, Help Centre, Privacy, Raise a ticket, etc.).
- "Help & FAQs" still opens the slide-in help drawer (unchanged).

No backend behaviour changed in this release — the backend zip is rebuilt only to
keep the version stamp in sync (footer must read **Frontend v56m · Backend v56m**).

## Deploy order
1. Upload `pmc-backend-v56m.zip` to Elastic Beanstalk; wait for green/healthy.
2. Upload the **contents** of `pmc-frontend-v56m-prod-build.zip` to the S3 bucket root.
3. CloudFront → invalidate `/*`.
4. Confirm the footer shows **Frontend v56m · Backend v56m** (matching versions).

## Files
- Backend:  `pmc-backend-v56m.zip`
- Frontend: `pmc-frontend-v56m-prod-build.zip`
