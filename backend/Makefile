.PHONY: dev install lint format typecheck test migrate revision

VENV := .venv/bin

install:
	uv venv --python 3.12
	uv pip install -e ".[dev]"

dev:
	$(VENV)/uvicorn app.main:app --reload --port 8000

lint:
	$(VENV)/ruff check .
	$(VENV)/ruff format --check .

format:
	$(VENV)/ruff check --fix .
	$(VENV)/ruff format .

typecheck:
	$(VENV)/mypy app

test:
	$(VENV)/pytest

migrate:
	$(VENV)/alembic upgrade head

revision:
	$(VENV)/alembic revision --autogenerate -m "$(m)"
