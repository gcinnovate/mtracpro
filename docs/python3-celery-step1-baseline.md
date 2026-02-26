# Python 3 + Celery Migration: Step 1 Baseline

This document records the Step 1 safety net and the current baseline failures.

## Baseline Check Command

Run from repository root:

```bash
make py3-compile-check
```

This executes:

```bash
python3 -m compileall webapp scripts
```

## Current Baseline Failures (Step 1)

The compile/import viability check currently fails on:

1. `webapp/caramal_reports.py`
   - Python 2 `print` syntax (`print usage()`)
2. `webapp/app/tools/pagination.py`
   - `TabError` due to inconsistent tabs/spaces indentation

## Migration Runtime Target

The Python 3 migration target is module-based execution so imports resolve consistently from repo root, for example:

```bash
python3 -m webapp.main
```
