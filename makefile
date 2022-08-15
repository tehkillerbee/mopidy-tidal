.PHONY: lint test

lint:
	isort --profile=black mopidy_tidal tests
	black mopidy_tidal tests

test:
	pytest tests/ --cov=mopidy_tidal --cov-report=html --cov-report=term-missing --cov-branch
