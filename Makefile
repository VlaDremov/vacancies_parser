PYTHON ?= python3

install:
	$(PYTHON) -m pip install -e '.[dev]'

run-once:
	$(PYTHON) -m app.run_once

backfill:
	$(PYTHON) -m app.backfill --hours 24

validate-sources:
	$(PYTHON) -m app.validate_sources

test:
	$(PYTHON) -m pytest -q
