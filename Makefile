.PHONY: eval test lint build install

eval:
	python evals/run_evals.py

test:
	cd backend && PYTHONPATH=. ../.venv/bin/python -m pytest tests/ -v

lint:
	cd backend && ../.venv/bin/python -m ruff check . || true
	cd frontend && npm run lint

build:
	cd frontend && npm run build

install:
	pip install -r backend/requirements.txt
	cd frontend && npm install
