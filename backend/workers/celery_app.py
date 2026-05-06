from celery import Celery
from celery.schedules import crontab
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from config import settings

celery_app = Celery(
    "social_automation",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=[
        "workers.trend_tasks",
        "workers.content_tasks",
        "workers.publish_tasks",
        "workers.analytics_tasks",
    ],
)

celery_app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
)

# Celery Beat periodic schedule
celery_app.conf.beat_schedule = {
    "discover-trends-every-6h": {
        "task": "workers.trend_tasks.discover_trends",
        "schedule": crontab(minute=0, hour="*/6"),
    },
    "check-scheduled-posts-every-minute": {
        "task": "workers.publish_tasks.publish_scheduled_posts",
        "schedule": crontab(minute="*/1"),
    },
    "refresh-analytics-every-hour": {
        "task": "workers.analytics_tasks.refresh_all_analytics",
        "schedule": crontab(minute=30),
    },
}
