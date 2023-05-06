.PHONY: lint test
POETRY ?= poetry run

format:
	${POETRY} isort --profile=black mopidy_tidal tests
	${POETRY} black mopidy_tidal tests

lint:
	${POETRY} isort --check --profile=black mopidy_tidal tests
	${POETRY} black --check mopidy_tidal tests

test:
	${POETRY} pytest tests/ \
-k "not gt_$$(python3 --version | sed 's/Python \([0-9]\).\([0-9]*\)\..*/\1_\2/')" \
--cov=mopidy_tidal --cov-report=html --cov-report=xml --cov-report=term-missing --cov-branch
