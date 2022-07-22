.PHONY: lint

lint:
	isort --profile=black mopidy_tidal
	black mopidy_tidal
