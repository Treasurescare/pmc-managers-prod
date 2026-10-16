# PMC Managers — Release v51z (cumulative, supersedes v51o–v51y)

## What's new in v51z (built on top of v51y Money-pages crash fix)

### 1. Reverse auction — Email invites now via Resend
Invite panel on each auction row has a new "Email vendors now via Resend"
checkbox (default **on**). When checked, each pasted email is both given
a unique join link AND auto-emailed from the verified pmcmanagers.com
Resend domain, using the default auction-invite template (or a built-in
fallback body if no template is seeded). Un-check it if you want links
only, no email.

### 2. Auction readiness badge
Every Draft auction row now shows a small badge next to the status pill:
  * amber `0/2 participants` / `1/2 participants` while gated
  * emerald `✓ 2/2 ready` once two or more vendors have registered
Backed by a new `participant_count` field on the list endpoint — one
round-trip for the whole table.

### 3. Admin Notices — filter state in URL
Every filter in the Notices filter bar is now reflected in the query
string (`?status=`, `?q=`, `?creator=`, `?from=`, `?to=`, `?templates=`).
Operators can bookmark a search, share it with a colleague, or jump
straight to it from a dashboard pipeline link. Clear wipes all params.

## Deploy
Upload `pmc-frontend-v51z-prod-build.zip` to S3, invalidate CloudFront
`/*`, push `pmc-backend-v51z.zip` to Elastic Beanstalk. No new secrets —
the Resend key you already have is reused.
