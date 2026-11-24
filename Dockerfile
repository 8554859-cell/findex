FROM ghcr.io/astral-sh/uv:python3.13-bookworm-slim AS build
WORKDIR /app
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy
COPY pyproject.toml uv.lock ./
RUN uv sync --locked --no-dev --no-install-project
COPY src src
COPY scripts scripts
RUN uv sync --locked --no-dev --no-editable && uv run --no-dev python scripts/download_python_docs.py && uv run --no-dev findex index data/python_docs --out data/index.json --positions
FROM python:3.13-slim-bookworm
WORKDIR /app
RUN useradd --create-home --uid 10001 findex
COPY --from=build /app/.venv /app/.venv
COPY --from=build /app/src /app/src
ENV PYTHONPATH=/app/src
COPY --from=build /app/data /app/data
ENV PATH="/app/.venv/bin:$PATH" INDEX_PATH=/app/data/index.json CORPUS_PATH=/app/data/python_docs
USER findex
EXPOSE 8000
CMD ["sh", "-c", "exec findex serve --host 0.0.0.0 --port ${PORT:-8000}"]
