"""
Optimal Posting Time Engine.

Phase 1 — static research-backed windows:
    Twitter:   09:00, 12:00, 17:00, 21:00 UTC
    Instagram: 11:00, 14:00, 20:00 UTC
    TikTok:    07:00, 12:00, 19:00, 22:00 UTC

Data-driven upgrade (kicks in after 30+ posts per account/platform):
    Reads PostingPerformance rows to rank hours by avg engagement and replaces
    the static defaults with the top-N performing hours.

Public API:
    get_next_optimal_slot(platform, account_id, db, after) -> datetime
    get_schedule_preview(platform, account_id, db, days)   -> list[datetime]
    update_posting_performance(platform, hour, engagement, account_id, db)
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)

# ── Research-backed defaults ───────────────────────────────────────────────

PLATFORM_DEFAULT_HOURS: dict[str, list[int]] = {
    "twitter":   [9, 12, 17, 21],
    "instagram": [11, 14, 20],
    "tiktok":    [7, 12, 19, 22],
}

_FALLBACK_HOURS = [9, 12, 17, 21]

# Minimum distinct samples needed before switching to data-driven hours
DATA_DRIVEN_THRESHOLD = 30


# ── Core helpers ───────────────────────────────────────────────────────────

def _get_optimal_hours(
    platform: str,
    account_id: Optional[str],
    db,
) -> list[int]:
    """Return ordered list of UTC hours to post on, using data-driven or static defaults."""
    if db is None:
        return PLATFORM_DEFAULT_HOURS.get(platform, _FALLBACK_HOURS)

    try:
        from models.orm import PostingPerformance

        query = db.query(PostingPerformance).filter(
            PostingPerformance.platform == platform,
            PostingPerformance.sample_count >= 3,
        )
        if account_id:
            query = query.filter(PostingPerformance.account_id == account_id)

        rows = query.order_by(PostingPerformance.avg_engagement.desc()).all()
        total_samples = sum(r.sample_count for r in rows)

        if total_samples >= DATA_DRIVEN_THRESHOLD:
            # Use the top 4 hours by avg engagement (or fewer if not available)
            top_hours = [r.hour_of_day for r in rows[:4]]
            if top_hours:
                logger.debug(
                    "Data-driven hours for %s / %s: %s (n=%d)",
                    platform, account_id, top_hours, total_samples,
                )
                return top_hours
    except Exception as exc:
        logger.warning("Failed to load data-driven hours: %s", exc)

    return PLATFORM_DEFAULT_HOURS.get(platform, _FALLBACK_HOURS)


def _already_scheduled(db, platform: str, slot: datetime, account_id: Optional[str]) -> bool:
    """Return True if another post is already scheduled within ±10 minutes of slot."""
    if db is None:
        return False
    try:
        from models.orm import Post

        window_start = slot - timedelta(minutes=10)
        window_end = slot + timedelta(minutes=10)
        q = db.query(Post).filter(
            Post.platform == platform,
            Post.status.in_(["approved", "scheduled"]),
            Post.scheduled_at >= window_start,
            Post.scheduled_at <= window_end,
        )
        if account_id:
            q = q.filter(Post.account_id == account_id)
        return q.first() is not None
    except Exception:
        return False


# ── Public API ─────────────────────────────────────────────────────────────

def get_next_optimal_slot(
    platform: str,
    account_id: Optional[str] = None,
    db=None,
    after: Optional[datetime] = None,
) -> datetime:
    """Return the next available UTC datetime in an optimal posting window.

    Skips slots that already have a post scheduled within ±10 minutes.

    Args:
        platform: "twitter" | "instagram" | "tiktok"
        account_id: optional for per-account scheduling conflicts
        db: SQLAlchemy session (enables data-driven hours + conflict detection)
        after: find a slot strictly after this datetime (defaults to utcnow)
    """
    now = after or datetime.utcnow()
    hours = _get_optimal_hours(platform, account_id, db)

    for days_ahead in range(14):
        base = now.date() + timedelta(days=days_ahead)
        for hour in sorted(hours):
            candidate = datetime(base.year, base.month, base.day, hour, 0)
            if candidate <= now + timedelta(minutes=5):
                continue
            if not _already_scheduled(db, platform, candidate, account_id):
                return candidate

    # Ultimate fallback: 1 hour from now even if it's not an optimal slot
    return now + timedelta(hours=1)


def get_schedule_preview(
    platform: str,
    account_id: Optional[str] = None,
    db=None,
    days: int = 7,
) -> list[datetime]:
    """Return the next N available optimal slots for a platform/account.

    Useful for the calendar view in the dashboard.
    """
    slots: list[datetime] = []
    cursor = datetime.utcnow()
    hours = _get_optimal_hours(platform, account_id, db)
    slots_needed = len(hours) * days

    for days_ahead in range(days + 3):   # small buffer
        base = cursor.date() + timedelta(days=days_ahead)
        for hour in sorted(hours):
            candidate = datetime(base.year, base.month, base.day, hour, 0)
            if candidate <= cursor + timedelta(minutes=5):
                continue
            if not _already_scheduled(db, platform, candidate, account_id):
                slots.append(candidate)
            if len(slots) >= slots_needed:
                return slots

    return slots


def update_posting_performance(
    platform: str,
    hour_of_day: int,
    engagement_score: float,
    account_id: Optional[str] = None,
    db=None,
) -> None:
    """Update running-average engagement for a (platform, hour_of_day) bucket.

    Called by the analytics task after engagement scores are computed so that
    the posting schedule gradually learns which hours perform best.
    """
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
            db.flush()

        # Incremental running average
        n = row.sample_count
        row.avg_engagement = (row.avg_engagement * n + engagement_score) / (n + 1)
        row.sample_count = n + 1
        db.commit()
    except Exception as exc:
        logger.warning("Failed to update posting performance: %s", exc)
        try:
            db.rollback()
        except Exception:
            pass
