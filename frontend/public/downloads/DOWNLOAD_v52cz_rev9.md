# PMC Managers — Release v52cz rev9

**Date:** 14 Feb 2026
**Scope:** HTTP 422 fix on Notice ↔ Escrow routing · duplicate open-escrow-tx cleanup (button + script) · bank roster auto-heal + public “+ Add bank” self-serve · signatories step layout + mobile overflow fix

> **Supersedes v52cz rev8.** Deploy rev9 to resolve the two production errors you shared (routing 422 + duplicate-row EMD 409).

---

## What's new in rev9

### 1. P0 — Notice ↔ Escrow account routing no longer 422s
The admin Escrow institutions page bulk/per-row “Apply” called `PATCH /api/v1/notices/{ref}` with just `{escrow_account_id}`. The backend reused the full `NoticeIn` model, so Pydantic rejected the partial payload with **4× “Field required”** (title/description/category/submission_deadline).

Fixed:
- New `NoticePatchIn` model — every field `Optional`, same validators retained.
- Handler now `model_dump(exclude_unset=True)` → only keys actually sent are `$set`.
- Bonus: a PATCH that omits `is_published` no longer silently unpublishes a notice.
- Verified live: `PATCH {escrow_account_id: null}` returns 200, title preserved; `PATCH {title: "ab"}` still 422; `PATCH {budget_amount: -5}` still 422.

### 2. P1 — Clean up duplicate open escrow transactions (both options shipped)
Each bid must hold ONE open escrow row (`pending / received / awaiting_signatures`). Legacy rows (pre-v51ap guard) left two bids with duplicates — this is what causes the HTTP 409 you saw when recording an inbound against `PMC-BID-2026-00061`.

Rev9 ships two ways to clean them up:
- **Admin button (reusable)** — the red “Unresolved duplicates” banner on `/admin/e/escrow` now shows a **Cancel extras** button per duplicated bid. One click → confirm → the newest open row is kept, the rest are cancelled (audit trail preserved). `data-testid=escrow-tx-dupe-cancel-<bid_ref>`.
- **One-shot script** — `backend/scripts/cleanup_duplicate_escrow_tx.py`
  - Dry run (default): `python scripts/cleanup_duplicate_escrow_tx.py`
  - Apply: `python scripts/cleanup_duplicate_escrow_tx.py --apply`
  - Keeps the newest open row (ObjectIds sort by creation time), cancels the extras with a `by: system:cleanup-script` audit entry.

### 3. Bank roster missing banks — root cause fixed
Why Revolut / Wise weren’t in your dropdown even though they were in the roster: `server.py` only upserted `masters_banks` when the collection was **completely empty**, so production — seeded by an older, smaller roster — never received rev7/rev8 additions.

Rev9 unconditionally upserts all 146 banks on every boot (idempotent). On next backend deploy prod will auto-heal; **no script run needed**.

Verified live on preview:
```
GET /api/v1/masters/banks?country_code=GB&q=Revolut  →  [{"name":"Revolut", "swift_prefix":"REVOGB", "currencies":["GBP","EUR","USD"]}]
GET /api/v1/masters/banks?country_code=GB&q=Wise     →  [{"name":"Wise", "swift_prefix":"TRWIGB", "currencies":["GBP","EUR","USD"]}]
```

### 4. “+ Add bank” — registrant self-serve
If a bank is still missing (any country), the banking-step autocomplete now shows `+ Add "<typed>"` under the suggestions. One click:
- `POST /api/v1/masters/banks {country_code, name}` (public, deliberately — the wizard is pre-auth), tagged `source: "user_suggested"` for later admin curation,
- toast confirms,
- list refreshes with the new row,
- newly-added bank stays selected on the form.

Idempotent (same name upserts, no duplicates); validation rejects malformed inputs (`country_code` must be 2 ISO letters; name 2–120 chars). `data-testid=escrow-bank-<idx>-name-add-custom`.

### 5. Signatories step UI fix
Step 2 of the escrow wizard used a 4-column grid; the phone input (dial dropdown + local number) overflowed the card on screens narrower than ~1400px (that was your screenshot complaint). Rev9:
- Row grid → `md:grid-cols-2`.
- `PhonePrefixInput` local input gets `min-w-0` so it never leaks on tight viewports.

### Carried over (rev8 → rev2)
Duplicate email guard at every entry point, Escrow dashboard sidebar + clickable KPIs, 146-bank roster across 20+ countries, ISD phone picker with length validation, Save-as-draft + Previous on every wizard step, country-aware reg/tax/VAT regex, structured address with cascading state/city, searchable country/state/bank pickers, in-page document viewer, magic-token document endpoint, auto geography & bank bootstrap, blank form auto-generation, bundle picker on bids, Documents tab data-driven, Download all above list.

### Tests
`backend/tests/test_v52cz_rev9.py` — **5/5 green** (partial PATCH preserves title; sent fields still validate; GB roster has Revolut / Wise / Monzo / Starling; suggest-bank upsert idempotent; suggest-bank 422 on bad input).

Full targeted suite (rev5 + rev6 + rev7 + rev9) 20/20 green against the preview backend.

---

## Files

| File | Purpose |
|---|---|
| [`pmc-backend-v52cz-rev9.zip`](./pmc-backend-v52cz-rev9.zip) | Elastic Beanstalk backend package |
| [`pmc-frontend-v52cz-rev9-prod-build.zip`](./pmc-frontend-v52cz-rev9-prod-build.zip) | S3 / CloudFront static assets |

> **No `docker-compose.yml` is shipped** (deliberately — EB AL2023 Docker platform must auto-generate the compose from the Dockerfile’s `EXPOSE 80`). Do not add one back.

---

## Deployment

### Backend → AWS Elastic Beanstalk (AL2023 Docker)
1. Upload `pmc-backend-v52cz-rev9.zip` as a new application version → Deploy.
2. Smoke on the live URL:
   ```bash
   curl -s "https://www.pmcmanagers.com/api/v1/masters/banks?country_code=GB&q=Revolut"
   # → [{"name":"Revolut", ...}]      ← confirms the bank roster auto-upsert ran

   curl -s "https://www.pmcmanagers.com/api/v1/masters/banks?country_code=GB" | python3 -c "import sys,json; print(len(json.load(sys.stdin)),'GB banks')"
   # → 18 GB banks (or more)
   ```
3. **Clean the two duplicate escrow rows** (your 409 cause). Pick one:
   - **UI (easier):** Admin → Money & compliance → Escrow / EMD → red banner → “Cancel extras” next to `BID-2026-TEST2` and `PMC-BID-2026-00048`.
   - **Script:**
     ```bash
     # inside the EB instance (eb ssh) OR a laptop with MONGO_URL set
     cd backend
     python scripts/cleanup_duplicate_escrow_tx.py            # dry run
     python scripts/cleanup_duplicate_escrow_tx.py --apply    # commit
     ```

### Frontend → S3 + CloudFront
Standard sync + CloudFront `/*` invalidation.

### Browser smoke test
- Admin → Escrow institutions → scroll to **Notice ↔ Escrow account routing** → tick a notice → **Apply to 1** → green toast (no HTTP 422).
- Admin → Escrow / EMD → if red banner shown, click **Cancel extras** → banner count drops; recording a new inbound for `PMC-BID-2026-00061` now succeeds.
- `/escrow/register` → step 2 Signatories renders cleanly, phone field stays inside the card.
- `/escrow/register` → step 3 Banking → pick United Kingdom → type **Revolut** → appears in dropdown; type something not listed → **+ Add "<name>"** button → click → success toast + selected.

---

## Rollback
Re-deploy any earlier v52cz revision. All new fields / endpoints / collection flags are additive — no data migration required.
