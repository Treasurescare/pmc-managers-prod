# PMC Managers — Release v53q (frontend + backend)

## The real production root cause

Your screenshots prove v53k/m/o are already deployed to production:
- Masters → Staff shows **ESCROW-SIGNER** badges (v53k frontend).
- Escrow institutions page shows the **FIND DUPLICATES** button (v53m).

So why do the dropdowns stay empty? The dropdown source
(`/api/v1/escrow/signatory-pool`) returns:
- `pmc_officers` = every staff with `is_escrow_signatory: true`.
- `institutions[].signatories[]` = each **approved** institution's
  **internally registered signatory roster**.

In your production data:
- Approved institutions (Escrow 4, escrow 2, escrow 1 MY, escrow 1 GB)
  only have a `primary_contact_email` — **no signatories added to their
  internal roster**. Signatories are added by the institution owner from
  the escrow dashboard (`/escrow/me`), not by registering the
  institution itself.

So the escrow-officer dropdown correctly returned 0 for every approved
institution. The "approved officers in Escrow Institutions ≠ signatories
in the escrow pool" confusion is real.

## v53q fixes

### 1. Fallback signatory = primary contact
If an approved institution has NO signatory roster yet, the pool now
synthesises a single fallback entry:
`{name: <legal_name>, email: <primary_contact_email>, designation: "Primary contact (fallback — add formal signatories from the institution dashboard)"}`.

This means every approved institution ALWAYS has at least one email in
the dropdown so you can create / backfill joint accounts and advance
EMD-bearing bids immediately. The institution owner can swap in proper
signatories from their dashboard later; the backfill button will then
refresh the joint account to use the real signatory.

### 2. Magic-link signing now actually emails the officer
`POST /api/v1/escrow/magic-tokens` previously created a token and
returned `{token, portal_url}` — the admin had to copy the URL out
manually. Now it also sends a Resend email to the officer with a
**Review & sign** CTA button pointing at `/escrow/officer/<token>`. The
officer clicks → lands on their officer portal with the token in the
URL → signs every open transaction on that joint account WITHOUT a
password.

Email delivery is soft-fail: if Resend 500s, the token is still
returned and the admin UI auto-copies the link to the clipboard with a
toast containing a manual Copy fallback.

### 3. Admin UI: "Email PMC link" / "Email Escrow link"
Every pending escrow transaction row now has two emerald buttons:
- **Email PMC link** — issues a magic token for the PMC officer on this
  account and emails it.
- **Email Escrow link** — same for the escrow-institution officer.

Hidden once that side has signed. Disabled when the "same email on both
officers" governance warning is active. This replaces the old sign
buttons (which 403'd because the admin's own email isn't on the account)
with the only flow that works in practice: email the officer, officer
signs via the link.

## What you need to do post-deploy

1. Deploy `pmc-backend-v53q.zip` to EB and
   `pmc-frontend-v53q-prod-build.zip` to S3 + CloudFront invalidate `/*`.
2. Delete the duplicate "escrow 1" approved institutions (two rows for
   `info@emeraldcorporates.com`) using the Find Duplicates panel.
3. Open Admin → Escrow / EMD → create a joint account:
   - Institution dropdown now lists Escrow 4, escrow 2, and the single
     surviving escrow 1 row.
   - Escrow-officer dropdown shows the primary contact as a fallback
     entry per institution (until signatories are added).
   - PMC officer dropdown shows your 4 flagged escrow signatories.
4. On any `emd_paid` bid with a pending escrow transaction, click
   **Email Escrow link** to send the signing link, then **Email PMC
   link** to the PMC officer. Both click, both sign, Release unlocks.

## Files touched

Backend
- `routers/escrow.py` — `config` import; `_build_pool` adds primary-contact
  fallback; `issue_magic_token` sends Resend email with Review & sign CTA
  and returns `emailed: true/false` + `officer_email`.

Frontend
- `lib/api.js` — `escrowApi.magicIssue(account_id, officer_email)`.
- `apps/admin-console/escrow/EscrowTransactionsSection.jsx` —
  `onSendSignLink` prop on TransactionRow; two new emerald buttons per
  pending row; `sendSignLink` handler with Copy-link fallback toast
  when Resend fails.
