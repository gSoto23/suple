import os
from celery import Celery
from app.core.config import settings

# Determine the Redis broker URL (for dev and prod parity)
# Defaults to localhost for dev environments if not present in env
CELERY_BROKER_URL = os.environ.get("CELERY_BROKER_URL", "redis://localhost:6379/0")

celery_app = Celery(
    "suplementos_worker",
    broker=CELERY_BROKER_URL,
    backend=CELERY_BROKER_URL
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
        timezone=settings.DEFAULT_TIMEZONE,
    enable_utc=True,
)

# Auto-discover tasks in the app.tasks module
celery_app.autodiscover_tasks(["app.tasks.marketing", "app.tasks.meta", "app.tasks.ai_tasks"])
