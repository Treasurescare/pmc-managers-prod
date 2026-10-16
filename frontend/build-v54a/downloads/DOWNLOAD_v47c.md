# v47c — Vendor confirmatory emails for every action (backend-only deploy)

## Why you saw no emails
They were never implemented for vendor actions — only staff got transition emails. v47b added bidder stage-transition emails; v47c closes the remaining gaps so **every vendor action gets a confirmatory email**.

## Vendor emails now sent (all from `admin@mail.pmcmanagers.com`)

| Vendor action | Email | When |
|---|---|---|
| Submit a bid | **Bid received — {bid_ref}** (price, status, EMD due + **Pay EMD securely** button when EMD applies) | Immediately on submission |
| EMD payment succeeds | **EMD payment received — {bid_ref}** (amount, payment reference) | Stripe webhook / status poll — fires exactly once (idempotent guard) |
| EMD refunded by admin | **EMD refunded — {bid_ref}** (amount + reason) | On refund action |
| Withdraw a bid | **Bid withdrawn — {bid_ref}** | Immediately |
| Change password | **Your vendor password was changed** (security notice with UTC timestamp + "contact us if not you") | Immediately |
| Submit registration | Registration submitted | Already existed (unchanged) |
| Bid transitions | Stage emails (approved / cleared / on-hold / awarded / rejected) | From v47b |

All sends are fire-and-forget and wrapped so a mail outage can never break the underlying action.

## Verified on preview
- Bid submission → HTTP 200 + confirmation email fired (see backend log, Resend message IDs).
- Syntax + import checks pass on all touched files (`payments.py`, `bids.py`, `vendor_auth.py`, `notify.py`).

## Deploy
**Backend-only** — no frontend changes in v47c. Upload `pmc-backend-v47b.zip` first (if not already), then `pmc-backend-v47c.zip` directly over it; v47c includes everything from v47b/v47a/v46z/v46y.

After EB restarts, test live: sign in as a vendor → submit a bid → the bidder's inbox should receive "Bid received" within ~30 s. Pay the EMD via Stripe test card → "EMD payment received" follows.

## Reminder: EB env-var check
`FRONTEND_URL=https://www.pmcmanagers.com` must be set on EB or the Pay-EMD button in emails will point at the wrong host.
