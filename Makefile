.PHONY: test run build
test:
	uv run pytest -v --cov=app
run:
	uv run uvicorn app.main:app --reload --port 8000
# Requires Dockerfile (added in T23)
build:
	docker build -t group-chat-digest:dev .
