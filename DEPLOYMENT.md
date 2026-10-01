# Deployment runbook (Render + Neon)

This document describes the **manual** production deployment for the Task Manager
API. The **API runs on Render** (Docker web service); the **database is Neon**
(managed PostgreSQL). Automated deploys from GitHub Actions are planned in
**TM-4** — keep **Auto-Deploy** disabled until that work lands.

## Platform choices

| Component | Platform | Why |
| --------- | -------- | --- |
| **API** | [Render](https://render.com) web service (Docker) | Simple Docker deploy, HTTPS, health checks, free tier |
| **Database** | [Neon](https://neon.tech) PostgreSQL | Managed Postgres already in use for development; persistent storage, no need for a second database on Render |

Render PostgreSQL is **not required** for this project. Neon satisfies the TM-3
managed-database requirement.

## Architecture

```
Internet → Render Web Service (Docker) → Neon PostgreSQL (HTTPS)
              ↑ env: DATABASE_URL, JWT_SECRET, …
              ↑ startup: alembic upgrade head (in start-production.sh)
```

Migrations run in the container **start script** (not Render Pre-Deploy), so this
works on the **free tier** where pre-deploy commands require a paid instance.

## Prerequisites

- Render account
- Neon project with a PostgreSQL database (connection string from the Neon dashboard)
- GitHub repository access (to connect the repo once; deploys are manual for now)
- Local tools optional: `curl`, `jq`

## One-time setup

### 1. Neon database (already provisioned)

This deployment uses an existing **Neon** database rather than creating Postgres
on Render.

1. Open the [Neon console](https://console.neon.tech) and select your project.
2. Copy the **pooled connection string** (recommended for Render — handles
   connection churn when containers restart). If unavailable, use the direct
   connection string.
3. Ensure the URL includes SSL, for example:
   `postgresql://user:password@ep-xxx-pooler.region.aws.neon.tech/neondb?sslmode=require`

Do **not** commit the connection string. Store it only in Render environment
variables (and in local `.env` for development).

Apply migrations once locally, or let the container start script handle them on
first boot:

```bash
# Optional: verify locally before first Render deploy
export DATABASE_URL="your-neon-connection-string"
alembic upgrade head
```

### 2. Create the Render web service

1. **New + → Web Service** (do **not** create Render PostgreSQL).
2. Connect your GitHub repository and select the branch to deploy from.
3. Configure the service:

| Setting | Value |
| ------- | ----- |
| **Name** | e.g. `task-manager-api` |
| **Region** | Any (Neon is remote; pick a Render region close to your Neon region if possible) |
| **Runtime** | **Docker** |
| **Dockerfile path** | `./Dockerfile` |
| **Instance type** | Free or paid (free tier sleeps after inactivity) |

4. **Important:** under **Settings → Build & Deploy**, set **Auto-Deploy** to
   **No** until TM-4 enables CI/CD. Use **Manual Deploy** for each release.

5. Leave **Pre-Deploy Command** empty — migrations run automatically via
   `scripts/start-production.sh` when the container starts (free-tier compatible).

6. Set **Health Check Path**: `/health`

The health endpoint verifies Neon connectivity, not just process liveness.

### 3. Environment variables

In the web service **Environment** tab, add:

| Key | Value | Notes |
| --- | ----- | ----- |
| `DATABASE_URL` | Neon connection string (pooled URL preferred) | Required — from Neon dashboard |
| `JWT_SECRET` | Long random string | Required — generate with `openssl rand -hex 32` |
| `JWT_ALGORITHM` | `HS256` | Optional (default) |
| `JWT_EXPIRE_MINUTES` | `60` | Optional (default) |
| `DEBUG` | `false` | Keep `false` in production |
| `APP_NAME` | `Task Manager API` | Optional |
| `APP_VERSION` | `0.1.0` | Optional |

Render injects `PORT` automatically; the start script binds to it.

**Never** commit real values for `DATABASE_URL` or `JWT_SECRET`. `.env.example`
contains placeholders only.

### 4. First deploy

1. Click **Manual Deploy → Deploy latest commit**.
2. Watch build logs until you see `Running database migrations...` and
   `Starting API server...`.
3. Note the public URL (e.g. `https://task-manager-api.onrender.com`).

Free-tier Render services may take 30–60 seconds to wake after idle sleep. Neon
free tier may also scale to zero; the first request after idle can be slower.

## Verify the live API

Replace `API_URL` with your Render service URL.

```bash
export API_URL=https://your-service.onrender.com

# Health (includes Neon DB check)
curl "$API_URL/health"

# OpenAPI docs (enabled in production)
curl -o /dev/null -w "%{http_code}\n" "$API_URL/docs"

# Register
curl -s -X POST "$API_URL/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"securepass123"}' | jq .

# Log in and capture token
TOKEN=$(curl -s -X POST "$API_URL/api/v1/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"demo@example.com","password":"securepass123"}' \
  | jq -r .data.access_token)

# Create a task (requires JWT)
curl -s -X POST "$API_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"title":"Live deploy test","due_date":"2026-12-01"}' | jq .

# List tasks
curl -s "$API_URL/api/v1/tasks" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

Redeploy the Render web service and repeat the list call to confirm data persists
in Neon (not container storage).

## Subsequent manual releases

1. Merge or commit changes to the deployed branch.
2. In Render: **Manual Deploy → Deploy latest commit**.
3. Container startup runs `alembic upgrade head` automatically against Neon.
4. Confirm `/health` and a smoke test against `/api/v1/tasks`.

## Logs and troubleshooting

| Issue | What to check |
| ----- | ------------- |
| Build fails | Render build logs; ensure `Dockerfile` builds locally |
| Startup fails during migrations | Runtime logs; run `alembic upgrade head` locally against Neon |
| 502 / service unavailable | Render instance still starting (free tier wake); check deploy logs |
| `/health` fails | `DATABASE_URL` correct; Neon project active; SSL params present (`sslmode=require`); DNS/network from Render to Neon |
| 401 on tasks | Register/login first; pass `Authorization: Bearer <token>` |
| 500 on register/login | Password max 72 characters (bcrypt limit); check application logs |
| Slow first request | Neon or Render free tier waking from idle |

View logs: Render web service → **Logs** tab (runtime and deploy).

## Rollback

1. In Render: **Events** → select a previous successful deploy → **Rollback**.
2. If a bad migration shipped, restore the Neon database from a Neon branch
   backup or point-in-time restore before rolling back application code.

Database rollback is not handled by Alembic automatically in production — plan
migrations accordingly.

## Alternative: Render PostgreSQL

You can use Render’s managed Postgres instead of Neon (Internal Database URL,
same region as the web service). This project **uses Neon** to avoid maintaining
two databases and to reuse the existing development database.

## Security notes

- All task routes require authentication (TM-2).
- `/docs` and `/redoc` remain enabled for this assignment; restrict or disable
  in hardened production if needed.
- CORS is not configured yet (no frontend in scope). Add when a browser client
  is introduced.
- Secrets live in Render environment variables only, not in the Docker image or
  git history. Neon credentials stay in the Neon console and Render env vars.

## Out of scope (TM-4)

- GitHub Actions deploy workflow
- Auto-deploy on push to `main`
- Lint/format gates in CI beyond current test job
