# PMC Managers — Bug Tracker (asked vs delivered)

Baseline: production (pmcmanagers.com). Source: testing-team bug sheet (24 items).
"Delivered / Current" is filled as each item is re-verified and fixed in preview, then
shipped and handed back to the testing team for sign-off.

Legend — Status: ⬜ open · 🟨 in progress · ✅ fixed (preview, agent-tested) · 🔵 clarification

| # | Module | Reported issue (asked) | Testing-team latest note | Priority | Delivered / Current |
|---|--------|------------------------|--------------------------|----------|---------------------|
| 18 | Admin · Evaluation | Evaluation page won't load — "Something crashed on this screen"; panel fails to render | Generate Award Report button does nothing; no report generated | P0 crash | ⬜ pending |
| 67 | Admin · Audit ledger | Audit ledger page AND masters module won't load — "Something crashed on this screen" | — | P0 crash | ⬜ pending |
| 72 | Escrow officer · Magic-link | Magic-link signature page is crashed | — | P0 crash | ⬜ pending |
| 41 | Escrow | Testing the bids throws an error | — | P0 crash | ⬜ pending |
| 60 | Reverse Auction | "Start" doesn't make the auction go live; invited vendor sees no fields to bid | Start after creating a new auction not working; vendor can't enter bid amount | P0 blocker | ⬜ pending |
| 56 | Tender Builder · AI FILL ALL | "AI FILL ALL" reports success but no sections are drafted | Drafting is not working | P1 | ⬜ pending |
| 15 | Admin · Registration | Approve returns 200 and DB flips to approved, but UI doesn't move the company to Approved / Pending-verify | — | P1 | ⬜ pending |
| 55 | Registration | Some companies can be approved / clarified / rejected; others cannot | Some companies approve, some don't | P1 | ⬜ pending |
| 17 | Admin · DocuSign | After admin signs/dispatches envelope, vendor side stays "submitted/pending" until 2 conditions met | Admin envelope stays SENT; supplier sees "Nothing to sign yet"; award/contract linkage needs verification | P1 | ⬜ pending |
| 44 | Evaluation Rubrics | Bid score always 0 — "technical cutoff not reached", no bid qualifies (expected ~90%) | — | P1 | ⬜ pending |
| 43 | Evaluation Rubrics | Saved weightages don't persist — refresh reverts to defaults | — | P1 | ⬜ pending |
| 45 | BOQ & Contracts | "Contract created successfully" but the contract isn't viewable anywhere in admin | — | P1 | ⬜ pending |
| 23 | Admin · Corrigenda | Public tender page not reflecting active corrigendum (shows old date) | Deadline/key-dates now update; but Corrigenda tab shows "No corrigenda published" and "DOWNLOAD DIFF PDF" returns 404 | P1 | ⬜ pending |
| 37 | Notices · Public page | Key Dates shows "Corrigendum 1" but Corrigenda section says "No corrigenda published on this notice" | — | P1 (dup of 23) | ⬜ pending |
| 36 | Vendor · Submit a Bid | "Start bid" still enabled for closed tenders | Dashboard correctly hides it, but opening the closed bid's View still shows Start bid | P1 | ⬜ pending |
| 13 | Admin · Vendor invite | Invite works but no email is received to continue registration | Not fixed | P1 | ⬜ pending |
| 58 | Product Catalog | Can't disable an existing product — shows an error | Disabling not happening | P1 | ⬜ pending |
| 40 | Notices | Notice timelines are wrong — don't match what was entered at creation | — | P1 | ⬜ pending |
| 69 | Admin · Compliance (Sec D) | Operating-regions country field has no type-ahead; must search manually | — | P2 UX | ⬜ pending |
| 71 | Admin · Events & Alerts | Raw HTML tags (`<p>`, `<b>`) render as plain text in event description | — | P2 UX | ⬜ pending |
| 6 | Admin · Vendors | Required "*" not visible; red "required" text overwhelming; no Next button (must scroll up) | Just add the `*` mark; drop the verbose red "required" text | P2 UX | ⬜ pending |
| 11 | Admin · Vendors | "Operating regions" helper text inside brackets not needed; allow adding fields manually with punctuation | Not fixed | P2 UX | ⬜ pending |
| 46 | Corrigenda | Clarify why the "search notices by ref" bar is needed here (corrigenda search by number/title/summary works) | — | 🔵 clarification | ⬜ pending |

## Proposed fix order
1. **P0 crashes/blockers** (18, 67, 72, 41, 60) — screens that fully break.
2. **P1 core workflow** (56, 15, 55, 17, 44, 43, 45, 23/37, 36, 13, 58, 40).
3. **P2 UX polish** (69, 71, 6, 11) + clarification (46).

Each fix is verified in preview (curl/testing agent) before being marked ✅ and shipped
in the next versioned build for the testing team to re-confirm in production.
