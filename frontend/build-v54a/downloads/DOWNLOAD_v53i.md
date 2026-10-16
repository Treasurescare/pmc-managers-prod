# PMC Managers — Release v53i (frontend + backend)

## What changed since v53h

### Invited-but-didn't-participate: silent gap fixed
Your report (verbatim): the auction was awarded to `managerspmc@gmail.com`;
the other invitee `info@emeraldcorporates.com` never received any email,
and the auction/bid is not visible on their dashboard with a clear
reference that they were invited.

Two independent gaps were causing that:

**1) Close fan-out skipped non-registered invitees.**
`close_reverse_auction` only emailed registered participants (vendors who
had clicked the invite link and joined the round). Vendors who were
invited but never joined received nothing. Now the close fan-out also
mails every invitation row whose email is not already a participant:

> *"You were invited to **{auction}** ({notice_ref}), but did not register
> for this round. The auction has now closed and will be awarded to another
> bidder. The invitation record stays visible under Reverse auctions in
> your supplier portal for your reference."*

**2) Vendor UI labelled invitees as "lost".**
`/mine` already surfaces every auction a vendor was invited to, but
`_stamp_outcome` marked non-winning vendors as `outcome: "lost"` and the
UI then said *"your bid was not the lowest this round"* — which is wrong
and confusing for a vendor who never bid. The outcome is now:

- `won` — this vendor is the winner.
- `lost` — vendor registered as a participant and did not win.
- `not_participated` — **new**. Vendor was invited but never registered.
  The row now shows: *"You were invited to this auction but did not
  register before it closed. It has been awarded to another bidder."*

So `info@emeraldcorporates.com` will see the auction on their Reverse
auctions page with a clear "invited — did not participate" badge, matching
your request for a reference that they were given the opportunity.

### Award-time backfill (for your existing auction)
The missing emails are already in the past — the close event has fired for
the auction in your screenshot. So the award endpoint now **also** runs
the same fan-out: when you click **Award winner** on the Modular OT row,
every registered loser and every non-registered invitee gets a clean
*"Reverse auction awarded — awarded to another bidder at {price}"* email.
Winner is unchanged (they already get the pipeline flow from v53b/v53g).

## Deploy

1. **Backend** — `pmc-backend-v53i.zip` → Elastic Beanstalk.
2. **Frontend** — `pmc-frontend-v53i-prod-build.zip` → S3 root,
   CloudFront invalidate `/*`.
3. Then award the Modular OT auction — the losers/invitees email fires
   on award too, so `info@emeraldcorporates.com` finally gets a mail about
   it, and both auctions on PMC-NOT-2026-0020 become visible on their
   Reverse auctions page.

## Files touched

- `backend/routers/auction_live.py`
  - `_stamp_outcome` → new `not_participated` outcome.
  - `close_reverse_auction` → mails non-registered invitees too.
  - `award_reverse_auction` → fan-out to losers + non-registered invitees
    (so historical auctions closed before v53i still get the mail).
- `frontend/src/apps/vendor-portal-e/VendorAuctionsE.jsx`
  - New grey "invited — did not participate — awarded to another bidder"
    reference block for `outcome === "not_participated"`.
