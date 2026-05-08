import logging
import random
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workers.celery_app import celery_app
from models.database import SessionLocal
from models.orm import App, Trend, Post, Analytics, SystemConfig
from services.content_generator import generate_content_variations
from services.media_generator import generate_text_image, generate_video_script_file
from prompts.templates import SYSTEM_PROMPT, build_generation_prompt, build_app_context, VIRAL_FORMATS
from config import settings

logger = logging.getLogger(__name__)

VIRAL_FORMAT_KEYS = list(VIRAL_FORMATS.keys())

# Rough quality rating per format (based on average viral performance research)
_FORMAT_QUALITY: dict[str, float] = {
    "curiosity_gap":    0.85,
    "controversy":      0.75,
    "built_in_x_days":  0.80,
    "nobody_knows":     0.70,
    "app_launch":       0.82,
    "social_proof":     0.78,
    "update_reveal":    0.76,
    "behind_the_scenes": 0.72,
    "competitor_comparison": 0.74,
}


def _compute_confidence_score(
    trend_score: float,
    viral_format: str,
    hook: str,
    db,
) -> float:
    """Compute a 0–1 confidence score for a generated post variation.

    Components:
        1. trend_score       (35%) — how hot the topic is
        2. format quality    (25%) — research-backed format effectiveness
        3. hook heuristics   (25%) — length, number, punctuation signals
        4. historical avg    (15%) — past engagement for any published posts
    """
    # 1. Trend signal
    trend_contrib = max(0.0, min(1.0, trend_score))

    # 2. Format quality
    format_contrib = _FORMAT_QUALITY.get(viral_format, 0.70)

    # 3. Hook heuristics
    words = hook.split()
    hook_score = 0.4
    if 8 <= len(words) <= 15:
        hook_score += 0.3
    elif 5 <= len(words) < 8:
        hook_score += 0.15
    if any(ch.isdigit() for ch in hook):
        hook_score += 0.15
    if "?" in hook or "!" in hook:
        hook_score += 0.15
    hook_contrib = min(hook_score, 1.0)

    # 4. Historical avg engagement (normalised to 0–1; engagement_score already 0–1)
    hist_contrib = 0.5
    try:
        from sqlalchemy import func as sqlfunc
        avg = db.query(sqlfunc.avg(Analytics.engagement_score)).scalar()
        if avg is not None:
            hist_contrib = max(0.0, min(1.0, float(avg)))
    except Exception:
        pass

    score = (
        trend_contrib  * 0.35
        + format_contrib * 0.25
        + hook_contrib   * 0.25
        + hist_contrib   * 0.15
    )
    return round(min(score, 1.0), 4)


def _get_config(db, key: str, default):
    row = db.query(SystemConfig).filter(SystemConfig.key == key).first()
    return row.value if row else default


@celery_app.task(name="workers.content_tasks.generate_posts_for_trend", bind=True, max_retries=3)
def generate_posts_for_trend(self, trend_id: int, viral_format: str | None = None, app_id: int | None = None):
    """Generate 3 post variations for a given trend_id, auto-approving when autopilot is on."""
    db = SessionLocal()
    try:
        trend = db.query(Trend).filter(Trend.id == trend_id).first()
        if not trend:
            logger.error(f"Trend {trend_id} not found")
            return {"error": "trend not found"}

        # Read autopilot config
        autopilot_on = _get_config(db, "autopilot_enabled", False)
        threshold = float(_get_config(db, "autopilot_confidence_threshold", 0.75))

        chosen_format = viral_format or random.choice(VIRAL_FORMAT_KEYS)
        user_prompt = build_generation_prompt(trend.topic, trend.source, chosen_format)

        # Inject app context into the system prompt when an app is linked
        system_prompt = SYSTEM_PROMPT
        app = None
        if app_id:
            app = db.query(App).filter(App.id == app_id, App.is_active == True).first()
            if app:
                system_prompt = f"{SYSTEM_PROMPT}\n\n{build_app_context(app)}"

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
        auto_approved_ids = []
        for i, v in enumerate(variations):
            img_path = generate_text_image(v.get("hook", ""), variation_index=i)
            generate_video_script_file(v.get("hook", ""), v.get("script", ""), variation_index=i)

            hook = v.get("hook", "")
            confidence = _compute_confidence_score(
                trend_score=trend.score,
                viral_format=chosen_format,
                hook=hook,
                db=db,
            )

            should_auto_approve = autopilot_on and confidence >= threshold

            if should_auto_approve:
                from services.posting_schedule import get_next_optimal_slot
                platform = v.get("platform", "twitter")
                scheduled_dt = get_next_optimal_slot(platform=platform, db=db)
                status = "approved"
            else:
                scheduled_dt = None
                status = "pending_review"

            post = Post(
                trend_id=trend_id,
                app_id=app_id,
                hook=hook,
                script=v.get("script", ""),
                caption=v.get("caption", ""),
                hashtags=v.get("hashtags", ""),
                variation_index=i,
                viral_format=chosen_format,
                confidence_score=confidence,
                auto_approved=should_auto_approve,
                status=status,
                scheduled_at=scheduled_dt,
                media_url=img_path,
                media_type="image" if img_path else None,
            )
            db.add(post)
            db.flush()
            created_ids.append(post.id)
            if should_auto_approve:
                auto_approved_ids.append(post.id)

        db.commit()
        logger.info(
            "Created %d posts for trend %d (auto-approved: %s)",
            len(created_ids), trend_id, auto_approved_ids,
        )
        return {
            "trend_id": trend_id,
            "post_ids": created_ids,
            "auto_approved_ids": auto_approved_ids,
        }
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
