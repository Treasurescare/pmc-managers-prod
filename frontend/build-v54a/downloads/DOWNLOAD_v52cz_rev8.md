# PMC Managers — Release v52cz rev8

**Date:** 14 Feb 2026
**Scope:** Escrow dup-email guard (hardened everywhere) · signatory dashboard with sidebar + clickable KPIs · bank roster further expanded · (includes everything in rev7 and earlier)

> **Supersedes v52cz rev7.** Deploy rev8 — this is the one bundle you asked for.

---

## What's new in rev8

### 1. Duplicate email now blocked at every entry point
Rev7 blocked `POST /register`. Prod still had three institutions with the same `info@emeraldcorporates.com` because the pre-rev7 backend was deployed. Rev8 additionally blocks:
- `PATCH /escrow-institutions/{iid}` — if the user edits the email to one already belonging to a **different** institution → 409.
- `POST /admin-invite` — if an institution with this email is already `submitted / under_review / approved / rejected` → 409. Only `draft` / `needs_clarification` rows are reused (the normal invite dedupe).
- New public endpoint `GET /api/v1/escrow-institutions/email-available?email=` returns `{available, status?}` so the registration form can flag the duplicate on blur before the user wastes time filling the rest.

> **Note on your three existing duplicate rows for `info@emeraldcorporates.com`:** rev8 won't retroactively delete them. Either reject/approve them from the admin panel so you're left with one canonical record, or ask me and I'll ship a one-shot cleanup script.

### 2. Escrow institution dashboard — vendor-style sidebar + clickable tiles
The previous dashboard was a bare 3-tile page with no navigation. Rev8 ships a full-chrome layout:
- **Left sidebar** (brand-navy, like the vendor portal): Overview · Pending signatures · All transactions · Joint accounts · Institution profile · Sign out.
- **Overview tab**: Joint accounts / Pending signatures / Total transactions KPIs are now **clickable** — clicking jumps straight to the matching tab.
- Each tab renders a titled panel (empty-state copy where there's no data yet).

### 3. Bank roster expanded again — 200+ banks across 20+ countries
Added another ~100 entries incl. India co-op / foreign / NBFC-partner neo rosters (Nubank, Niyo, Fi, Jupiter, slice, RBL, DCB, Dhanlaxmi, CSB, SBM, Jana / Suryoday / Utkarsh / Shivalik / Unity SFB…), UK (Chase UK, Zopa, Atom, Tide, Allica, OakNorth, Investec…), US (Regions, KeyBank, Citizens, M&T, Huntington, SVB, Discover, Current, Dave, SoFi…), DE/FR/UAE/SG/CN/JP/AU/BR/ZA/NG/RU long-tails. Free-text fallback remains for any bank still not listed.

### Carried over (rev7 → rev2)
Everything: ISD phone picker with length validation, Save-as-draft + Previous on every step, country-aware reg-no/tax-id/VAT regex, structured address with cascading state/city, searchable country/state/bank pickers, in-page document viewer, magic-token document endpoint, auto geography & bank bootstrap, blank form auto-generation, bundle picker on bids, Documents tab data-driven, Download all above list.

### Tests
Full targeted suite 15/15 green: rev5 (escrow core model), rev6 (bank master + magic-token file endpoint), rev7 (dup-email + roster size + neobank search).

---

## Files

| File | Purpose |
|---|---|
| [`pmc-backend-v52cz-rev8.zip`](./pmc-backend-v52cz-rev8.zip) | Elastic Beanstalk backend package |
| [`pmc-frontend-v52cz-rev8-prod-build.zip`](./pmc-frontend-v52cz-rev8-prod-build.zip) | S3 / CloudFront static assets |

Backend bootstrap seeds `masters_banks` on first boot. If prod already has an older roster, run `python scripts/seed_banks.py` once to upsert the new rows (idempotent).

## Deployment

### Backend → AWS Elastic Beanstalk
1. Deploy `pmc-backend-v52cz-rev8.zip`.
2. Smoke:
   ```
   curl -s "https://www.pmcmanagers.com/api/v1/escrow-institutions/email-available?email=info@emeraldcorporates.com" | python3 -m json.tool
   # → {"available": false, "status": "submitted"}
   curl -s "https://www.pmcmanagers.com/api/v1/masters/banks?country_code=IN&limit=200" | python3 -c "import sys,json;print(len(json.load(sys.stdin)))"
   # → 34+ (or run seed_banks.py once to top it up)
   ```

### Frontend → S3 + CloudFront
Standard sync + CloudFront `/*` invalidation.

### Browser smoke test
- Register with a used email → "already registered" 409 toast.
- Admin → Escrow institutions → new entries for the same email → 409 on invite.
- Escrow dashboard (post-signin): left sidebar with 5 tabs; clicking a KPI tile jumps to that tab.
- Add banks dropdown in registration (IN): more entries now (Paytm/Jio/Airtel Payments, AU/Ujjivan/Fincare SFB, Deutsche India, HSBC India, Standard Chartered India, Citibank India, Nubank-style neos…).

## Rollback
Re-deploy any earlier v52cz revision. All new endpoints / collections / fields are additive.
