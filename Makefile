.PHONY: help install db-up db-down backend frontend dev test lint clean

help:
	@echo "OctoPrep2000 — dev tasks"
	@echo "  make install   — install all deps (pnpm + uv)"
	@echo "  make db-up     — start local Postgres"
	@echo "  make db-down   — stop local Postgres"
	@echo "  make backend   — run FastAPI backend (port 8000)"
	@echo "  make frontend  — run TanStack Start frontend (port 3000)"
	@echo "  make dev       — run backend + frontend + db together"
	@echo "  make test      — run all tests"
	@echo "  make lint      — lint all packages"

install:
	pnpm install
	cd packages/backend && uv sync

db-up:
	docker compose up -d db

db-down:
	docker compose down

backend:
	cd packages/backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

frontend:
	pnpm --filter @octoprep/web-dashboard dev

dev: db-up
	pnpm -r --parallel run dev

test:
	cd packages/backend && uv run pytest
	pnpm -r run test

lint:
	cd packages/backend && uv run ruff check .
	pnpm -r run lint

clean:
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type d -name .venv -exec rm -rf {} +
	rm -rf packages/*/dist packages/*/.output packages/*/node_modules node_modules
