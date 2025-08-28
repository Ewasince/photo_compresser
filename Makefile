PYTHON_VERSION := python3.12
DEPLOY_DIR := .deploy
CHECKED_FILES := $(shell git ls-files "*.py")
PYTEST_ARGS := --cov
PYTEST_REPORT_ARGS :=  --cov-report=xml:coverage.xml

.PHONY: install
install:
	@git submodule init && git submodule update --remote
	@uv sync
	@uv run pre-commit install

.PHONY: lint.mypy
lint.mypy:
	@uv run mypy

.PHONY: lint.ruff
lint.ruff:
	@uv run ruff check . --fix

.PHONY: test.pytest
test.pytest:
	@uv run pytest $(PYTEST_ARGS) -- tests

.PHONY: test.coverage
test.coverage:
	@uv run pytest $(PYTEST_ARGS) $(PYTEST_REPORT_ARGS) -- tests

.PHONY: pre-commit-all
pre-commit-all:
	@uv run pre-commit run --all-files

.PHONY: align_code
align_code:
	uv run ruff format .

.PHONY: start_langflow
start_langflow:
	docker compose -f docker/docker-compose.yml up
