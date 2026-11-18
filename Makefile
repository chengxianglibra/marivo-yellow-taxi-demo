.PHONY: setup data-verify semantic-snapshot semantic-check analysis-smoke test lint typecheck verify

VENV_PYTHON := .venv/bin/python
TESTS ?= tests

setup:
	bash scripts/setup.sh

data-verify:
	$(VENV_PYTHON) -m yellow_taxi_demo.data

semantic-snapshot:
	$(VENV_PYTHON) -m yellow_taxi_demo.semantic_snapshot --all

semantic-check:
	$(VENV_PYTHON) -m yellow_taxi_demo.semantic_snapshot
	$(VENV_PYTHON) -m yellow_taxi_demo.semantic_check
	.venv/bin/marivo doctor --semantic

analysis-smoke:
	$(VENV_PYTHON) -m yellow_taxi_demo.analysis_smoke

test:
	$(VENV_PYTHON) -m pytest $(TESTS)

lint:
	$(VENV_PYTHON) -m ruff check yellow_taxi_demo tests

typecheck:
	$(VENV_PYTHON) -m mypy

verify: data-verify semantic-check analysis-smoke test lint typecheck
