.PHONY: setup dev test lint build clean help

PYTHON ?= python
PIP ?= pip
NPM ?= npm

help:
	@echo "ProofPatch Development Commands:"
	@echo "  make setup     - Install backend and frontend dependencies"
	@echo "  make dev-back  - Start FastAPI backend server"
	@echo "  make dev-front - Start Vite frontend server"
	@echo "  make test      - Run all backend and frontend tests"
	@echo "  make lint      - Run code linter and formatting checks"
	@echo "  make build     - Build frontend bundle and package validation"
	@echo "  make clean     - Remove caches and temporary build artifacts"

setup:
	$(PIP) install -e backend
	cd frontend && $(NPM) install

dev-back:
	$(PYTHON) -m uvicorn app.main:app --app-dir backend --reload --port 8000 --host 127.0.0.1

dev-front:
	cd frontend && $(NPM) run dev

test-back:
	$(PYTHON) -m pytest backend/tests -v

test-front:
	cd frontend && $(NPM) test

test: test-back test-front

lint-back:
	$(PYTHON) -m ruff check backend

lint-front:
	cd frontend && $(NPM) run lint

lint: lint-back lint-front

build-front:
	cd frontend && $(NPM) run build

build: build-front

clean:
	rm -rf data/workspaces data/*.db .pytest_cache .ruff_cache frontend/dist frontend/node_modules/.vite
