# Deploying OctoPrep2000 to Railway

OctoPrep2000 deploys as **three services in one Railway project**:

| Service | Source | Builder | Notes |
|---|---|---|---|
| **Postgres** | Railway database plugin | — | provisioned, not built |
| **backend** | `packages/backend` | Nixpacks (Python/uv) | FastAPI + all agents + WS hubs |
| **frontend** | `packages/web-dashboard` | Nixpacks (Node/pnpm) | TanStack Start SSR server |

Each app service ships a `railway.json` (config-as-code) that pins the builder, start command, and healthcheck — so the only manual setup is the **Root Directory** and **environment variables** per service.

> The repo is a pnpm + uv monorepo, but neither app has a workspace **runtime** dependency (`shared-types` is dev-only types). So each service builds standalone from its own package directory.

---

## What was made deploy-ready

- **`DATABASE_URL` scheme coercion** (`config.py`) — Railway injects `postgresql://…`; the async engine needs `postgresql+asyncpg://…`. A validator normalizes it automatically (Alembic re-maps to a sync driver in `migrations/env.py`).
- **Backend `railway.json`** — runs `alembic upgrade head` then `uvicorn` bound to `$PORT`; `/health` healthcheck.
- **Frontend `railway.json`** — `pnpm start` (Nitro server honours `$PORT`); `/` healthcheck.
- **`packages/backend/nixpacks.toml`** — installs `ffmpeg` (needed for video upload).

---

## Prerequisites

- A Railway account + the repo pushed to GitHub (or the Railway CLI).
- Decide on a **provider mode**:
  - **Live**: real `LITELLM_API_KEY` (+ `ELEVENLABS_API_KEY`), or Anthropic fallback.
  - **Demo**: `DEMO_MODE=replay` → zero external API calls (fixtures). Safest for a first deploy.

---

## Step 1 — Create the project + Postgres

Dashboard: **New Project → Deploy PostgreSQL**. This creates a `Postgres` service exposing a `DATABASE_URL` variable you reference below.

CLI:
```bash
railway login
railway init                 # create/select a project
railway add --database postgres
```

## Step 2 — Backend service

1. **New → GitHub Repo** (this repo). In service **Settings → Root Directory**, set `packages/backend`.
2. Railway reads `packages/backend/railway.json` automatically (Nixpacks, start command, `/health` healthcheck).
3. **Variables** (Settings → Variables):

   ```
   DATABASE_URL=${{Postgres.DATABASE_URL}}      # reference — uses the private network
   # --- pick ONE of the two modes ---
   DEMO_MODE=replay                              # demo: no external APIs
   # or live:
   LITELLM_API_KEY=...
   LITELLM_BASE_URL=https://litellm.tikalk.dev/v1
   ELEVENLABS_API_KEY=...
   # optional fallback
   ANTHROPIC_API_KEY=...
   PROVIDER_MODE=auto
   LOG_LEVEL=INFO
   ```

   Use the `${{Postgres.DATABASE_URL}}` **reference** (not a pasted value) so the backend talks to Postgres over Railway's private network.
4. **Generate Domain** (Settings → Networking → Public Networking). Note the URL, e.g. `https://octoprep-backend-production.up.railway.app`.

Migrations run on every deploy (`alembic upgrade head`, idempotent). Watch the deploy log for `uvicorn running` and a green `/health`.

## Step 3 — Frontend service

> ⚠️ **The frontend's backend URL is baked in at BUILD time.** `VITE_BACKEND_URL` / `VITE_WS_URL` are read via `import.meta.env` and compiled into the bundle. They must be set **before the build**, and changing them requires a **redeploy/rebuild**.

1. **New → GitHub Repo** (same repo, second service). **Root Directory** = `packages/web-dashboard`.
2. Railway reads `packages/web-dashboard/railway.json` (Nixpacks Node, `pnpm start`, `/` healthcheck).
3. **Variables** — point at the backend's **public** domain from Step 2:

   ```
   VITE_BACKEND_URL=https://octoprep-backend-production.up.railway.app
   VITE_WS_URL=wss://octoprep-backend-production.up.railway.app
   ```

   Note `wss://` (not `ws://`) — the WebSocket endpoints (`/video-stream`, `/audio-stream`, `/realtime-feedback`) must be secure to match the HTTPS page.
4. **Generate Domain** → this is the public app URL.

CORS is already `allow_origins=["*"]`, so the separate frontend domain works without extra backend config.

---

## Step 4 — Verify

```bash
curl https://<backend-domain>/health        # {"status":"ok"}
curl https://<backend-domain>/config         # confirm demo_mode / provider_mode
open https://<frontend-domain>               # run the /start → record → report flow
```

Full user flow to smoke-test: open the frontend → `/start` → upload `docs/testing/reat-19.2-news-example.pptx` → record → end → `/session/:id/report`. In `DEMO_MODE=replay` the report fills from fixtures.

---

## CLI deploy (alternative to the dashboard)

From each package directory, with a service linked:

```bash
# backend
cd packages/backend && railway up

# frontend
cd packages/web-dashboard && railway up
```

`railway up` reads the local `railway.json`. Set Root Directory / variables in the dashboard first (or via `railway variables --set`).

---

## Notes & gotchas

- **First deploy**: bring up Postgres before the backend, or the migration step fails until `DATABASE_URL` resolves.
- **asyncpg + SSL**: the private `${{Postgres.DATABASE_URL}}` reference does **not** require SSL params — don't append `?sslmode=...` (asyncpg rejects that libpq param).
- **Rebuild on URL change**: editing `VITE_*` vars has no effect until the frontend is redeployed (build-time bake).
- **ffmpeg**: provided by `packages/backend/nixpacks.toml`; only the video-upload path needs it.
- **Keep-warm**: `/health` is cheap and DB-free — fine as the Railway healthcheck and for any external pinger.
- **Scaling**: the backend is a single in-process pub/sub app (no Redis). Keep it at **one replica** — multiple replicas would split WS sessions across processes.
