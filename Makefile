.PHONY: run dev lint test format install clean rebuild-model init-ares

run:
	python3 manage.py runserver

dev:
	python3 manage.py runserver 0.0.0.0:8000

# Rebuild the Ollama model with updated Modelfile (run on machine with Ollama)
rebuild-model:
	ollama create ares -f Modelfile

# Initialize ARES identity in the database
init-ares:
	python3 init_ares.py --init

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

