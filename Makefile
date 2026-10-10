.PHONY: setup lint format-check typecheck test preflight eval eval-test run up down compose-check

setup:
	uv sync --dev

lint:
	uv run ruff check .

format-check:
	uv run ruff format --check .

typecheck:
	uv run mypy

test:
	uv run pytest

preflight:
	uv run python -m eval.preflight

eval:
	@test -f eval/run_eval.py || (echo "Evaluation runner arrives in Phase 1."; exit 1)
	uv run python -m eval.run_eval

eval-test:
	uv run python -m eval.run_eval --split test

run:
	@test -f src/unmess/api/main.py || (echo "Application runtime arrives in Phase 4."; exit 1)
	uv run uvicorn unmess.api.main:app --reload

compose-check:
	docker compose config --quiet

up:
	@echo "Starting Phase 0 infrastructure only: Qdrant and Redis."
	@echo "API, worker, and UI are defined under the 'app' profile and are not runnable yet."
	docker compose up -d qdrant redis

down:
	docker compose down
