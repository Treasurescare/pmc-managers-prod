# Production fresh-start flush — RUNBOOK

Mirrors the final **preview** reset. Deletes all transactional + vendor /
registration / KYC + escrow-operational data (incl. work packages, catalog
products, escrow institutions & signatories, audit ledger). **Keeps** admin &
user logins, all master/reference data, access-control settings and reusable
templates, so the app still boots.

> You run this against production yourself — the agent has no production access.
> The connection string stays in your environment; never paste it into chat.

## 0. Pick a maintenance window
Do it at low traffic. Anyone mid-action will lose in-progress work. Optionally
show a maintenance banner / pause writes.

## 1. FULL backup first (mandatory)
From a machine that can reach the production MongoDB:
```
mongodump --uri="<PROD_MONGO_URL>" --db="<PROD_DB_NAME>" \
          --out="./prod_backup_$(date +%Y%m%d_%H%M%S)"
```
Keep this safe. Restore (if ever needed):
```
mongorestore --uri="<PROD_MONGO_URL>" --drop \
             ./prod_backup_YYYYMMDD_HHMMSS
```

## 2. Dry run (see what WOULD change — no deletes)
Open a Mongo shell and compare collection names against the KEEP list in
`flush_production.py`. Anything not in KEEP will be cleared.

## 3. Run the flush
With the production backend's own env values:
```
CONFIRM_FLUSH=YES \
MONGO_URL="<PROD_MONGO_URL>" \
DB_NAME="<PROD_DB_NAME>" \
python3 flush_production.py
```
The script backs up every deleted collection to `./prod_flush_backup_<ts>/`
before deleting, and prints per-collection counts + a total.

## 4. Verify
- Admin can log in; dashboard loads with all-zero stats.
- Public board shows 0 open notices; search filters still populated (masters OK).
- Escrow institutions pipeline = 0.
- `mongosh`: spot-check `admin_users`, `users`, `masters_countries` are intact.

## 5. If anything looks wrong
Restore from the step-1 `mongodump` with `mongorestore --drop`.

---

## KEPT (app still boots)
admin_users, users, app_settings, approval_matrices, permission_matrix,
role_master, categories, contract_types, currencies, sectors, departments,
orgs, tenants, companies, legal_entity_types, emd_masters, taxonomy_nodes,
masters_banks, masters_banks_merge_log, masters_cities, masters_countries,
masters_country_formats, masters_country_licenses, masters_states,
masters_unspsc, auction_invite_templates, boq_templates, tender_templates,
sbd_templates, vendor_templates, rubrics, rating_criteria_sets.

## DELETED (the rest)
bids, bid_drafts, payment_transactions, awards, award_documents, contracts,
docusign_envelopes, auctions, reverse_auctions (+bids/invitations/participants),
committees, comparison_runs, scores, boq_submissions, coi_declarations,
corrigenda, notices, tenders, tender_questions, registrations, kyc_cases,
vendors + vendor_* (blacklist, category_requests, esg, licenses,
profile_requests, ratings, reviews, watchlist), packages (work packages),
products (catalog), escrow_accounts, escrow_transactions, escrow_payment_entries,
escrow_change_requests, escrow_notifications, escrow_magic_tokens,
escrow_sig_password_resets, escrow_institutions, escrow_signatories,
notifications, audit_events, counters, cron_runs, uploads, meetings,
engagements, tickets, help_requests, chat_messages, contact_enquiries,
ai_anomalies, inspections, tasks.
