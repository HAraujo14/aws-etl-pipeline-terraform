PYTHON ?= python3
export PYTHONPATH := src

.PHONY: help install lint format test run-local terraform-fmt terraform-validate ci

help:
	@echo "Targets: install lint format test run-local terraform-fmt terraform-validate ci"

install:
	$(PYTHON) -m pip install -r requirements.txt -r requirements-dev.txt

lint:
	ruff check src tests
	black --check src tests

format:
	ruff check --fix src tests
	black src tests

test:
	pytest

run-local:
	$(PYTHON) -m weather_etl run --backend local

terraform-fmt:
	terraform fmt -check -recursive infra

terraform-validate:
	terraform -chdir=infra init -backend=false -input=false
	terraform -chdir=infra validate

ci: lint test terraform-fmt terraform-validate
