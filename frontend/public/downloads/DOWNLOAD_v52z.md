# PMC Managers — Release v52z (frontend only)

## What changed since v52y

### Fix: HTTP 422 "String should have at most 3 characters" on Create Notice
**Root cause:** a tender's country can be stored as the full NAME (e.g.
"India" — typically when the AI/DPR fill writes it) while
`POST /api/v1/tender-pro/next-reference` and
`POST /api/v1/tender-pro/templates/{id}/save-as-master` both enforce
`country` as a 2–3 char ISO code. Tender Builder sent `INDIA` (5 chars)
straight through → Pydantic 422. The plain Save worked (that endpoint has
no country constraint), which is why you saw "Saved" and the red 422 toast
together.

**Fix (`TenderBuilderPanel.jsx`):** new `toIso2()` helper — accepts "IN",
"in", or "India"/"INDIA" and always yields the ISO-2 code by looking it up
in the 250-country master. Applied at all three country call sites:
1. **Generate reference** (`genRef`) — normalises before calling
   next-reference; prompts for ISO-2 only if the name isn't in the master.
2. **Save as master** — prompt default and user input both normalised.
3. **Create Notice prefill** (`delivery_country`) — the Notices form now
   receives "IN", not "INDIA", so the EMD-master picker and category
   refresh also query with the right code.

**Verified in preview (curl):** `next-reference?country=INDIA` → 422
(reproduced exactly); `country=IN` → 200 `PMC-IN-TENDER-…`. Frontend
production build compiles clean. No backend change — backend stays strict
on ISO codes (correct contract).

## Deploy

Frontend only: unzip `pmc-frontend-v52z-prod-build.zip` to the S3 bucket
root, CloudFront invalidate `/*`. No EB redeploy needed.

---

## Appendix — How to read your PRODUCTION MongoDB Atlas storage

Do this once to see the real prod numbers (preview ≠ prod):

1. Log in at https://cloud.mongodb.com → pick your **Project** → **Cluster**.
2. Click **Browse Collections** (or the cluster name → Collections tab).
3. Select your database in the left tree. Atlas shows **each collection's
   storage size and document count** in the right pane.
4. Screenshot that list (or copy the top rows) and send it to me — I'll tell
   you exactly what to trim and what's safe.

Expected shape based on the codebase: `masters_unspsc` (~40 MB) and
`masters_cities` (~25 MB) will dominate — both required, leave them.
`uploads` (inline base64 files) is the one to watch; everything business
(notices, bids, vendors, payments, corrigenda) should be well under 10 MB.

Free-tier reality check: Atlas M0 = **512 MB**. At the profiled growth rate
your business data is nowhere near the cap; the ceiling risk is file
uploads. If `uploads` is big in prod, the proper fix is moving file storage
to object storage (S3-style) — say the word and I'll scope it.
