FROM python:3.13-slim

RUN pip install --no-cache-dir uv

WORKDIR /app

COPY pyproject.toml uv.lock ./
COPY src/ src/
COPY README.md ./

RUN uv sync --frozen --no-dev

ENV MOCK_GMAIL_DB=/data/fixtures.sqlite
VOLUME /data
EXPOSE 8000

# No longer auto-seeds Faker fixture data on start (previously `generate
# --if-missing`) -- callers seed deterministically via POST /admin/messages
# instead (see README's Admin API section). `serve` works fine against a
# missing/empty db: db.connect()/init_schema() create it and its schema
# lazily on first request (server.py's get_conn dependency).
ENTRYPOINT ["sh", "-c", "uv run mock-gmail-api serve --host 0.0.0.0 --port 8000 --db \"$MOCK_GMAIL_DB\""]
