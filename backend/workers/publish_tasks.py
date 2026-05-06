import logging
import sys
import os
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workers.celery_app import celery_app
from models.database import SessionLocal
from models.orm import Post, Analytics
from services.publisher import publish_post
from config import settings

logger = logging.getLogger(__name__)


def _get_credentials(platform: str) -> dict:
    if platform == "twitter":
        return {
            "api_key": settings.twitter_api_key,
            "api_secret": settings.twitter_api_secret,
            "access_token": settings.twitter_access_token,
            "access_token_secret": settings.twitter_access_token_secret,
        }
    if platform == "instagram":
        return {"access_token": settings.instagram_access_token}
    return {}


@celery_app.task(name="workers.publish_tasks.publish_post_task", bind=True, max_retries=3)
def publish_post_task(self, post_id: int):
    db = SessionLocal()
    try:
        post = db.query(Post).filter(Post.id == post_id).first()
        if not post:
            return {"error": "post not found"}
        if post.status != "scheduled":
            return {"error": f"post is {post.status}, not scheduled"}

        credentials = _get_credentials(post.platform)
        result = publish_post(
            platform=post.platform,
            post_data={
                "caption": post.caption,
                "hashtags": post.hashtags,
                "hook": post.hook,
                "script": post.script,
                "media_url": post.media_url,
            },
            credentials=credentials,
        )

        if result.get("success"):
            post.status = "posted"
            post.posted_at = datetime.utcnow()
            # Seed analytics row
            if not post.analytics:
                db.add(Analytics(post_id=post.id))
            db.commit()
            logger.info(f"Post {post_id} published to {post.platform}")
            return {"post_id": post_id, "platform": post.platform, "url": result.get("url")}
        else:
            raise Exception(result.get("error", "publish failed"))
    except Exception as exc:
        db.rollback()
        logger.error(f"Publish failed for post {post_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)
    finally:
        db.close()


@celery_app.task(name="workers.publish_tasks.publish_scheduled_posts")
def publish_scheduled_posts():
    """Check for posts due to be published and dispatch them."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due_posts = (
            db.query(Post)
            .filter(Post.status == "scheduled", Post.scheduled_at <= now)
            .all()
        )
        dispatched = []
        for post in due_posts:
            publish_post_task.delay(post.id)
            dispatched.append(post.id)
        if dispatched:
            logger.info(f"Dispatched {len(dispatched)} scheduled posts: {dispatched}")
        return {"dispatched": dispatched}
    finally:
        db.close()
