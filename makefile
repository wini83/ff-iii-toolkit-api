dev:
	PYTHONPATH=src uv run uvicorn main:app --reload --app-dir src

dev2:
	PYTHONPATH=src uv run uvicorn main:create_production_app --factory --reload --app-dir src

test:
	uv run pytest

cov:
	uv run pytest --cov

commit:
	uv run cz commit

pre:
	uv run pre-commit run --all-files

ruff:
	uv run ruff check . --fix
	uv run ruff format .
	uv run black .