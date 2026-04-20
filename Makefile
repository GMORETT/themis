PYTHONPATH := apps:packages
export PYTHONPATH

.PHONY: help install sync up down logs fmt lint typecheck test ci clean ingest ingest-lgpd ingest-chunk

help: ## Show this help
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  \033[36m%-12s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

install: ## Install dependencies (uv sync)
	uv sync

sync: install ## Alias for install

up: ## Start local infra (postgres, redis, qdrant)
	docker compose up -d

down: ## Stop local infra
	docker compose down

logs: ## Tail infra logs
	docker compose logs -f

fmt: ## Format code (ruff)
	uv run ruff format .
	uv run ruff check --fix .

lint: ## Lint (ruff check + format check)
	uv run ruff check .
	uv run ruff format --check .

typecheck: ## Type check with mypy
	uv run mypy

test: ## Run pytest
	uv run pytest

ci: lint typecheck test ## Run full CI checks locally

clean: ## Remove caches
	rm -rf .venv .mypy_cache .pytest_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true

ingest-lgpd: ## Scrape + normalize LGPD from Planalto (Phase 1A)
	uv run python -m ingestion.cli fetch-lgpd

ingest-chunk: ## Chunk normalized JSONL into retrieval units (Phase 1B)
	uv run python -m ingestion.cli chunk

ingest: ingest-lgpd ingest-chunk ## Run the full ingestion pipeline
	@echo "✓ ingestion pipeline done (Phase 1B scope)"
