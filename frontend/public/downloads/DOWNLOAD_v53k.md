# PMC Managers — Release v53k (frontend + backend)

## Blocker fixed — EMD escrow accept had no routable signatories

Your report (verbatim excerpt): "lots of bids are there. but I am not
able to get them to move through the escrow emd … when I chose two
signatories … the name should be from a dropdown. one should not enter.
when I add a staff there has to be an option to either make him
signatory for escrow signoff … we are not able to move ahead at all."

### Why bids were stuck

Joint escrow accounts stored the signatories as **free-text name + email**.
Nothing linked them to:
- a real PMC staff user with the escrow role, OR
- a signatory registered on an approved escrow institution.

So the dual-signature gate had no one to route to and the `emd_paid →
escrow_accepted` step sat open indefinitely.

### What v53k changes

**Staff master gets an "Escrow signatory" flag.** Backend
`StaffCreateIn` / `StaffUpdateIn` + the `admin_users` doc now carry
`is_escrow_signatory`. Masters → Staff shows a checkbox in both the
"New staff" form and the inline edit row. Flagged staff get an
`escrow-signer` badge in the roster.

**New source of truth: `GET /api/v1/escrow/signatory-pool`.** Admin-only.
Returns:
```json
{
  "pmc_officers": [{ "id", "name", "email", "designation" }, …],
  "institutions": [
    { "id", "legal_name",
      "signatories": [{ "name", "email", "designation" }, …] },
    …
  ]
}
```
`pmc_officers` is every active staff member with `is_escrow_signatory=True`.
`institutions` is every escrow institution with status `approved` plus the
signatories registered on it.

**Create-joint-account form is dropdown-driven.** The three previously
free-text fields are now managed-list dropdowns:

| Field | Source |
|---|---|
| **Institution (bank / trustee)** | approved escrow institutions |
| **PMC officer** | staff flagged `is_escrow_signatory` |
| **Escrow-institution officer** | signatories of the chosen institution |

Picking an institution auto-fills `institution` (legal_name) and resets
the escrow-officer selector. Picking either officer auto-fills name,
email, and designation. The admin never types.

If the pool is empty (no flagged staff, or no approved institutions yet)
the form shows a yellow banner telling the admin exactly where to go to
fix it — **Masters → Staff** for PMC officers, **Escrow institutions**
for institutions.

**Edit flow for existing accounts** uses the same dropdowns too, with a
graceful fallback banner when an older account's `institution` legal
name doesn't match any current master row.

### Deploy

1. **Backend** — `pmc-backend-v53k.zip` → Elastic Beanstalk.
2. **Frontend** — `pmc-frontend-v53k-prod-build.zip` → S3 root,
   CloudFront invalidate `/*`.
3. In Masters → Staff, tick **Escrow signatory** on each staff member
   who can co-sign EMD releases (`escrow@pmcmanagers.com`,
   `accounts@pmcmanagers.com`, and anyone else at your discretion).
4. In Escrow institutions, make sure each institution you'll use is
   **approved** and has its signatories filled in.
5. Then create a Joint escrow account — the three dropdowns will be
   populated and the escrow-accept step on each `emd_paid` bid will
   finally have a routable owner.

### Files touched

Backend
- `models/staff_user.py` — `is_escrow_signatory` in create/update models.
- `routers/staff_auth.py` — persists `is_escrow_signatory` on create.
- `routers/escrow.py` — new `GET /signatory-pool` endpoint.

Frontend
- `lib/api.js` — `escrowApi.signatoryPool()`, `escrowInstitutionsApi.list()`.
- `apps/admin-console/escrow/EscrowAccountsSection.jsx` — dropdowns for
  institution + PMC officer + institution officer in both create and edit.
- `apps/admin-console/masters/StaffTab.jsx` — new "Escrow signatory"
  checkbox on create + inline edit; badge on roster.
- `apps/admin-console/MastersPanel.jsx` — threads `is_escrow_signatory`
  through the new-staff state and reset.
