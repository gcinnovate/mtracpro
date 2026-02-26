.PHONY: install clean py3-compile-check run-app run-celery-worker run-sync-facilities

install:
	pip install -r requirements/development.txt

clean:
	chmod +x ${PWD}/sh/clean.sh
	./scripts/clean.sh

py3-compile-check:
	python3 -m compileall webapp scripts

run-app:
	python3 -m webapp.main

run-celery-worker:
	celery -A webapp.celery_app:app worker --loglevel=info

run-sync-facilities:
	python3 -m webapp.sync_facilities
