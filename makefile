.PHONY: lint test

lint:
	isort --profile=black mopidy_tidal
	black mopidy_tidal

test:
	pytest tests/ --cov=mopidy_tidal --cov-report=html --cov-report=term-missing
