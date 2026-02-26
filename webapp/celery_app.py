from celery import Celery

from webapp.app.controllers.celeryconfig import BROKER_URL

app = Celery("mtrackpro", broker=BROKER_URL)

# Ensure task registration happens via package-absolute import paths.
import webapp.app.controllers.tasks  # noqa: F401
