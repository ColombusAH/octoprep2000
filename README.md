# OctoPrep2000

AI-powered presentation coach. Upload deck → record live → get scored report at `/session/:id/report`.

Built for **Tikal Fuse Day — June 24, 2026**.

## Architecture

Single FastAPI process (all agents = `asyncio` tasks) + TanStack Start frontend + PostgreSQL. Pub/sub in-process. See `docs/TECH-ARCHITECTURE-C4.md` for full C4 model.

| Layer | Tech |
|---|---|
| Frontend | TanStack Start (React, TypeScript), Spec it |
| Backend | Python 3.11+, FastAPI, Agno, SQLAlchemy async, asyncpg |
| DB | PostgreSQL 15 |
| Vision | GPT-4o Vision via Tikal LiteLLM (semantic posture/gestures) + Google Cloud Vision face_detection (deterministic eye contact / smile / tilt — see `agents/face_detection.py`) |
| STT | ElevenLabs Scribe v1 |
| PPTX | python-pptx |
| Monorepo | pnpm workspaces + uv |
| Host | Railway (Phase 3 bonus) |

## Repo Layout

```
packages/
├── backend/          # FastAPI, all agents
├── web-dashboard/    # TanStack Start
└── shared-types/     # TS WS payload types
docs/                 # PRD, C4, Playbook, 12-factors
```

## Quick Start

```bash
# 1. Install deps
make install

# 2. Start Postgres
make db-up

# 3. Copy env
cp .env.example .env  # fill LITELLM_API_KEY + ELEVENLABS_API_KEY

# 4. Run both
make dev
# backend: http://localhost:8000
# frontend: http://localhost:3000
```

## Spec-Kit Setup (one-time, after pulling main)

This repo now uses [spec-kit](https://github.com/tikalk/agentic-sdlc-spec-kit) (see PR [#1](https://github.com/ColombusAH/octoprep2000/pull/1)). After pulling `main`, every dev needs to do this once:

```bash
# 1. Install uv (if you don't have it)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 2. Install the spec-kit CLI
uv tool install agentic-sdlc-specify-cli --from git+https://github.com/tikalk/agentic-sdlc-spec-kit.git

# 3. Verify installation
specify check

# 4. Inside the project, wire up your coding agent (claude, cursor-agent, codex, opencode, ...)
specify integration use <your coding agent>
```

After that, restart/run your agent and the `specify`, `plan`, `implement`, `clarify`, etc. commands should be available.

> If you use a coding agent not listed above, ping Oryam.

## Phases

- **P1** (first 2h, hackathon day): PPTX upload + audio + STT + simple report
- **P2**: 4-vector scorecard (voice/body/slides/content) + lock/unlock
- **P3** (bonus): live toasts (toggle), Railway deploy, Chrome Extension, PDF export

## Endpoints

| Method | Route | Purpose |
|---|---|---|
| GET | `/health` | Liveness for Railway keep-warm |
| POST | `/sessions` | Create session, returns `{session_id, access_token}` (rate-limited 5/min/IP) |
| GET | `/sessions/:id` | Status |
| POST | `/sessions/:id/upload` | PPTX upload |
| POST | `/sessions/:id/end` | End session, triggers report |
| GET | `/sessions/:id/report` | View report (auth: access_token OR share_token) |
| POST | `/sessions/:id/report/share` | Generate share link |
| WS | `/video-stream?session_id=X&token=Y` | Browser → backend (JPEG) |
| WS | `/audio-stream?session_id=X&token=Y` | Browser → backend (PCM) |
| WS | `/realtime-feedback?session_id=X&token=Y` | Backend → browser (events) |

## Demo-Day Hardening

- `/health` keep-warm
- `DEMO_MODE=replay` swaps live Vision/STT for canned fixtures (`packages/backend/fixtures/`)
- WS auto-reconnect (exp backoff 1–8s)
- `POST /sessions` rate-limited via slowapi
- VideoEvent inserts batched (1s OR N=20)

## Docs

- `docs/PRD.md` — product requirements
- `docs/TECH-ARCHITECTURE-C4.md` — full C4 + sequence diagrams
- `docs/PRESENTATION-SKILLS-PLAYBOOK.md` — PPTX agent rubric
- `docs/12-factors.md` — Tikal full-stack methodology guidance
- `docs/MASTER-DOCUMENT.md` — hackathon plan + team comp
