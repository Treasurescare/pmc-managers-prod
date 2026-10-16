# PMC Managers — Release v52v (frontend + backend)

## What changed since v52u

### 1. Reverse auction join flow — fix + explain
- **Fixed:** `VendorAuctionsE.jsx` was linking rows to `/auction/<id>` instead
  of `/vendor/auction/<id>`, which hit the public catch-all and sent the
  vendor to the pmcmanagers.com home. Links now target the correct room.
- **New nav tab:** Vendor sidebar gets a dedicated **Reverse auctions** item
  (`/vendor/auctions`) under **My bids**.
- **How the flow actually works (the "logic" you asked about):**
  * Reverse auctions are a different animal to sealed-bid tenders.
    A tender notice → "Submit a bid" is the sealed-bid flow (one price,
    one chance). A reverse auction is a **live Dutch auction** — multiple
    rounds, bidders drop their price in real time, anti-snipe clock.
  * You go into the live auction room via **My bids → Reverse auctions →
    Enter** (shown when status is `live`). The row's "View details"
    label switches to "Enter" when the room is open.
  * In the room you see: countdown, current lowest, floor price, minimum
    decrement, and the leader's masked alias. You bid an amount lower than
    the current lowest by at least the minimum decrement, and not below
    the floor. New lowest resets the anti-snipe timer.
  * If you were invited via email, the token binds the invite to the
    invited email **exactly** — if you were signed in as a different
    vendor account, the page refused to accept. Sign out, sign in as the
    invited email, click Accept & join.

### 2. Shared Created-by + Created-from + Created-to filter — 9 panels
- New reusable `components/CreatorDateFilterBar.jsx` (native `type="date"`
  min/max guards so an invalid range is physically unpickable; "Created by"
  is a datalist contains-match).
- Wired into: **Work packages · Vendor requests · Bidding ops · Escrow EMD ·
  Evaluation · L1 comparison · Awards · Reverse auctions · DocuSign**
  (plus Vendors). Each panel filters its already-fetched rows via a
  `useMemo` + `matchCreatorDate(filters)` predicate, so empty filters are
  a no-op.

### 3. Backend `created_by_email` / `created_from` / `created_to` query params
- Added to these list endpoints so the shared filter can be pushed to the
  DB on large datasets:
  * `GET /api/v1/bids` (filters `vendor_email` + `created_at`)
  * `GET /api/v1/notices/admin/all` (filters `created_by_email` + `created_at`)
  * `GET /api/v1/packages` (filters `created_by_email` + `created_at`)
- Existing shared endpoints that already supported server-side filters
  (Audit ledger, Billing, Escrow institutions, Notices public) are
  unchanged.

## Deploy

1. **Backend** — upload `pmc-backend-v52v.zip` to Elastic Beanstalk
   (Dockerfile at root; `.env` and `docker-compose.yml` excluded; AL2023
   Docker contract).
2. **Frontend** — unzip `pmc-frontend-v52v-prod-build.zip` to your S3
   bucket root (overwrite). CloudFront → invalidation `/*`.
3. Hard-reload the admin console and the vendor sidebar — all 9 panels
   now show the Created-by/From/To bar, and vendors see the new
   **Reverse auctions** nav item.
