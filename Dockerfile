# Themis — API base image (Phase 0 stub; tuned further in Phase 9 deploy)
FROM python:3.11-slim-bookworm AS base

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    UV_LINK_MODE=copy

# Install uv
COPY --from=ghcr.io/astral-sh/uv:0.5 /uv /uvx /usr/local/bin/

WORKDIR /app

# Dependency layer: copy only lockfile + manifest for better caching
COPY pyproject.toml uv.lock* ./
RUN uv sync --frozen --no-install-project --no-dev

# App layer
COPY apps/ ./apps/
COPY packages/ ./packages/

ENV PATH="/app/.venv/bin:$PATH" \
    PYTHONPATH="/app:/app/apps:/app/packages"

EXPOSE 8000

CMD ["uvicorn", "apps.api.main:app", "--host", "0.0.0.0", "--port", "8000"]
