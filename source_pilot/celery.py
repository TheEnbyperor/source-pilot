import os
import celery

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'source_pilot.settings')

app = celery.Celery('source_pilot')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()
