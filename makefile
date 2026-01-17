dev:
	PYTHONPATH=src uv run uvicorn main:app --reload --app-dir src

test:
	uv run pytest

pre-commit:
	uv run pre-commit run --all-files

ruff:
	uv run ruff check . --fix
	uv run ruff format .