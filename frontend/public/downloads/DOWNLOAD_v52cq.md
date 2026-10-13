# PMC Managers · v52cq Release Notes (rev 3 — AL2023 Docker port fix)

**Build date:** 13 Oct 2026
**Rev:** 3 (fixes "ELB health is failing" on AL2023 Docker)

---

## Why your second deploy failed with ELB health failing

The rev-2 bundle built and ran the container successfully (EB events said
"Environment update completed successfully" and "New application version
was deployed"), but the Application Load Balancer couldn't reach the
container's `/health` endpoint on port 80. Health: Severe.

**Root cause.** On the **Docker on AL2023** platform, Elastic Beanstalk
**does not run a host-side nginx reverse proxy** (that was a feature of
the older Amazon Linux 2 Docker platform). The container must bind
directly to the port the ELB forwards traffic to — which is port 80 by
default. Rev 2 bound gunicorn to port 8001 with an `EXPOSE 8001`, so the
instance's port 80 had nothing listening on it, and every ALB health
check timed out.

## What rev 3 changes

| File | Change |
|---|---|
| `Dockerfile` | gunicorn now binds to `0.0.0.0:80`, `EXPOSE 80`, healthcheck hits `http://localhost:80/health`. |
| `.ebextensions/01-healthcheck.config` | ALB target group now uses `/health` on port 80 with 15 s interval, 2 healthy / 5 unhealthy thresholds. |
| `docker-compose.yml` | Local dev now maps `8080` on host → `80` in container so it matches EB. |

Nothing else changed — all v52cp/v52cq app-level features remain.

---

## Download links (rev 3)

| Bundle | URL |
|---|---|
| Backend (Docker on AL2023) | https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-backend-v52cq.zip |
| Frontend | https://pmc-forest-green.preview.emergentagent.com/downloads/pmc-frontend-v52cq-prod-build.zip |

---

## Deploy sequence

1. Re-download `pmc-backend-v52cq.zip` (rev 3).
2. In EB console → `pmc-backend-prod` → **Upload and deploy** → pick the new zip.
3. Expected events within ~2–3 min:
   - "Environment update completed successfully"
   - Health transitions **Severe → Info → Ok** (not Degraded, not Severe)
   - EB logs show `[bg-bootstrap] seeded masters_unspsc rows=158464` only on first boot after the Mongo collections are empty.

### Smoke test
```bash
API=https://api.YOUR-DOMAIN
curl -s $API/health                                   # → {"ok":true,"service":"pmc-tender-v2-api",...}
curl -s $API/api/v1/masters/countries | jq 'length'   # → 250
curl -s "$API/api/v1/masters/unspsc/public/search?q=biogas&limit=3" | jq .
```

---

## If ELB health still fails

Check EB **Logs → Request Logs → Full logs**, then look at:
- `/var/log/eb-engine.log` for Docker build / run errors
- `/var/log/eb-docker/containers/eb-current-app/*` for gunicorn stderr. 
  Expected startup lines:
  ```
  [INFO] Starting gunicorn 23.x
  [INFO] Listening at: http://0.0.0.0:80
  [INFO] Booting worker with pid: ...
  ```
  If you don't see "Listening at: http://0.0.0.0:80", something's wrong
  with the env — most commonly `MONGO_URL` not set, which causes gunicorn
  workers to crash on import.

### Env var checklist on EB console
Required under **Configuration → Updates, monitoring, and logging →
Environment properties**:
- `MONGO_URL` (full MongoDB connection string)
- `DB_NAME` (e.g. `pmc_v2`)
- `JWT_SECRET`
- `STRIPE_API_KEY`
- `STRIPE_WEBHOOK_SECRET`
- `LLM_API_KEY`
- `RESEND_API_KEY`
- `LOCAL_DEV=0`

---

## v52cq app-level features (unchanged across revs)

- **"Preview as bidder ↗"** amber button on every draft notice (admin console).
- **Create Notice from Tender Builder** carries country / budget / currency / EMD; drops submission deadline; shows amber "Documents from the linked tender" panel; primary document now optional.
- **"Sometimes 422"** when saving tenders fixed (SectionBlock + TenderTemplateIn relaxed).
- Public /tenders cards show **EMD + Country**.
- Carried from v52cm/cn/co: full 158k UNSPSC + 250 countries + 150k cities + country licenses masters, Section D UNSPSC multi-picker, KZ licence block gated, Masters → Country Licenses CRUD, Masters → Geography viewer with license coverage overlay.
