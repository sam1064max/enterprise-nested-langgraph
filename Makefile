# Makefile for Enterprise Nested LangGraph
#
# Convenience targets for local development. CI uses the equivalent
# direct commands; this file is for ergonomics.

.PHONY: help install sync test test-unit test-integration lint format typecheck coverage clean run all

PYTHON ?= python
UV ?= uv

help:
	@echo "Enterprise Nested LangGraph - development targets"
	@echo "  make install        - Install uv (assumes curl/winget available)"
	@echo "  make sync           - Sync project dependencies"
	@echo "  make test           - Run the full test suite"
	@echo "  make test-unit      - Run unit tests only"
	@echo "  make test-integration - Run integration tests only"
	@echo "  make lint           - Run ruff check"
	@echo "  make format         - Auto-fix lint errors"
	@echo "  make typecheck      - Run mypy"
	@echo "  make coverage       - Run tests with coverage"
	@echo "  make run            - Run the application with a sample query"
	@echo "  make all            - Run lint, typecheck, and test"
	@echo "  make clean          - Remove caches and build artifacts"

install:
	@echo "Install uv via https://github.com/astral-sh/uv"

sync:
	$(UV) sync --all-extras

test:
	$(UV) run pytest -q

test-unit:
	$(UV) run pytest tests/unit -q

test-integration:
	$(UV) run pytest tests/integration -q

lint:
	$(UV) run ruff check .

format:
	$(UV) run ruff check . --fix

typecheck:
	$(UV) run mypy .

coverage:
	$(UV) run pytest --cov --cov-report=term-missing --cov-report=xml

run:
	$(UV) run python app.py "Summarize the latest enterprise AI agent trends for 2026"

all: lint typecheck test

clean:
	rm -rf .pytest_cache .mypy_cache .ruff_cache .coverage coverage.xml htmlcov build dist
	find . -type d -name __pycache__ -exec rm -rf {} +
