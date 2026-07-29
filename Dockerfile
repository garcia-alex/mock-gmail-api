FROM python:3.13-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ src/
COPY README.md ./

RUN uv sync --frozen --no-dev

ENV MOCK_GMAIL_DB=/data/fixtures.sqlite
ENV MOCK_GMAIL_SEED=42
VOLUME /data
EXPOSE 8000

# Same image works whether or not a fixture volume is mounted:
# `--if-missing` regenerates the fixture DB only if /data/fixtures.sqlite
# isn't already there (e.g. from a persisted named volume), then serves it.
ENTRYPOINT ["sh", "-c", "uv run mock-gmail-api generate --if-missing --seed \"$MOCK_GMAIL_SEED\" --db \"$MOCK_GMAIL_DB\" && uv run mock-gmail-api serve --host 0.0.0.0 --port 8000 --db \"$MOCK_GMAIL_DB\""]
