.PHONY: run dashboard seed eval test lint typecheck

run:
	uv run python scripts/tasks.py run

dashboard:
	uv run python scripts/tasks.py dashboard

seed:
	uv run python scripts/tasks.py seed

eval:
	uv run python scripts/tasks.py eval

test:
	uv run python scripts/tasks.py test

lint:
	uv run python scripts/tasks.py lint

typecheck:
	uv run python scripts/tasks.py typecheck
