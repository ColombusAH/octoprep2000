.PHONY: help install check-node install-uv db-up db-down backend frontend dev test lint clean

NODE_MIN_MAJOR := 20

help:
	@echo "OctoPrep2000 — dev tasks"
	@echo "  make install   — install all deps (pnpm + uv), checking Node >= $(NODE_MIN_MAJOR)"
	@echo "  make db-up     — start local Postgres"
	@echo "  make db-down   — stop local Postgres"
	@echo "  make backend   — run FastAPI backend (port 8000)"
	@echo "  make frontend  — run TanStack Start frontend (port 3000)"
	@echo "  make dev       — run backend + frontend + db together"
	@echo "  make test      — run all tests"
	@echo "  make lint      — lint all packages"

install: check-node install-uv
	pnpm install
	cd packages/backend && PATH="$$HOME/.local/bin:$$PATH" uv sync

check-node:
	@command -v node >/dev/null 2>&1 || { \
		echo "Node.js not found. Install Node >= $(NODE_MIN_MAJOR) (e.g. via nvm: nvm install $(NODE_MIN_MAJOR))."; \
		exit 1; \
	}
	@node -e 'process.exit(parseInt(process.versions.node.split(".")[0], 10) >= $(NODE_MIN_MAJOR) ? 0 : 1)' || { \
		echo "Node $$(node -v) found, but >= $(NODE_MIN_MAJOR) is required. Run: nvm install $(NODE_MIN_MAJOR) && nvm use $(NODE_MIN_MAJOR)"; \
		exit 1; \
	}

install-uv:
	@command -v uv >/dev/null 2>&1 || { \
		echo "uv not found — installing..."; \
		curl -LsSf https://astral.sh/uv/install.sh | sh; \
	}

db-up:
	docker compose up -d db

db-down:
	docker compose down

backend:
	cd packages/backend && uv run uvicorn main:app --reload --host 0.0.0.0 --port 8000

db-migrate:
	cd packages/backend && uv run alembic upgrade head

db-rev:
	cd packages/backend && uv run alembic revision --autogenerate -m "$(m)"

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
