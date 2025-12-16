.PHONY: help setup test lint format build clean

help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

setup: ## Install all dependencies
	uv sync

test: ## Run all tests
	uv run pytest

test-verbose: ## Run tests with verbose output
	uv run pytest -v

test-coverage: ## Run tests with coverage report
	uv run pytest --cov=packages --cov-report=term-missing

lint: ## Run linter (ruff)
	uv run ruff check .

lint-fix: ## Fix linting issues automatically
	uv run ruff check --fix .

format: ## Format code with ruff
	uv run ruff format .

format-check: ## Check code formatting without changes
	uv run ruff format --check .

typecheck: ## Run type checker (mypy)
	uv run mypy packages/

check: lint format-check typecheck ## Run all code quality checks

build: ## Build all packages
	uv build

cli: ## Run the SCP CLI (pass args with ARGS="...")
	uv run scp-cli $(ARGS)

scan: ## Scan a directory for scp.yaml files (use DIR=path)
	uv run scp-cli scan $(DIR)

test-constructor: ## Run constructor package tests
	cd packages/constructor && uv run pytest

lint-constructor: ## Lint constructor package
	cd packages/constructor && uv run ruff check .

clean: ## Clean build artifacts and caches
	rm -rf build/ dist/ *.egg-info/
	rm -rf packages/*/*.egg-info/
	rm -rf .pytest_cache/ packages/*/.pytest_cache/
	rm -rf .ruff_cache/ packages/*/.ruff_cache/
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true

clean-venv: ## Remove virtual environments
	rm -rf .venv/ packages/*/.venv/

clean-all: clean clean-venv ## Full cleanup including venvs
