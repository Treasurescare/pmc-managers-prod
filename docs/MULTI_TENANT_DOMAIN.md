# Multi-tenant Domain Setup (CNAME / Custom Domain)

The tender platform supports **three** ways for a tenant (Corporate Client or
Government Department) to reach *their* branded portal:

| Priority | Style                              | Example                            | Tenant field on record |
|----------|------------------------------------|------------------------------------|-------------------------|
| 1a       | Full custom domain (host alias)    | `tenders.acme.com`                 | `host_alias`            |
| 1b       | CNAME subdomain of PMC apex        | `acme.pmcmanagers.com`             | `subdomain`             |
| 2 (legacy)| Query string                       | `pmcmanagers.com/?tenant=ACME`     | `code`                  |

Backends resolve tenants via
`GET /api/v1/tenants/by-host?host=<hostname>` — the frontend hook
`useTenantSkin` calls this on mount before falling back to `?tenant=CODE`.

## Set up a new tenant

1. Admin console → **Masters → Tenants → Add Tenant**
   Provide `code`, `name`, `kind`, and optionally set:
   * **subdomain** — e.g. `acme` (must be unique)
   * **host_alias** — e.g. `tenders.acme.com` (must be unique, lowercase)
   * **branding_color** — hex e.g. `#0b1e3f`
2. Point DNS.  Two possible flavours:
   * **CNAME subdomain** — client creates a CNAME record `acme → app.pmcmanagers.com`
     (or wherever the Emergent deployment is hosted).
   * **Custom domain** — client sets an ALIAS/CNAME record for their apex or
     sub-domain to point at the PMC frontend. Then set `host_alias` to that
     hostname on the tenant record.
3. TLS — Emergent-managed edge auto-issues a certificate via Let's Encrypt
   for any hostname routed to it. No manual cert install needed for
   `*.pmcmanagers.com`. For a custom apex (e.g. `tenders.acme.com`) the
   client must complete an ACME `HTTP-01` domain-verify — Emergent will
   surface the challenge token; forward it to the client.

## Notes for engineers

* `routers/tenants.py::tenant_by_host` treats hostnames case-insensitively,
  strips ports, and rejects reserved labels like `www`, `api`, `admin`,
  `preview`, `staging`, and the current preview slug.
* Frontend cache lives in `sessionStorage.pmc.tenant`. It bakes in the
  resolved hostname so switching subdomains never leaks the previous
  tenant's palette across a tab.
* Old `?tenant=CODE` URLs continue to work — they hit the same public
  endpoint (`/api/v1/tenants/public/{code}`) as a fallback.
