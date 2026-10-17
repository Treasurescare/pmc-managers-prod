# PMC Managers v54h — Default country + upload polish

Release target: 17 Feb 2026

**Contains everything from v54a → v54g plus the items below. Deploy this
pair and skip earlier bundles.**

## Fixes

### 1. `/register` no longer defaults to Kazakhstan
- The country dropdown now starts blank — you must pick one before the
  resume-link button activates.
- Once you successfully send a resume link, your choice is remembered in
  the browser (`localStorage`). Next time you open `/register`, the
  dropdown prefills with your last country.

### 2. Section A / C / D uploads — View / Download appear immediately
When a vendor uploads from inside the resume page, the View / Download
buttons now render immediately on the slot card. Previously the link
only materialised when the parent re-rendered with fresh `regId`/`token`
props, which could lag behind the upload POST — vendors saw the "✓
uploaded" toast but no action buttons. DocSlot now captures the actual
`rid`/`tok` used by the upload call and uses them as a fallback source
for the View / Download links.

### 3. Section D 422 — richer diagnostics
If the save payload ever carries a field the backend doesn't recognise,
the browser console now prints the offending field names (e.g.
`[saveDraft] dropping unknown fields: ["foo"]`) and the save proceeds
with the stray fields dropped — so vendors are never blocked from
advancing. If the 422 persists, we now have the exact field name in
console logs instead of the opaque "Extra inputs are not permitted".

### 4. Build stamp bump
Footer + `/api/v1/_version` now report **v54h**.

## Deploy

1. EB: upload `pmc-backend-v54h.zip` → wait for Green.
2. S3: sync `pmc-frontend-v54h-prod-build.zip` contents (no `--delete`).
3. CloudFront: invalidate `/*`.
4. Visit `https://pmcmanagers.com/api/v1/_version` → should return
   `{"version":"v54h"}`.
5. Scroll to the homepage footer → should read **Frontend v54h · Backend v54h**.

## Artifacts

* Backend: `pmc-backend-v54h.zip`
* Frontend: `pmc-frontend-v54h-prod-build.zip`
