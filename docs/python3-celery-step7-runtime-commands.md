# Python 3 + Celery Migration: Step 7 Runtime Entry Commands

This document records completion of Step 7 from `docs/python3-celery-migration-plan.md`.

## Scope Completed

Step 7 only:

1. Standardized runtime command references to module mode for app startup.
2. Added module-mode command for utility execution under `webapp/`.
3. Updated operational docs and automation commands accordingly.

## Changes Made

1. `Makefile`
   - Added `run-app`:
     - `python3 -m webapp.main`
   - Added `run-celery-worker`:
     - `celery -A webapp.celery_app:app worker --loglevel=info`
   - Added `run-sync-facilities`:
     - `python3 -m webapp.sync_facilities`

2. `README.md`
   - Added a "Runtime Commands (Python 3 Module Mode)" section documenting:
     - `python3 -m webapp.main`
     - `celery -A webapp.celery_app:app worker --loglevel=info`
     - `python3 -m webapp.sync_facilities`

## Validation

Run from repository root:

```bash
python3 -m compileall webapp scripts
```

Result:

- Command completed successfully (exit code `0`).
- Runtime command updates do not introduce syntax regressions.
