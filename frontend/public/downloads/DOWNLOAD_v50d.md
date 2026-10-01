# PMC Managers Limited — Release v50d

## What's fixed
### DPR section-headings panel was invisible when a master template was picked
User report: the "Use the DPR's own section headings (N found, in
order)…" panel does not appear.

Root cause: v50c only rendered the panel when NO master was selected
(`!p.masterId`) AND the deep-dive blueprint existed. When you pick a
master in step 2, the analyze call uses the template-aware path — the
AI fills the master's own sections and no blueprint is returned — so
the panel had nothing to key on and stayed hidden.

Fix (`DprGenerateModal.jsx`):
- The headings panel now appears in BOTH flows:
  - **New master from DPR** → "Use the DPR's own section headings
    (N found, in order). Uncheck to edit before creating."
  - **Existing master picked** → "Keep the master template's section
    headings (N). Uncheck to edit them for this tender only."
- In both cases, unchecking reveals one editable input per heading,
  and the edited values flow into the created tender on
  "Create AI-drafted TENDERs" (master flow: titles overridden for this
  tender only — the saved master template itself is not modified).
- Sections remain in the exact order read from the DPR (new-master)
  or defined in the master (existing master).

Testids: `dpr-headings-panel-<idx>`, `dpr-use-dpr-headings-<idx>`,
`dpr-section-title-<idx>-<i>`.

Service-worker cache bumped to `pmc-shell-v50d-rev1`.

## Bundles
* **Frontend: `pmc-frontend-v50d-prod-build.zip`** — deploy ONLY this.
* **Backend: `pmc-backend-v49y.zip`** — unchanged.

## Deploy
Frontend — S3 + CloudFront: unzip → `aws s3 sync --delete` → invalidate `/*`.

Verify:
- Tender builder → AI-generate from DPR → pick a master → upload →
  Analyse → the preview card now shows the headings panel with the
  keep/edit checkbox in BOTH master and new-master flows.

## Rollback
Frontend v50c. No API or schema changes.
