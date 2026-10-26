# Production fresh-start flush — RUNBOOK

Total reset to "start from no. 1". Deletes ALL transactional + vendor/buyer
data + escrow-operational data + signed DocuSign documents + audit ledger +
uploaded files, AND purges external logins (vendors + buyers). **Keeps** only
the internal PMC team logins, all master/reference data, access-control
settings and reusable templates — so the app still boots.

> You run this against production yourself — the agent has no production access.
> The connection string stays in your environment; never paste it into chat.

## 0. Pick a maintenance window
Low traffic. Anyone mid-action loses in-progress work. External users (vendors
& buyers) will need to re-register afterwards.

## 1. FULL backup first (mandatory)
From a machine that can reach the production MongoDB:
```
mongodump --uri="<PROD_MONGO_URL>" --db="<PROD_DB_NAME>" \
          --out="./prod_backup_$(date +%Y%m%d_%H%M%S)"
```
Restore (if ever needed):
```
mongorestore --uri="<PROD_MONGO_URL>" --drop ./prod_backup_YYYYMMDD_HHMMSS
```

## 2. Run the flush
With the production env values:
```
CONFIRM_FLUSH=YES \
MONGO_URL="<PROD_MONGO_URL>" \
DB_NAME="<PROD_DB_NAME>" \
python3 flush_production.py
```
It backs up every deleted collection + the purged external users to
`./prod_flush_backup_<ts>/` before deleting, then prints per-collection counts.

## 3. Scheduled jobs
Already disabled in `.emergent/crons.yml` (all three set `enabled: false`).
They deploy as "off" with the next frontend/backend release. No code change
needed; endpoints remain but are never scheduled. Re-enable later by flipping
`enabled: true`.

## 4. Verify
- A PMC admin/staff user can log in; admin dashboard loads all-zero.
- Public board shows 0 open notices; search filters still populated (masters OK).
- Escrow institutions pipeline = 0; no vendors/buyers can log in (they re-register).
- `mongosh`: `admin_users` intact; `users` holds only internal (role != vendor/buyer);
  `masters_countries` etc. intact.

## 5. Rollback
Restore from the step-1 `mongodump` with `mongorestore --drop`.

---

## Storage note (no orphaned files)
Uploaded files are stored INLINE in MongoDB (base64 in the `uploads`
collection) in the current pilot build — nothing on disk or S3. Clearing
`uploads` removes the file bytes too, so there are no orphaned files to clean
and no file-path reads that could crash the app. (When you move to S3 in a
later phase, add an S3 bucket cleanup step here.)

## KEPT (app still boots)
admin_users (all PMC staff), users WHERE role NOT IN (vendor, buyer),
app_settings, approval_matrices, permission_matrix, role_master, categories,
contract_types, currencies, sectors, departments, orgs, tenants, companies,
legal_entity_types, emd_masters, taxonomy_nodes, masters_banks,
masters_banks_merge_log, masters_cities, masters_countries,
masters_country_formats, masters_country_licenses, masters_states,
masters_unspsc, auction_invite_templates, boq_templates, tender_templates,
sbd_templates, vendor_templates, rubrics, rating_criteria_sets.

## DELETED (the rest)
users WHERE role IN (vendor, buyer); bids, bid_drafts, payment_transactions,
awards, award_documents, contracts, docusign_envelopes (signed docs), auctions,
reverse_auctions (+bids/invitations/participants), committees, comparison_runs,
scores, boq_submissions, coi_declarations, corrigenda, notices, tenders,
tender_questions, registrations, kyc_cases, vendors + vendor_* (blacklist,
category_requests, esg, licenses, profile_requests, ratings, reviews, watchlist),
packages (work packages), products (catalog), escrow_accounts,
escrow_transactions, escrow_payment_entries, escrow_change_requests,
escrow_notifications, escrow_magic_tokens, escrow_sig_password_resets,
escrow_institutions, escrow_signatories, notifications, audit_events, counters,
cron_runs, uploads (file bytes), meetings, engagements, tickets, help_requests,
chat_messages, contact_enquiries, ai_anomalies, inspections, tasks.
