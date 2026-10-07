# Escrow Institution Module — v51al Scaffold (NOT WIRED)

Shipped as dark code so UI/UX can be reviewed before activation.

## Files
- `backend/routers/escrow_institutions.py` — model, public register/resume/update/submit, admin list/get/decision, institution dashboard.
- `frontend/src/apps/escrow-portal/EscrowInstitutionRegister.jsx` — public 4-step registration (Core → Signatories → Banking → Documents → Submit).
- `frontend/src/apps/escrow-portal/EscrowInstitutionDashboard.jsx` — portal landing with KPI tiles for joint accounts + pending signatures.

## To activate (one future PR):
1. **Backend** — add to `/app/backend/server.py`:
   ```python
   from routers import escrow_institutions
   app.include_router(escrow_institutions.router)
   ```
2. **Frontend routes** — in `/app/frontend/src/App.js`:
   ```jsx
   import EscrowInstitutionRegister from "./apps/escrow-portal/EscrowInstitutionRegister";
   import EscrowInstitutionDashboard from "./apps/escrow-portal/EscrowInstitutionDashboard";
   <Route path="/escrow/register" element={<EscrowInstitutionRegister />} />
   <Route path="/escrow/dashboard" element={<EscrowInstitutionDashboard />} />
   ```
3. **Login page** — add a 4th tile "Escrow Institution" next to Supplier / PMC staff / Administrator.
4. **Admin approval queue** — new tab in Masters → Escrow Institutions (reuses `GET /api/v1/escrow-institutions?status=submitted`).
5. **Joint-account picker** — rewire `EscrowAccountsSection.jsx` so the Escrow officer email becomes a dropdown of approved institutions' signatories (no free-type).
6. **Document uploads** — wire `uploadsApi.presign` + `direct` into Step 4 of the registration form (slots list already defined in `DOC_SLOTS`).

## Not included (deferred to activation PR)
- Magic-link sign flow for one-click officer signatures from email.
- Separate Resend email templates for registration confirmation + decision notice.
- Admin review UI for individual institutions (will reuse the pattern from `RegistrationsPanel.jsx`).

## Audit of what's intentionally NOT connected
- `backend/server.py` — unchanged.
- `App.js` — unchanged.
- `AdminLogin.jsx` / sign-in page — unchanged.
- `EscrowAccountsSection.jsx` — still allows free-type officer emails.

Nothing in the live product references these files yet. Safe to deploy as-is; feature stays dark until the 5 wiring steps above are applied.
