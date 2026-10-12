
# PMC Managers — Frontend v52ch (12 Oct 2026)

## What's in this build (quick-win pack #2)

### 1. Sticky 3-column layouts (your Q (g))
Admin **Registrations** and **Vendors** pages now give each column its own
scrollbar: when you click a row, the detail opens **right next to it** —
no more scrolling to the bottom to find it. Implementation:

- `lg:sticky lg:top-6 lg:self-start lg:max-h-[calc(100vh-140px)] lg:overflow-y-auto`
  on both grid columns. Mobile stays stacked (unchanged).
- Classes applied in `RegistrationsPanel.jsx` and `VendorsPanel.jsx`.

### 2. Status pill in Notices tender picker
Picker rows now carry a small chip:
- **"★ Master"** (amber) for seeded/master templates
- **"✏ Draft"** (navy soft) for everything else

Sits next to the EMD chip so you can tell reusable library templates apart
from one-off drafts at a glance. Testid: `notice-tpl-status-<id>`.

## Deploy
- Backend: unchanged (stay on v52cf).
- Frontend: sync this zip to S3, invalidate CloudFront `/*`.
- Supersedes v52cg frontend (includes it).

File: `pmc-frontend-v52ch-prod-build.zip`
