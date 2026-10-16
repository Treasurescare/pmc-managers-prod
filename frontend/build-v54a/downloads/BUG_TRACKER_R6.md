# PMC Managers — Round 6 Bug Tracker (11 Oct 2026)

Source: Test Report "Round 6" (spreadsheet shared by user). Each item is mapped
against recent releases (v52bs → v52bw). Status legend:
- **FIXED** — shipped & test-verified in a named release (may need prod deploy/CloudFront invalidation)
- **RE-VERIFY** — fixed in preview but re-reported; likely stale production build, needs user confirmation
- **NEW** — not yet fixed, queued for next release (v52bx)
- **CLARIFY** — need more info from the reporter

| # | Module | Bug (as reported) | Status | Release / Notes |
|---|--------|-------------------|--------|-----------------|
| 0 | EMD & payments | Pay button does not process EMD payment in Stripe sandbox | FIXED | v52bt — Pay EMD resolves exact bid & opens real Stripe checkout |
| 10 | EMD & Payments | All statuses / All currencies dropdowns unresponsive | FIXED | v52bt — populated from live rows + filtering works |
| 12 | DocuSign | Resend on older bids raises error | FIXED | v52bt (ENVELOPE_DOES_NOT_EXIST→410) + v52bw (UNKNOWN_ENVELOPE_RECIPIENT→410) |
| 17 | Admin DocuSign | Vendor side stays submitted/pending until two conditions met | FIXED | v52bw — both gates removed (bid_id fallback + /refresh endpoint) |
| 28 | Admin-Stakeholder | Stakeholder reports CSV download error | FIXED | v52bs — authenticated blob download (deploy + invalidate!) |
| 30 | Admin-Work packages | Sample CSV required for import testing | FIXED | v52bt — verified header + auth download |
| 31 | Admin-Tender builder | Search results shown below Kind/Master Library | FIXED | v52bw — results banner promoted to top of main pane |
| 32 | Admin-Work packages | Creating a new package auto-redirects to Tender Builder | NEW | Root cause likely PmcLinkPatcher label intercepting "New package" (same class as v52bl Create Notice bug). Fix queued for v52bx |
| 33 | Admin Console | Market menu shows only 4 items; Masters/others below don't open on first attempt | FIXED | v52bt — sidebar unified across all 9 pages (27 items) |
| 34 | Admin-Engagement | Different users on same browser without sign-out keep old session active; permissions mix | NEW | Session cross-contamination — needs token-scoping review; HIGH priority, queued v52bx |
| 35 | Vendor | Categories icon missing; no Services link in UI | FIXED | v52bu — both links restored on every vendor page |
| 37 | Notices/Public tender | Key Dates shows "Corrigendum 1" but Corrigenda section says "No corrigenda published" | RE-VERIFY | Public corrigenda display shipped v52bn/bo; verify on production after deploy + CloudFront invalidation |
| 40 | Notices | Notice timelines wrong vs what was set at creation | RE-VERIFY | Timeline rework shipped v52bo; re-reported — verify on production |
| 41 | escrow | "testing the bids, throwing error" | CLARIFY | Need repro steps: which bid, which action, what error |
| 43 | Set up Evaluation Rubrics | Saved weightage not persisted after page refresh | NEW | Queued v52bx — rubric save/restore |
| 44 | Set up Evaluation Rubrics | Scoring always 0 → "technical cutoff not reached, no bid qualifies" | NEW | Queued v52bx — scoring engine investigation |
| 45 | BOQ & Contracts | Contract created but not viewable | FIXED | v52bw — toast shows contract_ref, row auto-scrolls into view |
| 46 | Corrigenda | Clarify search notices by ref bar; confusion between search bars | CLARIFY/UX | Minor UX: label the search bars; queued low |
| 47 | BOQ & Contracts | View button results shown at bottom | FIXED | v52bw — viewer scrolls into view + Close button |
| 48 | BOQ & Contracts | No export button for template | NEW | Add Export (Excel/PDF) per template — queued v52bx |
| 49 | Corrigenda | Withdraw succeeds but corrigendum still shows in active list | NEW | Queued v52bx — withdrawn items must drop out of active list |
| 52 | Tender Builder | Industry filter not working (Public Works/Construction/PMC shows general industry) | RE-VERIFY | Category-master filter shipped v52bs; re-reported — verify on production after deploy |
| 54 | BOQ & contracts | New BOQ has no Add Line Item/Edit; pagination "1–5 of 5" with 0 rows | RE-VERIFY | Shipped v52bs; re-reported — verify on production after deploy |
| 57 | BOQ & contracts | PDF/Excel export options missing (only Import Excel + View) | NEW | Same as #48 — export template to Excel/PDF, queued v52bx |
| 58 | Product Catalog | Disabling existing product shows error | NEW | Queued v52bx |
| 59 | Reverse Auction | Newly created auction not listed as draft | NEW | Queued v52bx |
| 60 | Reverse Auction | "Start" does not make notice go live | NEW | Queued v52bx |
| 61 | Evaluation | Page crashing | RE-VERIFY | AwardReport crash fixed (rubric guard); re-reported — verify, else NEW |
| 63 | Escrow/EMD | Opacity on edit buttons | FIXED | v52bt — solid navy button |
| 64 | Reverse Auction | Cannot create draft auction; "field required" error despite filled fields | NEW | Queued v52bx — likely field-name mismatch in payload |

## Summary

- **Already fixed (deploy v52bs–v52bw to production + invalidate CloudFront):** #0, 10, 12, 17, 28, 30, 31, 33, 35, 45, 47, 63 — **12 items**
- **Re-verify on production (fixed in preview, re-reported):** #37, 40, 52, 54, 61 — **5 items**
- **New bugs queued for v52bx:** #32, 34, 43, 44, 48, 49, 57, 58, 59, 60, 64 — **11 items**
- **Needs clarification:** #41, 46 — **2 items**

## Proposed v52bx scope (priority order)

1. **P0 — Session security** (#34): old session must not survive a new login on the same browser.
2. **P0 — Reverse Auction blockers** (#64, #59, #60): create-draft field error, draft not listed, Start not going live.
3. **P1 — Evaluation** (#43, #44): rubric weightage persistence + scoring returning 0.
4. **P1 — Corrigenda** (#49): withdrawn corrigendum still active.
5. **P2 — Work packages redirect** (#32): PmcLinkPatcher interception.
6. **P2 — BOQ export** (#48/#57): template export to Excel/PDF.
7. **P2 — Product Catalog** (#58): disable product error.
8. **P3 — UX labels** (#46): label the two corrigenda search bars.
