.PHONY: test ruff mypy lint

test:
	uv run pytest -v

ruff:
	uv run ruff check src
	uv run ruff format --check src

mypy:
	uv run mypy src

lint: ruff mypy
