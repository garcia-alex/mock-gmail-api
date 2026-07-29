.PHONY: pre-commit pre-commit-all lint test generate serve docker-build docker-run

pre-commit:
	@git symbolic-ref -q refs/remotes/origin/HEAD >/dev/null || git remote set-head origin -a
	uv run --frozen pre-commit run --files $$(git diff --name-only origin/HEAD...HEAD)

pre-commit-all:
	uv run --frozen pre-commit run --all-files

lint:
	uv run --frozen ruff check .
	uv run --frozen ruff format --check .
	uv run --frozen pyright

test:
	uv run --frozen pytest tests/

generate:
	uv run --frozen mock-gmail-api generate --seed 42 --volume 200 --pitch-ratio 0.3 --db ./fixtures.sqlite

serve:
	uv run --frozen mock-gmail-api serve --db ./fixtures.sqlite

docker-build:
	docker build -t mock-gmail-api .

docker-run:
	docker run --rm -p 8000:8000 -e MOCK_GMAIL_DEV_TOKEN=dev-secret-token mock-gmail-api
