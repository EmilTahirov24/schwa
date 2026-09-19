# Build from the repository root:
#   docker build -f packages/api/Dockerfile -t schwa-api .
#   docker run -p 8000:8000 schwa-api
#
# The image carries the model the package ships, so it needs nothing else. Other files can
# be mounted and named instead - SCHWA_TAGGER, SCHWA_LEXICON, SCHWA_CONTEXT - and /v1/info
# says which restorer is running.

FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/README.md packages/core/LICENSE packages/core/
COPY packages/api/pyproject.toml packages/api/
COPY packages/core/schwa packages/core/schwa
COPY packages/api/schwa_api packages/api/schwa_api

RUN uv sync --frozen --no-dev --package schwa-api

FROM python:3.12-slim

RUN useradd --create-home --uid 1000 schwa
WORKDIR /app

COPY --from=build --chown=schwa:schwa /app /app
ENV PATH="/app/.venv/bin:$PATH"

USER schwa
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "schwa_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
