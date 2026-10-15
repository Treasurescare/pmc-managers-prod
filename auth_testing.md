# Auth Testing Playbook

## Current targeted auth regression

1. Unified login at `/login` with role `Escrow Institution` must authenticate a verified account-first user through `POST /api/v1/escrow-accounts/auth/login` and navigate to `/escrow/me`.
2. If that endpoint returns 401/404, unified login must try `POST /api/v1/escrow-signatories/auth/login` for legacy signatories.
3. If the account endpoint returns 403 with `detail.error === "unverified"`, show the backend verification message and do not fall through.
4. Direct `/escrow/login` must retain the same account-first then signatory behavior.
5. Supplier login at `/login` must continue to use `POST /api/v1/vendor/auth/login` and navigate to `/vendor`.

## Smoke credentials

Use only `/app/memory/test_credentials.md`; do not invent credentials or expose password values in reports.
