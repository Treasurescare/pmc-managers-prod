# PMC Managers Limited — Release v50c

## What's new
### Tender builder — DPR section headings are now carried through
User request: order the DPR sections as read from the file and use
their real headings as the tender section titles, with a checkbox to
toggle "keep as read / edit before creating".

Behind the scenes the AI pipeline already discovered the real section
headings in order (`sections_blueprint` in the analyze response). The
"Build new master from this DPR" code path, however, was deriving the
titles from the section codes (`dpr-1` → "Dpr 1", `dpr-2` → "Dpr 2"…),
so every freshly-built master lost the real headings.

Fix (`frontend/.../DprGenerateModal.jsx`):
1. When building a new master, the section titles now come from the
   `sections_blueprint` the backend returned — ordered exactly as the
   AI read them from the DPR.
2. Each DPR preview card shows a new panel: a checkbox **"Use the
   DPR's own section headings (N found, in order). Uncheck to edit
   before creating."** When unchecked, every heading becomes an inline
   text input and the edited values flow into the new master on
   "Create AI-drafted TENDERs".
3. The panel is scoped to the "new master" case — when the admin
   picks an existing master, the master's own section titles remain
   authoritative (as before).

Testids: `dpr-use-dpr-headings-<idx>`, `dpr-section-title-<idx>-<i>`.

Service-worker cache bumped to `pmc-shell-v50c-rev1`.

## Bundles
* **Frontend: `pmc-frontend-v50c-prod-build.zip`** — deploy ONLY this
  (supersedes v49r → v50b).
* **Backend: `pmc-backend-v49y.zip`** — unchanged.

## Deploy
Frontend — S3 + CloudFront: unzip → `aws s3 sync --delete` → invalidate `/*`.

Verify:
- Tender builder → AI-generate from DPR → upload PDF → Analyse. The
  DPR's own headings now populate the new master, in order; the
  "Use the DPR's own section headings" checkbox lets you edit them
  before "Create AI-drafted TENDERs".

## Rollback
Frontend v50b. No API or schema changes.
