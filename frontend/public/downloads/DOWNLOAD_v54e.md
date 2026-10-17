# PMC Managers v54e — Vendor registration validation & upload pack

Release target: 17 Feb 2026

**Contains v54a + v54b + v54c + v54d plus everything below.** Deploy this
pair and skip the earlier ones.

## Section A — Identity & Basic Information
- **Registration number & Tax ID are now live-validated against the
  selected country's official format** (CIN/PAN/GSTIN for India, BIN for
  Kazakhstan, UEN for Singapore, USCI for China, etc., from the
  `masters_country_formats` master). The label shows the local identifier
  name, the hint shows an example, and a wrong format blocks Next with an
  inline error. Countries without a seeded format fall back to free text —
  no false negatives.
- **Incorporation date is mandatory and capped at today** — the date
  picker can't select the future, typed future dates show an inline error
  and block advancing.

## Section B — Contact & Signatory
- Office phone, mobile, and signatory contact now have a **country ISD
  dropdown** (defaults to the vendor's country from Section A) plus a
  national-number field validated to 4–14 digits. Values are stored as
  "+91 98765 43210" so existing records stay compatible.

## Section C — Banking & Financial
- **Bank name is now a country-filtered type-ahead from the banks master**
  (the same `masters_banks` source the escrow banking step uses — 34
  Indian banks, etc.). Picking a bank **auto-fills its SWIFT code**
  (prefix + XXX, editable after). Countries without seeded banks fall back
  to free text.
- Turnover fields are hard-limited to numbers — letters can't even be
  typed; commas format as thousands.

## Section D — Business Profile & Capability
- **UNSPSC picker click fixed**: options now activate on mousedown so the
  debounced re-render can no longer swallow the click (this was the
  "unable to choose" bug).
- **Comma-separated entry works**: type any category followed by a comma
  (or press Enter with no match) to add it as a custom chip.
- Country combobox (from v54d) in Operating Regions unchanged.

## Uploads (all sections)
- View / Download verified end-to-end (token-authed endpoint returns the
  file inline with the correct content type).
- **Files can no longer vanish on save**: document slots are excluded from
  save payloads entirely — upload state is owned only by the slot
  upload/delete endpoints, so a stale save can never wipe them.

## Verified by automated browser run (13 checks)
Format hints ✓ · bad CIN rejected ✓ · future date rejected ✓ · upload →
View ✓ · view endpoint 200 ✓ · file persists after save+reload ✓ · ISD
dropdown defaults to vendor country ✓ · national number validation ✓ ·
bank pick autofills SWIFT ✓ · turnover rejects words / accepts numbers ✓ ·
UNSPSC search + physical click adds chip ✓ (×2) · comma custom chip ✓

## Artifacts

* Backend: `pmc-backend-v54e.zip`
* Frontend: `pmc-frontend-v54e-prod-build.zip`
