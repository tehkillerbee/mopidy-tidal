.PHONY: lint test

format:
	isort --profile=black mopidy_tidal tests
	black mopidy_tidal tests

lint:
	isort --check --profile=black mopidy_tidal tests
	black --check mopidy_tidal tests

test:
	pytest tests/ \
-k "not gt_$$(python --version | sed 's/Python \([0-9]\).\([0-9]*\)\..*/\1_\2/')" \
--cov=mopidy_tidal --cov-report=html --cov-report=xml --cov-report=term-missing --cov-branch
