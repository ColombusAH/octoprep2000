# OctoPrep2000 — Developer Guide

## What is this project?

AI-powered presentation coach. Upload a PPTX deck, record a live rehearsal in the browser, get a scored report with timestamps and slide feedback at `/session/:id/report`.

Built for **Tikal Fuse Day — June 24, 2026**.

## Stack

| Layer | Tech |
|---|---|
| Frontend | TanStack Start (React, TypeScript) — port 3000 |
| Backend | Python 3.11+, FastAPI, SQLAlchemy async — port 8000 |
| DB | PostgreSQL 15 (Docker) |
| Vision | GPT-4o Vision via Tikal LiteLLM + Google Cloud Vision |
| STT | ElevenLabs Scribe v1 |
| Monorepo | pnpm workspaces + uv |

## Repo Layout

```
packages/
├── backend/          # FastAPI app, all agents
├── web-dashboard/    # TanStack Start frontend
└── shared-types/     # TypeScript WebSocket payload types
docs/                 # PRD, architecture, playbook, guidelines
```

## Commands

```bash
# Install all dependencies (pnpm + uv)
make install

# Start Postgres in Docker
make db-up

# Stop Postgres
make db-down

# Run backend only (port 8000, hot-reload)
make backend

# Run frontend only (port 3000)
make frontend

# Run everything together (db + backend + frontend)
make dev

# Run DB migrations
make db-migrate

# Create a new migration (m="description")
make db-rev m="add users table"

# Run all tests
make test

# Lint everything
make lint

# Clean build artifacts and caches
make clean
```

## First-time setup

```bash
make install
make db-up
cp .env.example .env   # fill in LITELLM_API_KEY and ELEVENLABS_API_KEY
make dev
```

## Environment variables

Copy `.env.example` to `.env` and fill in:
- `LITELLM_API_KEY` — Tikal LiteLLM key (GPT-4o Vision + STT)
- `ELEVENLABS_API_KEY` — ElevenLabs Scribe v1 (speech-to-text)
- `DEMO_MODE=replay` — swap live Vision/STT for canned fixtures (safe for demo day)

## Key docs

- [`docs/PRD.md`](docs/PRD.md) — product requirements and phase breakdown
- [`docs/TECH-ARCHITECTURE-C4.md`](docs/TECH-ARCHITECTURE-C4.md) — full C4 architecture + sequence diagrams
- [`docs/TIKAL-12-FACTORS-FOR-PRESENTERS.md`](docs/TIKAL-12-FACTORS-FOR-PRESENTERS.md) — Tikal presentation guidelines (used as rubric by the PPTX agent)
- [`docs/MASTER-DOCUMENT.md`](docs/MASTER-DOCUMENT.md) — hackathon plan and team composition

<!-- SPECKIT START -->
Active plan: [`specs/20260624-hebrew-rtl-support/plan.md`](specs/20260624-hebrew-rtl-support/plan.md) — Hebrew
speech support, bilingual session reports, and RTL UI. See also
[`research.md`](specs/20260624-hebrew-rtl-support/research.md) and
[`data-model.md`](specs/20260624-hebrew-rtl-support/data-model.md) in the same directory.
<!-- SPECKIT END -->
