# Build from the repository root:
#   docker build -f packages/api/Dockerfile -t duzelt-api .
#   docker run -p 8000:8000 -v "$PWD/data/processed:/models:ro" \
#     -e DUZELT_LEXICON=/models/lexicon.jsonl -e DUZELT_CONTEXT=/models/context.jsonl duzelt-api
#
# The model files are mounted rather than baked in, so the same image can serve the plain
# lexicon on a small box and the full model where there is room for it.

FROM python:3.12-slim AS build

COPY --from=ghcr.io/astral-sh/uv:latest /uv /usr/local/bin/uv

WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy

COPY pyproject.toml uv.lock ./
COPY packages/core/pyproject.toml packages/core/README.md packages/core/LICENSE packages/core/
COPY packages/api/pyproject.toml packages/api/
COPY packages/core/duzelt packages/core/duzelt
COPY packages/api/duzelt_api packages/api/duzelt_api

RUN uv sync --frozen --no-dev --package duzelt-api

FROM python:3.12-slim

RUN useradd --create-home --uid 1000 duzelt
WORKDIR /app

COPY --from=build --chown=duzelt:duzelt /app /app
ENV PATH="/app/.venv/bin:$PATH"

USER duzelt
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s \
  CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health')"

CMD ["uvicorn", "duzelt_api.main:app", "--host", "0.0.0.0", "--port", "8000"]
