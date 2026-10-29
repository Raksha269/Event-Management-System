import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "ems.settings")
app = Celery("ems")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()
