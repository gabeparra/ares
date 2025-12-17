.PHONY: run lint test format install clean

run:
	python -m caption_ai

lint:
	ruff check .
	ruff format --check .

format:
	ruff format .

test:
	pytest

install:
	uv sync

clean:
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	rm -rf .pytest_cache
	rm -rf .ruff_cache

