# GNOST developer commands. Run `make help` to list them.
# Override the interpreter with e.g. `make test PYTHON=.venv/bin/python`.

PYTHON ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
PATH_ARG ?= .

.DEFAULT_GOAL := help

.PHONY: help install install-docs test snapshots lint format hooks format-check check \
        docs docs-open docs-clean build clean analyze onboard version

help: ## Show this help
	@grep -E '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-14s\033[0m %s\n", $$1, $$2}'

install: ## Install gnost in editable mode with test and lint tools
	$(PYTHON) -m pip install -e ".[test]" "ruff==0.15.4"

install-docs: ## Install Sphinx and the docs theme
	$(PYTHON) -m pip install -r docs/requirements.txt

test: ## Run the test suite
	$(PYTHON) -m pytest -q

snapshots: ## Regenerate onboard golden snapshots (review the git diff afterwards)
	UPDATE_SNAPSHOTS=1 $(PYTHON) -m pytest -q tests/test_onboard_snapshots.py

lint: ## Lint with ruff (same as CI)
	$(PYTHON) -m ruff check .

format: ## Format code with ruff
	$(PYTHON) -m ruff format gnost tests scripts

hooks: ## Install the git pre-commit hook (.pre-commit-config.yaml)
	$(PYTHON) -m pip install pre-commit
	$(PYTHON) -m pre_commit install

format-check: ## Check formatting without changing files
	$(PYTHON) -m ruff format --check --diff gnost tests scripts

check: lint format-check test ## Run everything CI runs (lint, formatting, tests)

docs: ## Build the Sphinx docs into docs/_build/html
	$(PYTHON) -m sphinx -b html docs docs/_build/html

docs-open: docs ## Build the docs and open them in a browser
	$(PYTHON) -m webbrowser "file://$(CURDIR)/docs/_build/html/index.html"

docs-clean: ## Remove built docs
	rm -rf docs/_build

build: clean ## Build sdist and wheel into dist/
	$(PYTHON) -m pip install -q build
	$(PYTHON) -m build

clean: ## Remove build artifacts and caches
	rm -rf build dist *.egg-info .pytest_cache .ruff_cache docs/_build
	find . -name __pycache__ -type d -not -path "./.venv/*" -prune -exec rm -rf {} +

onboard: ## Run gnost onboard on PATH_ARG (default: .)
	$(PYTHON) -c "from gnost.cli import main; main()" onboard $(PATH_ARG)

analyze: ## Run gnost analyze on PATH_ARG with all analyzers and write reports
	$(PYTHON) -c "from gnost.cli import main; main()" analyze $(PATH_ARG) --parallel -o

version: ## Print the gnost version
	$(PYTHON) -c "import gnost; print(gnost.__version__)"
