"""
Daily digest and urgent-alert notification tasks.

Channels (in priority order):
  1. Telegram bot  (TELEGRAM_BOT_TOKEN + TELEGRAM_CHAT_ID)
  2. SMTP email    (SMTP_USER + SMTP_PASSWORD + NOTIFY_EMAIL_TO)

Beat schedule:
  - daily_digest:          daily at 09:00 UTC
  - check_stale_reviews:   every 30 minutes (alerts when post pending > 24 h)
"""
from __future__ import annotations

import logging
import smtplib
import sys
import os
from datetime import datetime, timedelta
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from workers.celery_app import celery_app
from models.database import SessionLocal
from models.orm import Post, Analytics
from config import settings

logger = logging.getLogger(__name__)


# ── Low-level send helpers ─────────────────────────────────────────────────

def _send_telegram(message: str) -> bool:
    """Send a message via Telegram Bot API. Returns True on success."""
    if not settings.telegram_bot_token or not settings.telegram_chat_id:
        return False
    try:
        import httpx
        url = f"https://api.telegram.org/bot{settings.telegram_bot_token}/sendMessage"
        resp = httpx.post(
            url,
            json={
                "chat_id": settings.telegram_chat_id,
                "text": message,
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        resp.raise_for_status()
        logger.info("Telegram message sent")
        return True
    except Exception as exc:
        logger.warning("Telegram send failed: %s", exc)
        return False


def _send_email(subject: str, body: str) -> bool:
    """Send a plain-text email via SMTP. Returns True on success."""
    if not all([settings.smtp_user, settings.smtp_password, settings.notify_email_to]):
        return False
    try:
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = settings.smtp_user
        msg["To"] = settings.notify_email_to
        msg.attach(MIMEText(body, "plain"))

        with smtplib.SMTP(settings.smtp_host, settings.smtp_port) as server:
            server.ehlo()
            server.starttls()
            server.login(settings.smtp_user, settings.smtp_password)
            server.sendmail(settings.smtp_user, settings.notify_email_to, msg.as_string())
        logger.info("Email notification sent to %s", settings.notify_email_to)
        return True
    except Exception as exc:
        logger.warning("SMTP send failed: %s", exc)
        return False


def _notify(subject: str, body: str) -> None:
    """Send via Telegram (preferred) with SMTP fallback."""
    sent = _send_telegram(body)
    if not sent:
        _send_email(subject, body)


# ── Digest builder ─────────────────────────────────────────────────────────

def _build_digest(db) -> str:
    now = datetime.utcnow()
    yesterday = now - timedelta(days=1)

    # Pending review posts
    pending = (
        db.query(Post)
        .filter(Post.status == "pending_review")
        .order_by(Post.created_at.desc())
        .all()
    )

    # Yesterday's top performer
    top_post = (
        db.query(Post, Analytics)
        .join(Analytics, Analytics.post_id == Post.id)
        .filter(Post.posted_at >= yesterday)
        .order_by(Analytics.engagement_score.desc())
        .first()
    )

    # Today's scheduled posts
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    today_end = today_start + timedelta(days=1)
    scheduled_today = (
        db.query(Post)
        .filter(
            Post.status == "scheduled",
            Post.scheduled_at >= today_start,
            Post.scheduled_at < today_end,
        )
        .order_by(Post.scheduled_at)
        .all()
    )

    lines = ["<b>📊 Daily Social Media Digest</b>", f"<i>{now.strftime('%Y-%m-%d %H:%M UTC')}</i>", ""]

    # Pending review
    lines.append(f"<b>🔎 Pending Review ({len(pending)} posts)</b>")
    if pending:
        for p in pending[:5]:
            approve_url = f"{settings.base_url}/api/v1/posts/{p.id}/review"
            age_h = int((now - p.created_at).total_seconds() / 3600)
            lines.append(f"  • [{p.platform}] {p.hook[:60]}… (age: {age_h}h)")
            lines.append(f"    Approve: {approve_url}")
        if len(pending) > 5:
            lines.append(f"  … and {len(pending) - 5} more")
    else:
        lines.append("  ✅ No posts pending review")
    lines.append("")

    # Top performer
    lines.append("<b>🏆 Yesterday's Top Post</b>")
    if top_post:
        post_obj, analytics_obj = top_post
        lines.append(
            f"  [{post_obj.platform}] {post_obj.hook[:80]}\n"
            f"  Engagement: {analytics_obj.engagement_score:.2f} | "
            f"Likes: {analytics_obj.likes} | Views: {analytics_obj.views}"
        )
    else:
        lines.append("  No published posts yesterday")
    lines.append("")

    # Scheduled today
    lines.append(f"<b>📅 Scheduled Today ({len(scheduled_today)} posts)</b>")
    if scheduled_today:
        for p in scheduled_today:
            slot = p.scheduled_at.strftime("%H:%M UTC") if p.scheduled_at else "?"
            lines.append(f"  • {slot} [{p.platform}] {p.hook[:60]}…")
    else:
        lines.append("  No posts scheduled for today")

    return "\n".join(lines)


# ── Celery tasks ───────────────────────────────────────────────────────────

@celery_app.task(name="workers.notification_tasks.send_daily_digest")
def send_daily_digest():
    """Build and send the daily digest at 09:00 UTC."""
    db = SessionLocal()
    try:
        digest = _build_digest(db)
        _notify("📊 Daily Social Media Digest", digest)
        logger.info("Daily digest sent")
        return {"status": "sent"}
    except Exception as exc:
        logger.error("Daily digest failed: %s", exc)
        return {"status": "error", "detail": str(exc)}
    finally:
        db.close()


@celery_app.task(name="workers.notification_tasks.check_stale_reviews")
def check_stale_reviews():
    """Alert immediately if any post has been pending_review for > 24 h."""
    db = SessionLocal()
    try:
        cutoff = datetime.utcnow() - timedelta(hours=24)
        stale = (
            db.query(Post)
            .filter(
                Post.status == "pending_review",
                Post.created_at <= cutoff,
            )
            .all()
        )
        if not stale:
            return {"stale": 0}

        lines = [
            f"⚠️ <b>URGENT: {len(stale)} post(s) have been waiting for review for over 24 hours!</b>",
            "",
        ]
        for p in stale:
            age_h = int((datetime.utcnow() - p.created_at).total_seconds() / 3600)
            approve_url = f"{settings.base_url}/api/v1/posts/{p.id}/review"
            lines.append(f"  • [{p.platform}] {p.hook[:60]}… (age: {age_h}h)")
            lines.append(f"    Approve: {approve_url}")

        message = "\n".join(lines)
        _notify(f"⚠️ URGENT: {len(stale)} stale review(s)", message)
        logger.warning("Stale review alert sent for %d posts", len(stale))
        return {"stale": len(stale)}
    except Exception as exc:
        logger.error("Stale review check failed: %s", exc)
        return {"status": "error", "detail": str(exc)}
    finally:
        db.close()
