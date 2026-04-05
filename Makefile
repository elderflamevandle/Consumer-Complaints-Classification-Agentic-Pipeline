run:
	uv run python -c "from src.config import get_settings; print('runtime ready:', get_settings().groq_base_url)"

seed:
	uv run python scripts/build_dataset.py
	uv run python scripts/seed_vectordb.py

eval:
	uv run python -c "print('Evaluation harness arrives in Phase 6.')"

test:
	uv run pytest -q

lint:
	uv run ruff check .

typecheck:
	uv run mypy src
