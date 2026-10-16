# PMC Managers Limited — Release v50b

## What's fixed
### DPR AI analysis failing with "Not authenticated"
User report: Tender builder → AI-generate from DPR → 20 MB PDF →
"Analyse 1 DPR with AI" → row shows "Not authenticated", toast
"1 DPR(s) failed".

Investigation results (on production):
- `POST /api/v1/tender-pro/dpr/analyze-async` works on production with
  a valid session — verified with a 27 MB payload (HTTP 200, job
  queued). The endpoint, nginx body cap, CloudFront and CSRF all pass.
- "Not authenticated" (HTTP 401) means the browser sent NO auth cookie
  — i.e. the session had lapsed (cookie Max-Age is 24 h) or a stale
  service-worker shell was mid-flight. Other panel calls only LOOK
  fine because their failures are silent.

Fixes (`frontend/src/lib/api.js`):
1. **Stale-session handler** — a response interceptor now catches
   401 "Not authenticated" / "Token expired" on ANY api call and
   redirects once to `/login?expired=1&next=<page>` instead of letting
   each panel show the raw "Not authenticated" string.
2. **Upload timeout raised** — the DPR analyze endpoints (sync + async
   kick) now use a 5-minute axios timeout instead of the 20 s default;
   a 27 MB base64 upload on a slow link exceeded the default and could
   surface as a confusing failure.

## Bundles
* **Frontend: `pmc-frontend-v50b-prod-build.zip`** — deploy this
  (supersedes v50a and everything before).
* **Backend: `pmc-backend-v49y.zip`** — unchanged since last release.

## Deploy
Frontend — S3 + CloudFront: unzip → `aws s3 sync --delete` → invalidate `/*`.

## Verify
1. Hard-refresh once (the new service worker activates), sign in fresh.
2. Tender builder → AI-generate from DPR → pick country → pick the
   master (or tick "build a new master") → upload the 20 MB PDF →
   Analyse. The row should show queued → analyzing → complete.
3. If the session ever lapses again, you are taken to /login with
   "Session expired" instead of a cryptic per-row error.

## Note
If the analysis still fails AFTER the job is accepted (row shows a
backend error rather than "Not authenticated"), send us the job's error
text — that would be the AI-extraction stage, a separate issue.
