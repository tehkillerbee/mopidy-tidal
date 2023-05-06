.PHONY: lint test install format all system-venv
POETRY ?= poetry run

help:
	@printf "Chose one of install, format, lint or test.\n"

install:
	rm -rf dist
	poetry build
	pip install dist/*.whl

format:
	${POETRY} isort --profile=black mopidy_tidal tests
	${POETRY} black mopidy_tidal tests

lint:
	${POETRY} isort --check --profile=black mopidy_tidal tests
	${POETRY} black --check mopidy_tidal tests

system-venv:
	python -m venv .venv --system-site-packages
	bash -c "source .venv/bin/activate && poetry install"
	@printf "You now need to activate the venv by sourcing the right file, e.g. source .venv/bin/activate\n"


test:
	${POETRY} pytest tests/ \
-k "not gt_$$(python3 --version | sed 's/Python \([0-9]\).\([0-9]*\)\..*/\1_\2/')" \
--cov=mopidy_tidal --cov-report=html --cov-report=xml --cov-report=term-missing --cov-branch
