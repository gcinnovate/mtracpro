.PHONY: install clean py3-compile-check

install:
	pip install -r requirements/development.txt

clean:
	chmod +x ${PWD}/sh/clean.sh
	./scripts/clean.sh

py3-compile-check:
	python3 -m compileall webapp scripts
