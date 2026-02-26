# mTracpro
The mTrac RapidPro version

## Runtime Commands (Python 3 Module Mode)

Run from repository root:

```bash
python3 -m webapp.main
celery -A webapp.celery_app:app worker --loglevel=info
python3 -m webapp.sync_facilities
```
