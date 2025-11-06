.PHONY: test ruff ty lint

test:
	uv run pytest -v

ruff:
	uv run ruff check src
	uv run ruff format --check src

ty:
	uv run ty check src

lint: ruff ty
