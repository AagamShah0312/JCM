"""
Celery application configuration for the judicial backend.
"""
import os

from celery import Celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'judicial_backend.settings')

app = Celery('judicial_backend')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Ensure Django setup inside worker processes
app.conf.update(
    worker_hijack_root_logger=False,
)
