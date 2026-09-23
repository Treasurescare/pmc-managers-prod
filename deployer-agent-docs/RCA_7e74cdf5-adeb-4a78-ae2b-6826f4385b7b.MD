# RCA — Deploy run 7e74cdf5-adeb-4a78-ae2b-6826f4385b7b (tender-hub-57, v46c)

## Outcome
Build failed at `build_image`. **Source-level fix required — NOT a deployment-manifest issue.** I cannot fix it from the deployer side; it must be changed in the preview/source environment, then re-triggered.

## Failure
- Pipeline step: `build_image` → Cloud Build step #2 `docker-build` exited non-zero.
- The `restore-pip-cache` `CommandException: No URLs matched ... pip-cache.tar.gz` in the error excerpt is a **red herring** (benign cache miss). The real terminal error is downstream in the docker-build step.

## Root cause (evidence-backed)
Cloud Build log tail (from `get_build_logs`):
```
#45 [frontend-build 6/14] COPY frontend/ /app/
#45 ERROR: "/frontend" not found: not found
...
failed to compute cache key: "/frontend" not found: not found
ERROR: build step 2 "gcr.io/cloud-builders/docker" failed: step exited with non-zero status: 1
```

The frontend source IS present in the pulled source (verified in eph sandbox at `/app/scratch/frontend` — `package.json`, `src/`, `build/`, `yarn.lock` all intact). The `COPY frontend/ /app/` in the `frontend-build` stage of `Dockerfile.cloudbuild` nevertheless can't see it because **the source-root `.dockerignore` excludes the `frontend` directory from the Docker build context.**

Verified `.dockerignore` contents (source root, `/app/.dockerignore`):
```
# Never bundle these into the Docker image
.git
.gitignore
.eslintcache
node_modules
frontend        <-- THIS excludes the entire frontend/ dir from the build context
docs
tests
__pycache__
...
build
dist
...
```

Because `frontend` is listed, Docker strips `frontend/` out of the context, so `COPY frontend/ /app/` fails with `"/frontend" not found`. This is a regression: prior successful deploys (last green run 169b9da7, 2026-08-11) built fine, so the bare `frontend` line was added to `.dockerignore` after that.

## Fix (apply in the source / preview environment)
Edit **`/app/.dockerignore`** and **remove the line that reads exactly `frontend`** (the top-level entry that excludes the whole frontend source tree).

- Do NOT remove `node_modules`, `__pycache__`, `.env*`, key/pem entries — those are correct.
- The `build` and `dist` lines are safe to keep: they are top-level patterns and do not match `frontend/build` / `frontend/dist`, and `yarn build` regenerates the output inside the frontend-build stage anyway. Only the bare `frontend` line is the blocker.

Resulting relevant section should look like:
```
node_modules
docs
tests
__pycache__
```
(with `frontend` deleted)

## Verification performed
- eph sandbox confirmed `/app/scratch/frontend/package.json` + `/app/scratch/frontend/src` exist → source is intact; the ONLY reason `COPY frontend/` fails is the `.dockerignore` exclusion.
- Build log confirms the frontend-build stage reached step 6 (`COPY frontend/`) and failed there specifically; earlier steps were cached/succeeded, so no other frontend build problem is in play.
- A full docker build could not be exercised end-to-end in the sandbox (no docker daemon), but the exclusion → missing-context → COPY-failure chain is deterministic and matches the exact build error verbatim.

## Next step
1. Remove the `frontend` line from `.dockerignore` in the source environment.
2. Re-trigger the deploy. `mongo`/`secrets` are preserved; the rebuild will re-pull the corrected source. No manifest changes needed.
