import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workers.celery_app import celery_app
from models.database import SessionLocal
from models.orm import Trend
from services.trend_discovery import discover_all_trends
from config import settings

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.trend_tasks.discover_trends", bind=True, max_retries=3)
def discover_trends(self):
    """Fetch trends from all sources and persist new ones to the database."""
    config = {
        "reddit_client_id": settings.reddit_client_id,
        "reddit_client_secret": settings.reddit_client_secret,
        "reddit_user_agent": settings.reddit_user_agent,
        "twitter_bearer_token": settings.twitter_bearer_token,
        "tiktok_api_key": settings.tiktok_api_key,
    }
    try:
        trends = discover_all_trends(config)
        db = SessionLocal()
        new_count = 0
        try:
            for t in trends:
                existing = db.query(Trend).filter(
                    Trend.topic == t["topic"],
                    Trend.source == t["source"],
                ).first()
                if not existing:
                    db.add(Trend(
                        source=t["source"],
                        topic=t["topic"],
                        score=t["score"],
                        raw_data=t.get("raw_data", {}),
                    ))
                    new_count += 1
            db.commit()
        finally:
            db.close()
        logger.info(f"Trend discovery: {new_count} new trends saved (total fetched: {len(trends)})")
        return {"fetched": len(trends), "new": new_count}
    except Exception as exc:
        logger.error(f"Trend discovery failed: {exc}")
        raise self.retry(exc=exc, countdown=60)
