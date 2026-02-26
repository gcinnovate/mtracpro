# Python 3 + Celery Migration: Step 8 CI Guardrails

This document records completion of Step 8 from `docs/python3-celery-migration-plan.md`.

## Scope Completed

Step 8 only:

1. Added CI checks for Python 3 syntax/import regressions.
2. Added lint/upgrade tooling (`ruff`) with Python 3 and import consistency rules.
3. Added a lightweight smoke test for app and Celery imports.

## Changes Made

1. CI workflow added: `.github/workflows/python3-celery-guardrails.yml`
   - Runs on `push` and `pull_request`.
   - Installs dependencies from `production.txt` and installs `ruff`.
   - Runs:
     - `python -m compileall webapp scripts`
     - `ruff check webapp scripts`
     - Python 2 API guard: rejects `.iteritems()`, `xrange()`, `unicode(...)` in `*.py`
     - `python scripts/py3_import_smoke.py`

2. Ruff config added: `.ruff.toml`
   - Syntax/error guardrails:
     - `E9`, `F63`, `F7`, `F82`
   - Pyupgrade guardrails:
     - `UP003`, `UP004`, `UP015`, `UP024`, `UP025`
   - Import consistency guardrail:
     - `TID251` banning top-level `settings`, `app`, and `urls` imports in favor of `webapp.*`.
   - Per-file ignore for existing pre-migration issue:
     - `webapp/app/controllers/queue_mgt_handler.py`: `F821`

3. Smoke test script added: `scripts/py3_import_smoke.py`
   - Stubs `web.database` with an in-memory dummy to avoid DB dependency.
   - Verifies importability of:
     - `webapp.main`
     - `webapp.celery_app`

4. Local developer commands added to `Makefile`
   - `py3-lint`
   - `py3-import-smoke`

5. Autofixed currently-detected pyupgrade issues required by new rules
   - `webapp/app/controllers/tasks.py`
   - `webapp/load_reporters.py`
   - `webapp/update_tree.py`
   - `webapp/upload_rapidpro_reporters_v3.py`

## Validation

Run from repository root:

```bash
python3 -m compileall webapp scripts
ruff check webapp scripts
python3 scripts/py3_import_smoke.py
```

Results:

- Compile check passed (exit code `0`).
- Ruff checks passed.
- Smoke import test passed:
  - `Smoke imports passed: webapp.main and webapp.celery_app`
