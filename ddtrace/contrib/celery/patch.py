# Third party
import celery

# Project
from .app import patch_app
from .task import patch_task


def patch():
    """ patch will add  all available tracing to the celery library """
    setattr(celery, 'Celery', patch_app(celery.Celery))
    setattr(celery, 'Task', patch_task(celery.Task))
