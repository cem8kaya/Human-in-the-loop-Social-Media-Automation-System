import logging
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workers.celery_app import celery_app
from models.database import SessionLocal
from models.orm import Post, Analytics
from services.analytics import fetch_platform_analytics, compute_engagement_score, compute_content_score

logger = logging.getLogger(__name__)


@celery_app.task(name="workers.analytics_tasks.refresh_post_analytics", bind=True)
def refresh_post_analytics(self, post_id: int):
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id, Post.status == "posted").first()
        if not post:
            return {"skipped": post_id}

        raw = fetch_platform_analytics(post.platform, str(post.id), {})
        score = compute_engagement_score(
            raw["views"], raw["likes"], raw["comments"], raw["shares"], raw["clicks"]
        )

        analytics = post.analytics
        if not analytics:
            analytics = Analytics(post_id=post_id)
            db.add(analytics)

        analytics.views = raw["views"]
        analytics.likes = raw["likes"]
        analytics.comments = raw["comments"]
        analytics.shares = raw["shares"]
        analytics.clicks = raw["clicks"]
        analytics.engagement_score = score
        analytics.raw_data = raw
        analytics.fetched_at = datetime.utcnow()
        db.commit()

        # Feed engagement data into the posting-schedule learner
        if post.posted_at:
            from services.posting_schedule import update_posting_performance
            update_posting_performance(
                platform=post.platform,
                hour_of_day=post.posted_at.hour,
                engagement_score=score,
                account_id=post.account_id,
                db=db,
            )

        return {"post_id": post_id, "engagement_score": score}
    except Exception as exc:
        db.rollback()
        logger.error(f"Analytics refresh failed for post {post_id}: {exc}")
    finally:
        db.close()


@celery_app.task(name="workers.analytics_tasks.refresh_all_analytics")
def refresh_all_analytics():
    db = SessionLocal()
    try:
        posted = db.query(Post).filter(Post.status == "posted").all()
        for post in posted:
            refresh_post_analytics.delay(post.id)

        # Compute A/B content scores for each trend
        from sqlalchemy import func
        trend_ids = db.query(Post.trend_id).filter(Post.status == "posted").distinct().all()
        for (tid,) in trend_ids:
            if tid is None:
                continue
            posts = db.query(Post).filter(Post.trend_id == tid, Post.status == "posted").all()
            peer_scores = [p.analytics.engagement_score for p in posts if p.analytics]
            for post in posts:
                if post.analytics:
                    post.analytics.content_score = compute_content_score(
                        post.analytics.engagement_score,
                        post.variation_index,
                        peer_scores,
                    )
        db.commit()
        return {"refreshed": len(posted)}
    finally:
        db.close()
