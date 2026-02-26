# Python 3 + Celery Migration: Step 4 Import Strategy Standardization

This document records completion of Step 4 from `docs/python3-celery-migration-plan.md`, including the package rename fix applied to remove the `web` namespace collision with `web.py`.

## Scope Completed

Step 4 only:

1. Standardized imports to package-absolute `webapp.*` style.
2. Renamed project package directory:
   - `web/` -> `webapp/`
3. Updated top-level entry files:
   - `webapp/main.py`
   - `webapp/urls.py`
   - `webapp/app/controllers/__init__.py`
4. Applied the same import strategy across controllers, tools, and scripts under `webapp/`.

## Import Conventions Applied

1. `from settings ...` -> `from webapp.settings ...`
2. `import settings` -> `import webapp.settings as settings`
3. `from app...` -> `from webapp.app...`
4. `from urls ...` -> `from webapp.urls ...`

Notes:

1. `import web` and `from web.contrib...` remain unchanged because they refer to the external `web.py` framework.
2. The rename removes ambiguity between app package imports and framework imports.

## Validation

Run from repository root:

```bash
python3 -m compileall webapp scripts
```

Result:

- Command completed successfully (exit code `0`).
- Syntax checks pass after import conversion and package rename.

Additional import smoke check:

```bash
python3 -c "import importlib; importlib.import_module('webapp.urls'); importlib.import_module('webapp.main')"
```

Result:

- Import resolution gets past the prior `web` namespace conflict.
- Current failure in this environment is a DB connection error during controller initialization (not an import-path ambiguity).
