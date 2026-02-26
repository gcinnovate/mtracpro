# Python 3 + Celery Migration: Step 6 Dedicated Celery Entrypoint

This document records completion of Step 6 from `docs/python3-celery-migration-plan.md`.

## Scope Completed

Step 6 only:

1. Added a dedicated Celery app entrypoint module at `webapp/celery_app.py`.
2. Centralized Celery app construction in that module.
3. Ensured task module import via package path (`webapp.app.controllers.tasks`).
4. Updated worker startup reference from `celery -A tasks worker --loglevel=info` to `celery -A webapp.celery_app:app worker --loglevel=info`.

## Changes Made

1. `webapp/celery_app.py`
   - Added Celery app creation:
     - `app = Celery("mtrackpro", broker=BROKER_URL)`
   - Imports task module using package-absolute path for task registration:
     - `import webapp.app.controllers.tasks`

2. `webapp/app/controllers/tasks.py`
   - Removed in-module Celery app construction.
   - Switched to importing the centralized app:
     - `from webapp.celery_app import app`
   - Updated the worker command comment to:
     - `celery -A webapp.celery_app:app worker --loglevel=info`

## Validation

Run from repository root:

```bash
python3 -m compileall webapp scripts
```

Result:

- Command completed successfully (exit code `0`).
- `webapp/celery_app.py` and updated `webapp/app/controllers/tasks.py` compile successfully.
