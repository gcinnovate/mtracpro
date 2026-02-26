.PHONY: install clean py3-compile-check py3-lint py3-import-smoke run-app run-celery-worker run-sync-facilities

install:
	pip install -r requirements/development.txt

clean:
	chmod +x ${PWD}/sh/clean.sh
	./scripts/clean.sh

py3-compile-check:
	python3 -m compileall webapp scripts

py3-lint:
	ruff check webapp scripts

py3-import-smoke:
	python3 scripts/py3_import_smoke.py

run-app:
	python3 -m webapp.main 8383

run-celery-worker:
	celery -A webapp.celery_app:app worker --loglevel=info

run-sync-facilities:
	python3 -m webapp.sync_facilities
