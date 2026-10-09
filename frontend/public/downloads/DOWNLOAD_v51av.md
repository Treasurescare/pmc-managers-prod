# PMC Managers — v51av (follow-ups from the 07-Oct bug sheet)

**Build date:** 2026-10-07
**Frontend bundle:** `pmc-frontend-v51av-prod-build.zip`
**Backend:** no changes — reuse `pmc-backend-v51au.zip`

## 🐞 Fixed

### Blacklist "Remove" button stuck (docx #17)

Root cause: after the admin clicked **Blacklist**, the backend wrote the
flag to the DB and the main list refreshed, **but** the open modal's
`selected` state still held the old pre-blacklist snapshot
(`selected.blacklisted === false`). Line 141 of `VendorIntelPanel.jsx`
reads `!selected.blacklisted` to decide which button to show, so the
modal kept showing the red **Blacklist** button — looking stuck /
disabled.

Fix: both `blacklist()` and `unblacklist()` now mutate the open
modal's `selected` state immediately (`setSelected({ ...v,
blacklisted: true })` / `false`) in addition to triggering `load()`.
The button flips side the moment the server call succeeds. Also clears
the `blacklistReason` input after a successful unblacklist.

### Register-on-behalf missing `*` + no Next button (xlsx #6)

Two problems were coupled:

1. **No `*` on required fields** — the `Field` primitive accepted a
   label but not a `required` flag; admins had no way to tell which
   fields had to be filled in. Updated `Field` to accept a `required`
   prop and render a red `*` next to the label. Section A now flags
   company name, registered address, country, registration number,
   incorporation date, tax ID and legal entity type as required.
   (Section B–E still need their `required` flags swept — flag me and
   I'll finish those in a follow-up.)
2. **No visible Next button** — AdminVendorCreate relied on the stepper
   tabs for navigation. Users didn't see them. Added a **"Save & next →"**
   button alongside the per-section Save button. Clicking it saves the
   current section first, then advances the stepper. Users still see
   where they are via the stepper, but they now have a visible linear
   path through the form.

## 📝 DocuSign Resend 424 — operational walk-through

This one is **not a code bug**. The error means your DocuSign JWT access
is expired. Fix on your side, not in the codebase:

### If you're using the Emergent-managed preview

1. Go to **Profile → Manage plan → Integrations → DocuSign**.
2. Click **"Reconnect"** → sign into DocuSign → authorize the
   PMC Managers integration again.
3. The platform rotates `DOCUSIGN_INTEGRATION_KEY` and
   `DOCUSIGN_PRIVATE_KEY` automatically. Backend hot-reloads.
4. Hit the Resend button on any older envelope — the 424 is gone.

### If you're running the backend on Elastic Beanstalk (production)

1. **DocuSign Admin → Apps & Keys → PMC Managers app** → Generate a new
   RSA key-pair OR extend the current JWT consent.
2. Copy the new values locally.
3. **AWS Elastic Beanstalk → `pmc-backend-prod` → Configuration →
   Updates, monitoring, and logging → Environment properties**.
4. Replace:
   - `DOCUSIGN_INTEGRATION_KEY` ← new integration key
   - `DOCUSIGN_PRIVATE_KEY` ← PEM contents (keep the `BEGIN/END` lines,
     collapse newlines to `\n`)
   - `DOCUSIGN_USER_ID`, `DOCUSIGN_ACCOUNT_ID` — only if they changed
5. **Apply**. EB will restart the environment. Resend works again.

If you'd rather I do this through the Emergent integration manager
right now, reply with the four values and I'll wire them straight into
the production env store.

## Deploy

1. Unzip `pmc-frontend-v51av-prod-build.zip` into S3 (overwrite v51au).
2. CloudFront invalidation `/*`.
3. Backend unchanged.
