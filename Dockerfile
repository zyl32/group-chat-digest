# syntax=docker/dockerfile:1.7
# Single-stage production image for the Group Chat Digest service.
# Slim base + non-root `appuser` runtime for a small, hardened image.

FROM python:3.12-slim

WORKDIR /app

# Install uv via pip (binary wheel, no extra Python deps). PyPI is reachable
# from CN networks while ghcr.io (used by COPY --from=ghcr.io/astral-sh/uv)
# frequently stalls in this region. `--no-cache-dir` keeps the image small.
RUN pip install --no-cache-dir uv

# Create a non-root user for runtime security.
# python:3.12-slim has no built-in `python` user, so we add `appuser` (uid 1000).
RUN groupadd --system --gid 1000 appuser && \
    useradd --system --uid 1000 --gid appuser --home-dir /app --shell /usr/sbin/nologin appuser

# Copy dependency manifests first to maximize layer-cache reuse.
COPY pyproject.toml uv.lock ./

# Sync production dependencies only (no dev extras, lockfile must match).
# pyproject.toml uses [project.optional-dependencies] (PEP 621 extras), so
# omitting `--extra dev` means pytest et al. are NOT installed. `--frozen`
# forbids re-resolution and fails fast if uv.lock is out of date.
RUN uv sync --frozen --no-install-project

# Copy application, scripts, run config, and bundled mock data.
COPY app/ ./app/
COPY scripts/ ./scripts/
COPY run/ ./run/
COPY data/ ./data/

# Ensure the non-root user can write the SQLite DB + uploads.
RUN mkdir -p data/db data/uploads && chmod 0777 data/db data/uploads

ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=8000
# uv would try to write `.cache/uv` under /app; point it at /tmp instead.
ENV UV_CACHE_DIR=/tmp/uv-cache
EXPOSE 8000

USER appuser

# Call the venv's uvicorn directly to avoid `uv run` re-resolving on every
# start (the venv is already populated by `uv sync` above).
# Use shell form so $PORT can be overridden by the runtime environment
# (e.g. Hugging Face Spaces may set PORT=7860; local docker defaults to 8000).
CMD ["sh", "-c", ".venv/bin/uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
