SHELL := /bin/bash

.PHONY: setup dev clean migrate test check css-build

setup:
	bash scripts/setup.sh

dev:
	bash scripts/dev.sh

clean:
	bash scripts/clean.sh

migrate:
	. .venv/bin/activate && python manage.py migrate --noinput

test:
	. .venv/bin/activate && python manage.py test

check:
	. .venv/bin/activate && python manage.py check

css-build:
	npm run build
