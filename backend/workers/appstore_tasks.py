"""
App Store Intelligence Celery tasks.

Beat schedule (registered in celery_app.py):
  refresh-store-data-daily: daily at 05:00 UTC
"""
from __future__ import annotations

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workers.celery_app import celery_app
from models.database import SessionLocal
from models.orm import App

logger = logging.getLogger(__name__)

# Threshold: if rating drops more than this, fire an urgent alert
RATING_DROP_THRESHOLD = 0.3


@celery_app.task(name="workers.appstore_tasks.refresh_store_data", bind=True, max_retries=2)
def refresh_store_data(self, app_id: int | None = None):
    """Refresh App Store / Play Store data for one app (or all active apps).

    If app_id is provided, refreshes only that app.
    If called without app_id (by Beat), refreshes all active apps.
    """
    db = SessionLocal()
    try:
        from services.appstore_scraper import refresh_app_store_data

        query = db.query(App).filter(App.is_active == True)
        if app_id:
            query = query.filter(App.id == app_id)

        apps = query.all()
        results = []

        for app in apps:
            if not app.app_store_url and not app.bundle_id:
                continue  # nothing to scrape

            previous_rating = (app.raw_store_data or {}).get("rating")
            try:
                new_data = refresh_app_store_data(app)
                app.raw_store_data = new_data
                db.commit()

                new_rating = new_data.get("rating")
                result = {"app_id": app.id, "name": app.name, "rating": new_rating}

                # Rating drop alert
                if (
                    previous_rating is not None
                    and new_rating is not None
                    and (previous_rating - new_rating) >= RATING_DROP_THRESHOLD
                ):
                    _alert_rating_drop(app, previous_rating, new_rating)
                    result["rating_drop_alert"] = True

                results.append(result)
                logger.info("Refreshed store data for app %d: rating=%s", app.id, new_rating)

            except Exception as exc:
                logger.error("Store refresh failed for app %d: %s", app.id, exc)
                db.rollback()

        return {"refreshed": len(results), "apps": results}

    except Exception as exc:
        db.rollback()
        logger.error("refresh_store_data task failed: %s", exc)
        raise self.retry(exc=exc, countdown=300)
    finally:
        db.close()


def _alert_rating_drop(app, previous: float, current: float) -> None:
    """Send an urgent notification when an app's rating drops significantly."""
    try:
        from workers.notification_tasks import _notify
        drop = round(previous - current, 2)
        message = (
            f"⚠️ <b>RATING DROP ALERT</b>\n\n"
            f"App: <b>{app.name}</b>\n"
            f"Rating dropped from ⭐ {previous} → ⭐ {current} (−{drop})\n\n"
            f"Suggested action: generate recovery content to address user concerns.\n"
            f"Trigger: POST /api/v1/apps/{app.id}/generate-campaign"
        )
        _notify(f"⚠️ Rating Drop: {app.name} ({previous} → {current})", message)
        logger.warning("Rating drop alert sent for app %d: %s → %s", app.id, previous, current)
    except Exception as exc:
        logger.error("Failed to send rating drop alert: %s", exc)


@celery_app.task(name="workers.appstore_tasks.refresh_all_store_data")
def refresh_all_store_data():
    """Convenience Beat task — delegates to refresh_store_data with no app_id filter."""
    return refresh_store_data.apply(args=[None]).get(timeout=120)
