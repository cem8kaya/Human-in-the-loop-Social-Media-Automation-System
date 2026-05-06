import logging
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workers.celery_app import celery_app
from models.database import SessionLocal
from models.orm import Trend, Post
from services.content_generator import generate_content_variations
from services.media_generator import generate_text_image, generate_video_script_file
from prompts.templates import SYSTEM_PROMPT, build_generation_prompt, VIRAL_FORMATS
from config import settings

logger = logging.getLogger(__name__)

VIRAL_FORMAT_KEYS = list(VIRAL_FORMATS.keys())


@celery_app.task(name="workers.content_tasks.generate_posts_for_trend", bind=True, max_retries=3)
def generate_posts_for_trend(self, trend_id: int, viral_format: str | None = None):
    """Generate 3 post variations for a given trend_id."""
    db = SessionLocal()
    try:
        trend = db.query(Trend).filter(Trend.id == trend_id).first()
        if not trend:
            logger.error(f"Trend {trend_id} not found")
            return {"error": "trend not found"}

        chosen_format = viral_format or random.choice(VIRAL_FORMAT_KEYS)
        system_prompt = SYSTEM_PROMPT
        user_prompt = build_generation_prompt(trend.topic, trend.source, chosen_format)

        variations = generate_content_variations(
            topic=trend.topic,
            source=trend.source,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            ollama_base_url=settings.ollama_base_url,
            ollama_model=settings.ollama_model,
            openrouter_api_key=settings.openrouter_api_key,
            openrouter_model=settings.openrouter_model,
        )

        created_ids = []
        for i, v in enumerate(variations):
            # Generate thumbnail image
            img_path = generate_text_image(v.get("hook", ""), variation_index=i)
            generate_video_script_file(v.get("hook", ""), v.get("script", ""), variation_index=i)

            post = Post(
                trend_id=trend_id,
                hook=v.get("hook", ""),
                script=v.get("script", ""),
                caption=v.get("caption", ""),
                hashtags=v.get("hashtags", ""),
                variation_index=i,
                status="generated",
                media_url=img_path,
                media_type="image" if img_path else None,
            )
            db.add(post)
            db.flush()
            created_ids.append(post.id)

        db.commit()
        logger.info(f"Created {len(created_ids)} posts for trend {trend_id}")
        return {"trend_id": trend_id, "post_ids": created_ids}
    except Exception as exc:
        db.rollback()
        logger.error(f"Content generation failed for trend {trend_id}: {exc}")
        raise self.retry(exc=exc, countdown=30)
    finally:
        db.close()


@celery_app.task(name="workers.content_tasks.generate_posts_for_top_trends")
def generate_posts_for_top_trends(limit: int = 5):
    """Auto-generate posts for the top-N trending topics that have no posts yet."""
    db = SessionLocal()
    try:
        trends_with_posts = db.query(Post.trend_id).distinct().subquery()
        fresh_trends = (
            db.query(Trend)
            .filter(Trend.id.not_in(trends_with_posts))
            .order_by(Trend.score.desc())
            .limit(limit)
            .all()
        )
        for trend in fresh_trends:
            generate_posts_for_trend.delay(trend.id)
        return {"queued": [t.id for t in fresh_trends]}
    finally:
        db.close()
