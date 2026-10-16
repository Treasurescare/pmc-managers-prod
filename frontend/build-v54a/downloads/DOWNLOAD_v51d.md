# PMC Managers — Release v51d (cumulative v50m → v51d)

## Fixes in this build (over v51b)

### DocuSign admin console — the five "dead button" bugs
- **Reassign & save** now works end-to-end (the API client was missing
  reassignEnvelope / archiveEnvelope / unarchiveEnvelope in v51b, so every
  click threw a silent TypeError in the browser).
- **Error toasts render again app-wide** — showApiError had been using
  require("sonner") which loaded a second CJS copy of the toast store that
  was never mounted; every API failure was silent. Fixed with an ESM
  top-level import.
- **Resend** no longer 502s on embedded envelopes — the backend was calling
  _recipient_view with 4 of 6 required args. Fixed, with a one-off repair
  pass that stamps client_user_id onto older envelopes.
- **Duplicate "Archive"** removed — the amber button is now "Save PDF"
  (mirror signed PDF into PMC storage); the slate "Archive" hides the
  envelope from vendor Signatures pages. Archived rows show as a light
  warm-grey band with a dark ARCHIVED chip and a ⟲ Restore button.
- **Save PDF 403 "CSRF token missing or invalid"** fixed — archive-pdf is
  now Bearer-auth like the rest of the router (cookie CSRF was blocked
  inside the preview iframe / SameSite=Lax contexts).
- **Print / Download fragility** — admin combined-pdf now serves the
  PMC-storage copy first when one exists, so once you have "Save PDF"'d
  an envelope its signed PDF stays downloadable even if DocuSign is
  unreachable.

### Upstream error visibility
- All DocuSign upstream failures now return HTTP 424 with an explicit
  JSON reason. (The AWS gateway rewrites every 5xx response body into a
  generic HTML error page, which is why on-screen toasts previously only
  showed a bare "Request failed with status code 502".)
- Blob download handlers unwrap JSON error bodies so toasts show the
  real server message, not "Something went wrong".

### Mobile global guards (every page, ≤767px)
- Login, landing and hero inputs can never extend past the viewport.
- Mobile hamburger header is **frozen** (position:fixed) with body
  padding so content doesn't slide underneath.
- Fixed bottom tab-bar clearance applied to every page (not just vendor
  dashboards) — the last buttons are no longer hidden behind the menu.
- Tender listing + content wraps get 12px side padding so cards don't
  sit flush with the screen edge.

## Deploy
- Backend: `pmc-backend-v51d.zip` → Elastic Beanstalk
  (contains the resend, archive-pdf, combined-pdf and 424 error fixes).
- Frontend: `pmc-frontend-v51d-prod-build.zip` → S3, then CloudFront
  invalidate `/*` (contains the API-client, toast, DocuSign UI and mobile
  CSS fixes).

## Preview-only note
The preview pod's DocuSign sandbox key is expired (`invalid_grant /
issuer_not_found`), so live-DocuSign actions can only fully succeed on
production. On production the fixes themselves are environment-independent.
