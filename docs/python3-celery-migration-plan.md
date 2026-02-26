# Python 3 + Celery Import Compliance Plan

This plan is ordered for implementation so each step can be done independently and validated before moving on.

## Step 1: Baseline and Safety Net
Goal: make changes measurable and prevent regressions.

Actions:
1. Add a repeatable check command for syntax/import viability:
   - `python3 -m compileall webapp scripts`
2. Document current known failures as baseline:
   - `webapp/caramal_reports.py` (Python 2 `print` syntax)
   - `webapp/app/tools/pagination.py` (TabError)
3. Add a short migration note in repo docs explaining that Python 3 module execution is the target.

Exit criteria:
1. Team can run one baseline command and see pass/fail.
2. Known failure list is documented.

## Step 2: Remove Hard Python 3 Syntax Blockers
Goal: unblock Python 3 parsing first.

Actions:
1. Fix `print` statements in `webapp/caramal_reports.py`:
   - `print usage()` -> `print(usage())`
   - `print SQL` -> `print(SQL)`
2. Normalize indentation in `webapp/app/tools/pagination.py` (tabs -> spaces).
3. Fix integer division behavior in pagination helper:
   - replace `/` with `//` where integer pagination math is expected.

Exit criteria:
1. `python3 -m compileall webapp scripts` no longer fails on syntax/indentation.

## Step 3: Replace Python 2 APIs
Goal: remove Python 2-only idioms that fail or behave badly in Python 3.

Actions:
1. Replace `.iteritems()` with `.items()`.
2. Replace `xrange()` with `range()`.
3. Replace `unicode(...)` with `str(...)`.
4. Review remaining Python 2 compatibility branches and simplify where safe.

Priority files:
1. `webapp/app/controllers/tasks.py`
2. `webapp/app/controllers/api.py`
3. `webapp/app/controllers/api3.py`
4. `webapp/app/controllers/api6.py`
5. `webapp/app/controllers/dataentry_handler.py`
6. `webapp/sync_facilities.py`
7. `webapp/fullsync.py`
8. `webapp/parse_kannel_log.py`
9. `webapp/export_reporters.py`
10. `webapp/load_vhtdata.py`
11. `webapp/app/tools/utils.py`

Exit criteria:
1. No Python 2 API usage remains in tracked app scripts.
2. Compile check still passes.

## Step 4: Standardize Import Strategy (Package-Absolute)
Goal: eliminate relative import challenges across app, scripts, and Celery workers.

Actions:
1. Standardize to package-absolute imports rooted at `webapp`:
   - `from settings ...` -> `from webapp.settings ...`
   - `from app...` -> `from webapp.app...`
   - `from urls ...` -> `from webapp.urls ...`
2. Keep local relative imports only for true intra-package modules where appropriate.
3. Update top-level entry files first:
   - `webapp/main.py`
   - `webapp/urls.py`
   - `webapp/app/controllers/__init__.py`
4. Update controllers/tools/scripts consistently after entry files.

Exit criteria:
1. Application imports resolve when run from repository root with Python 3.
2. No dependency on implicit current working directory for imports.

## Step 5: Fix Local Override Imports
Goal: make override modules robust under package execution.

Actions:
1. In `webapp/settings.py`:
   - `from local_settings import *` -> `from .local_settings import *`
2. In `webapp/app/controllers/celeryconfig.py`:
   - `from local_celeryconfig import *` -> `from .local_celeryconfig import *`
3. Verify fallback behavior if local override files are absent.

Exit criteria:
1. Both default config and local override loading work under module imports.

## Step 6: Introduce Dedicated Celery App Entrypoint
Goal: make Celery startup stable and independent of script-relative imports.

Actions:
1. Create a dedicated Celery app module (recommended: `webapp/celery_app.py`).
2. Move/centralize Celery app construction there.
3. Ensure task modules are imported via package paths (`webapp.app.controllers.tasks`).
4. Update worker startup command:
   - from `celery -A tasks worker --loglevel=info`
   - to `celery -A webapp.celery_app:app worker --loglevel=info`
5. Update any supervisor/fabric docs/scripts referencing old worker path.

Exit criteria:
1. Worker starts reliably from repository root.
2. Task discovery/import succeeds without path hacks.

## Step 7: Align Runtime Entry Commands
Goal: run everything in module mode for consistent import resolution.

Actions:
1. Prefer `python3 -m webapp.main` for app startup.
2. For utility scripts under `webapp/`, either:
   - run as modules (`python3 -m webapp.sync_facilities`), or
   - migrate into a script package with package-absolute imports.
3. Update operational docs and automation commands accordingly.

Exit criteria:
1. Startup commands are module-based and reproducible.

## Step 8: Add CI Guardrails
Goal: prevent reintroduction of Python 2/import regressions.

Actions:
1. Add CI step: `python3 -m compileall webapp scripts`.
2. Add lint/upgrade tooling (e.g., `ruff`, `pyupgrade`) with rules for:
   - Python 3 syntax
   - import consistency
3. Add a lightweight smoke test for app import and Celery import.

Exit criteria:
1. CI fails on Python 2 syntax/import regressions.
2. CI validates app and Celery importability.

## Suggested One-at-a-Time Execution Order
1. Step 1
2. Step 2
3. Step 3
4. Step 4
5. Step 5
6. Step 6
7. Step 7
8. Step 8

## Notes for Implementation Sessions
1. Implement one step per PR/change set.
2. Run compile check after each step.
3. Do not mix Celery entrypoint refactor with broad import rewrites in the same change set.
