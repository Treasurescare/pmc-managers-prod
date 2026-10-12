# PMC Managers — Frontend v52cl (12 Oct 2026)

## What's in this build

### Golden active sidebar tab (user request)
`src/pmc-theme-e.css`: the active left-sidebar item is now an unmistakable
**gold** tab — bright gold gradient (`#e3b93b → #c9a227`), bold dark text,
gold inner edge bar plus a soft gold glow ring so it reads at a glance on
the dark chrome sidebar. Applies to both the explicit `.pmc-side__item--active`
class and the `aria-current="page"` fallback, so every admin page highlights
its tab identically.

Verified live: Billing tab renders gold on /admin/e/billing; Evaluation tab
renders gold on /admin/e/evaluation (pathname auto-detection intact).

## Deploy
- Backend: unchanged (stay on v52ck).
- Frontend: sync this zip to S3, invalidate CloudFront `/*`.
- Supersedes v52ck frontend (includes it).

File: `pmc-frontend-v52cl-prod-build.zip`
