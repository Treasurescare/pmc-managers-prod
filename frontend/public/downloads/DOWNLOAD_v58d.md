# PMC Managers — v58d (30 Oct 2026)

- Backend  → `pmc-backend-v58d.zip` → Elastic Beanstalk
- Frontend → `pmc-frontend-v58d-prod-build.zip` → S3 root (delete old index.html + static/ first) → CloudFront invalidation `/*`
- Footer must read "Frontend v58d · Backend v58d"

## New since v58c
- "Ask PMC" AI chat assistant on public pages and the supplier portal (answers only).
- Marketing → LinkedIn posts: every newly published tender waits for approval; Approve & post (once LinkedIn is connected) or Post manually.
- "Continue with LinkedIn" sign-in appears automatically once the LinkedIn app keys are added.

## LinkedIn keys (Parameter Store, SecureString)
/pmc/prod/LINKEDIN_CLIENT_ID, /pmc/prod/LINKEDIN_CLIENT_SECRET, /pmc/prod/LINKEDIN_ORG_ID (numeric company page ID)
Authorized redirect URL in the LinkedIn app: https://www.pmcmanagers.com/api/v1/auth/linkedin/callback
