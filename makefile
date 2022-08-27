.PHONY: lint test

lint:
	isort --profile=black mopidy_tidal tests
	black mopidy_tidal tests

test:
	pytest tests/ \
-k "not gt_$$(python --version | sed 's/Python \([0-9]\).\([0-9]*\)\..*/\1_\2/')" \
--cov=mopidy_tidal --cov-report=html --cov-report=term-missing --cov-branch
