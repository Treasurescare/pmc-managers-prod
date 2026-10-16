# PMC Managers — Frontend v52ca (11 Oct 2026)

## What's in this build
Corrigenda screen (Admin → Corrigenda) — second search bar UX fix:

1. **Live match feedback** — the lower search bar ("Filter THIS notice's
   corrigenda…") now shows a result line under it on every keystroke:
   - Matches: `N of M corrigenda match "<query>"`
   - No hits: amber `No corrigenda match "<query>" — try the corrigendum
     number, a title word, or text from the change description.`
   - New testids: `corr-search-feedback`, `corr-search-empty-hint`.
2. **Zero-corrigenda hint** — when the picked notice has no corrigenda at
   all, an italic hint explains "This notice has no corrigenda yet — publish
   the first one via 'New corrigendum' above." Previously the search box
   looked dead because there was nothing to filter and no feedback.
3. **Filter reset on notice switch** — changing the notice dropdown clears
   the corrigenda filter so a stale query can't hide rows on the new notice.

Also verified in this build (regression from v52bz):
- Withdraw corrigendum dialog opens, validates reason (min 8 chars),
  confirms, and the row moves from Active → Withdrawn immediately
  (ACTIVE 3 → 2, WITHDRAWN 1 → 2 on the test notice).

## Root-cause note (user question: "second search bar not working")
The filter itself was functional. It looked dead because (a) the
default-picked notice had zero corrigenda, so typing changed nothing
visible, and (b) there was no feedback text under the input. Both are now
addressed. If the search still appears dead on **production**, the deployed
frontend is stale — upload this build and invalidate CloudFront `/*`.

## Deploy
- Backend: unchanged from v52bz (`pmc-backend-v52bz.zip`) — no redeploy needed.
- Frontend: sync this zip's contents to the S3 bucket, then invalidate
  CloudFront with `/*`.

File: `pmc-frontend-v52ca-prod-build.zip`
