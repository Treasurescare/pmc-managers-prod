# PMC Managers — v56v (26 Jun 2026)

Production bundles (upload to your AWS stack):
- Backend  → `pmc-backend-v56v.zip`        → Elastic Beanstalk
- Frontend → `pmc-frontend-v56v-prod-build.zip` → unzip, upload to S3 root → invalidate CloudFront `/*`
- Confirm footer: "Frontend v56v · Backend v56v"

## What's new / fixed in v56v
1. **Admin console responsive (tablet/phone)** — below 1100px the sidebar now
   collapses into an off-canvas drawer with a hamburger + tap-to-close scrim, so
   the content/tables get the full width instead of being squeezed (fixes the
   iPad cut-off). Applied across every admin screen. The old duplicate hamburger
   is suppressed so only one appears.
2. **Dashboard escrow counters** — the ATTENTION row now shows
   "N escrow institutions awaiting review" and "N new escrow accounts this month"
   (both tap through to their screens).
3. **Landing-page filters on mobile** — the Sector / Contract type / Category /
   Country / keyword controls stack into a clean full-width column with proper
   side padding instead of wrapping awkwardly.

Preview-verified (testing_agent iter 109 confirmed the drawer + counters +
stacking; this build also removes the duplicate hamburger). Awaiting your deploy
+ confirmation.
