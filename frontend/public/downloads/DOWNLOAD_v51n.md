# PMC Managers — Release v51n (cumulative v50m → v51n)

## Fixes in this build (over v51f)

### v51n — mobile top bar restructure (vendor)
- Hamburger moved to top-LEFT.
- New top-RIGHT cluster: bell icon, avatar circle with company initials (links to Account), and an always-visible Sign out button — no drawer needed.
- Brand subtitle hidden on mobile to make room.
- Sign out also remains at the bottom of the drawer menu.

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
- Backend: `pmc-backend-v51n.zip` → Elastic Beanstalk
  (contains the resend, archive-pdf, combined-pdf and 424 error fixes).
- Frontend: `pmc-frontend-v51n-prod-build.zip` → S3, then CloudFront
  invalidate `/*` (contains the API-client, toast, DocuSign UI and mobile
  CSS fixes).

## Preview-only note
The preview pod's DocuSign sandbox key is expired (`invalid_grant /
issuer_not_found`), so live-DocuSign actions can only fully succeed on
production. On production the fixes themselves are environment-independent.

## v51n addition
Every sign-out (vendor top bar, drawer, avatar menu, admin, staff, legacy dashboard) now lands on the unified /login role-picker page instead of the legacy navy vendor login.

## v51n additions (Tender builder)
- DPR "Document is N chars — deep-dive analysed" technical note no longer shown in the "fields the AI could not extract" warning box (removed from new generations in backend; filtered from display for existing drafts; audit ledger unaffected).
- Cover numbering fixed: default template had cover_no 1,1,2 — now 1,2,3, and any loaded draft is renumbered sequentially, repairing legacy drafts.

## v51n additions (branding scrub)
- Help-centre copy neutralised: no platform/vendor names in user-facing help content.
- Production frontend builds ship with no JS/CSS source maps (source no longer browsable via DevTools).
- Shipped bundle scanned: zero platform-identifying strings (verified by automated scan).

## v51n additions (Help Centre fully wired)
- Topic cards, role tabs, live search and Raise-a-ticket were all dead static links; the page is now driven by the real manual API (/api/v1/meta/help).
- 8 topic cards filter the guide library; role tabs switch supplier vs buyer/staff content; search matches titles, purposes and step text.
- Raise a ticket opens a modal that posts to the real public endpoint (admin sees it under help requests).
- /help/:slug deep links render the matching guide (was a fixed mockup article).
- Dead "Guided tours" section removed.

## v51n additions (Help Centre fixes from your video)
- Topic cards (Signatures, EMD, Evaluation, Account…) no longer show "No guide matches" for suppliers — they now search the entire manual across both audiences, with each guide labelled Suppliers / Buyers & staff.
- Floating "?" help drawer: the dead duplicate drawer embedded in 12 older pages (search box did nothing) is now removed at runtime, leaving the single working drawer with live FAQ filtering.

## v51n additions (Help drawer consistency)
- The floating "?" drawer now searches the same 28-guide manual as the Help Centre (previously only 7 built-in FAQs — searching "tender" gave 1 result there vs 2/13 on the page).
- Quick answers render first, then "From the full manual" guide links (supplier-facing guides ranked first), each linking to its full guide page.
