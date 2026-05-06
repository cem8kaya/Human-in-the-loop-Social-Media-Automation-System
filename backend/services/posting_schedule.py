"""
Optimal posting time engine.

Phase 1 (item 1): static research-backed windows used for auto-scheduling.
Phase 1 (item 3): data-driven windows once >= 30 posts exist per (platform, account).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# Research-backed default optimal posting windows (hour, UTC)
PLATFORM_DEFAULT_HOURS: dict[str, list[int]] = {
    "twitter":   [9, 12, 17, 21],
    "instagram": [11, 14, 20],
    "tiktok":    [7, 12, 19, 22],
}

_FALLBACK_HOURS = [9, 12, 17, 21]


def get_next_optimal_slot(
    platform: str,
    account_id: Optional[str] = None,
    db=None,
    after: Optional[datetime] = None,
) -> datetime:
    """Return the next UTC datetime in an optimal posting window.

    Uses data-driven hours when >= 30 posts exist for the account/platform
    (populated by item 3 full implementation); otherwise falls back to the
    research-backed defaults.

    Args:
        platform: "twitter" | "instagram" | "tiktok"
        account_id: optional account identifier for per-account learning
        db: SQLAlchemy session (optional; enables data-driven hours)
        after: find a slot after this datetime (defaults to utcnow)
    """
    now = after or datetime.utcnow()
    hours = _get_optimal_hours(platform, account_id, db)

    for days_ahead in range(14):
        base = now.date() + timedelta(days=days_ahead)
        for hour in sorted(hours):
            candidate = datetime(base.year, base.month, base.day, hour, 0)
            if candidate > now + timedelta(minutes=5):
                return candidate

    return now + timedelta(hours=1)


def _get_optimal_hours(
    platform: str,
    account_id: Optional[str],
    db,
) -> list[int]:
    """Return data-driven hours if enough data exists, else static defaults."""
    if db is None:
        return PLATFORM_DEFAULT_HOURS.get(platform, _FALLBACK_HOURS)

    try:
        from models.orm import PostingPerformance
        from sqlalchemy import func

        query = db.query(PostingPerformance).filter(
            PostingPerformance.platform == platform,
            PostingPerformance.sample_count >= 5,
        )
        if account_id:
            query = query.filter(PostingPerformance.account_id == account_id)

        rows = query.order_by(PostingPerformance.avg_engagement.desc()).all()
        total_samples = sum(r.sample_count for r in rows)

        if total_samples >= 30:
            # Use top-N hours by avg engagement
            top = rows[:4]
            return [r.hour_of_day for r in top] or PLATFORM_DEFAULT_HOURS.get(platform, _FALLBACK_HOURS)
    except Exception:
        pass

    return PLATFORM_DEFAULT_HOURS.get(platform, _FALLBACK_HOURS)


def update_posting_performance(
    platform: str,
    hour_of_day: int,
    engagement_score: float,
    account_id: Optional[str] = None,
    db=None,
) -> None:
    """Update running avg engagement for a (platform, hour) slot after a post is published."""
    if db is None:
        return
    try:
        from models.orm import PostingPerformance

        row = (
            db.query(PostingPerformance)
            .filter(
                PostingPerformance.platform == platform,
                PostingPerformance.hour_of_day == hour_of_day,
                PostingPerformance.account_id == account_id,
            )
            .first()
        )
        if row is None:
            row = PostingPerformance(
                platform=platform,
                hour_of_day=hour_of_day,
                account_id=account_id,
                sample_count=0,
                avg_engagement=0.0,
            )
            db.add(row)

        n = row.sample_count
        row.avg_engagement = (row.avg_engagement * n + engagement_score) / (n + 1)
        row.sample_count = n + 1
        db.commit()
    except Exception as exc:
        logger.warning("Failed to update posting performance: %s", exc)
