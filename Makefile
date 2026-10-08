.PHONY: install test lint run demo clean

install:
	pip install -e ".[dev]"

test:
	pytest --cov=contratalupa --cov-report=term-missing

lint:
	ruff check contratalupa tests

run:
	uvicorn contratalupa.main:app --reload --port 8000

demo:
	python -m contratalupa.cli demo

clean:
	rm -rf .pytest_cache .ruff_cache .coverage htmlcov
