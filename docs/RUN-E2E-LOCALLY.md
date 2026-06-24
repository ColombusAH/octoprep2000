# Running OctoPrep2000 End-to-End Locally

This guide walks you through running the **full stack** — Postgres + FastAPI backend + TanStack Start frontend — and driving a complete user flow: **upload a deck → record a rehearsal → end the session → read the scored report**.

For a fast, API-key-free run, jump to [Option B: DEMO_MODE replay](#option-b-demo_mode-replay-no-api-keys).

---

## 1. Prerequisites

Install these before you start:

| Tool | Version | Install |
|---|---|---|
| Node.js | ≥ 20 | `nvm install 20 && nvm use 20` |
| pnpm | ≥ 9 | `corepack enable` (ships with Node) |
| uv | latest | `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Docker | any | for the Postgres container |
| ffmpeg (+ ffprobe) | any | `brew install ffmpeg` (macOS) / `apt-get install ffmpeg` (Linux) |

`ffmpeg`/`ffprobe` are only required for the **uploaded-video** batch path (`POST /sessions/:id/upload-video`). The live-rehearsal path works without it.

A modern Chrome/Edge is recommended for the recording flow (camera + mic + WebSocket).

---

## 2. Install dependencies

From the repo root:

```bash
make install
```

This checks Node ≥ 20, installs pnpm workspaces, and runs `uv sync` in `packages/backend`.

---

## 3. Configure environment

```bash
cp .env.example .env
```

The root `.env` is read by **both** backend and frontend. Two ways to fill it:

- **Live mode** — set real keys (`LITELLM_API_KEY`, `LITELLM_BASE_URL`, and `ELEVENLABS_API_KEY` for STT). Optional fallback: `ANTHROPIC_API_KEY` + `PROVIDER_MODE`. See comments in `.env.example`.
- **Demo/replay mode** — set `DEMO_MODE=replay` and skip the keys entirely (see [Option B](#option-b-demo_mode-replay-no-api-keys)).

Defaults already point at local services:

```
DATABASE_URL=postgresql+asyncpg://octoprep:octoprep@localhost:5432/octoprep
VITE_BACKEND_URL=http://localhost:8000
VITE_WS_URL=ws://localhost:8000
```

---

## 4. Start Postgres

```bash
make db-up
```

Boots `postgres:15` (and pgAdmin at http://localhost:5050, login `admin@octoprep.com` / `octoprep`) via `docker-compose.yml`. The DB has a healthcheck — give it a few seconds.

## 5. Run migrations

Schema is **not** auto-created on boot. Apply Alembic migrations once (and after any pull that adds migrations):

```bash
make db-migrate
```

---

## 6. Run the stack

**One command (recommended)** — starts db + backend + frontend in parallel:

```bash
make dev
```

**Or run each in its own terminal** (handy for readable logs):

```bash
make backend    # FastAPI, http://localhost:8000  (hot-reload)
make frontend   # TanStack Start, http://localhost:3000
```

Verify both are up:

```bash
curl localhost:8000/health     # → {"status":"ok"}
curl localhost:8000/config     # → provider/demo flags; confirm "demo_mode" + "provider_mode"
open http://localhost:3000
```

`GET /config` is the quickest way to confirm which mode the backend booted in (`demo_mode`, `provider_mode`, fallback flags).

---

## 7. End-to-end walkthrough (UI)

1. Open **http://localhost:3000** and go to **`/start`**.
2. Pick a language (EN/HE) and **upload a PPTX deck**. A sample ships in the repo: `docs/testing/reat-19.2-news-example.pptx`. The page waits for the deck to be parsed.
3. Grant **camera + microphone** when prompted, then **start recording** your rehearsal. This opens three WebSockets: video (JPEG frames), audio (PCM), and realtime-feedback (events back to the browser). Talk through a slide or two.
4. **End the session.** This triggers report generation (voice / body / slides / content scoring).
5. You're redirected to **`/session/:id/report`** — timestamps, per-slide feedback, and the 4-vector scorecard.

That exercises the whole pipeline: PPTX agent → live Vision/Audio agents → STT → orchestrator → report.

---

## Option B: DEMO_MODE replay (no API keys)

For a deterministic run with **zero external API calls** — ideal for demos, offline dev, or a quick smoke test.

```bash
# in .env
DEMO_MODE=replay
```

Then `make db-up && make db-migrate && make dev`. The backend swaps live Vision/STT for canned fixtures in `packages/backend/fixtures/` (`audio_events.json`, `vision_events.json`, `slide_findings.json`, …). Run the same [UI walkthrough](#7-end-to-end-walkthrough-ui) — the report fills from fixtures instead of live model output. Confirm with `curl localhost:8000/config` → `"demo_mode": true`.

---

## 8. E2E via the API (no browser)

Useful for scripting/CI. Endpoints (full list in `README.md`):

```bash
# 1. Create a session — returns {session_id, access_token} (rate-limited 5/min/IP)
curl -s -X POST localhost:8000/sessions

# 2. Upload a deck (use the token from step 1)
curl -s -X POST localhost:8000/sessions/$SID/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@docs/testing/reat-19.2-news-example.pptx"

# 3. (Live rehearsal frames/audio go over the WS endpoints — browser only.)

# 4. End the session → triggers report
curl -s -X POST localhost:8000/sessions/$SID/end -H "Authorization: Bearer $TOKEN"

# 5. Read the report
curl -s localhost:8000/sessions/$SID/report -H "Authorization: Bearer $TOKEN"
```

WebSocket routes (`/video-stream`, `/audio-stream`, `/realtime-feedback`) take `?session_id=X&token=Y` and are driven by the browser client. In `DEMO_MODE=replay` the report is populated from fixtures, so steps 1 → 2 → 4 → 5 alone give a full report without streaming.

---

## 9. Tests & lint

```bash
make test    # pytest (backend) + pnpm -r test (frontend)
make lint    # ruff (backend) + tsc (frontend)
```

---

## 10. Troubleshooting

| Symptom | Fix |
|---|---|
| `Node ... required` on `make install` | `nvm install 20 && nvm use 20` |
| Backend can't connect to DB | Is the container up? `make db-up`; check `docker ps`. Wait for healthcheck. |
| `relation ... does not exist` | Run `make db-migrate` — schema isn't auto-created. |
| Video upload fails fast | `ffmpeg`/`ffprobe` not on `PATH` — `brew install ffmpeg`. |
| 429 on `POST /sessions` | Rate limit (5/min/IP). Wait a minute. |
| Live model errors / quota | Set `PROVIDER_MODE=direct` with `ANTHROPIC_API_KEY`, or `DEMO_MODE=replay`. Restart backend. |
| Port 8000/3000 busy | Stop the other process, or change `PORT` / frontend `--port`. |
| Reset DB | `make db-down` (drops container) then `make db-up && make db-migrate`. |

---

## Command cheat-sheet

```bash
make install     # deps (pnpm + uv)
make db-up       # start Postgres (+ pgAdmin :5050)
make db-migrate  # apply migrations
make dev         # db + backend + frontend
make backend     # backend only  (:8000)
make frontend    # frontend only (:3000)
make test        # all tests
make db-down     # stop Postgres
```
