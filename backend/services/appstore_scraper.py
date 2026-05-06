"""
App Store Intelligence service.

Sources:
  - Apple App Store: iTunes lookup API (no auth, public)
  - Google Play Store: google-play-scraper Python library

Extracted data stored in App.raw_store_data:
  {
    "rating": float,
    "review_count": int,
    "category_ranking": str | None,
    "whats_new": str | None,
    "recent_reviews": [{"author": str, "rating": int, "text": str}],
    "last_updated": ISO-8601 str
  }
"""
from __future__ import annotations

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)


# ── Apple App Store ────────────────────────────────────────────────────────

def _apple_app_id_from_url(url: str) -> Optional[str]:
    """Extract numeric App Store ID from a URL like …/id123456789."""
    import re
    m = re.search(r"/id(\d+)", url)
    return m.group(1) if m else None


def fetch_appstore_data(app_store_url: str) -> Dict[str, Any]:
    """Fetch app metadata from the Apple iTunes lookup API."""
    app_id = _apple_app_id_from_url(app_store_url)
    if not app_id:
        raise ValueError(f"Cannot extract App Store ID from URL: {app_store_url}")

    with httpx.Client(timeout=15) as client:
        resp = client.get(
            "https://itunes.apple.com/lookup",
            params={"id": app_id, "country": "us"},
        )
        resp.raise_for_status()
        data = resp.json()

    results = data.get("results", [])
    if not results:
        raise ValueError(f"No results from iTunes lookup for id={app_id}")

    r = results[0]
    return {
        "rating": round(r.get("averageUserRating", 0.0), 1),
        "review_count": r.get("userRatingCount", 0),
        "category_ranking": r.get("primaryGenreName"),
        "whats_new": r.get("releaseNotes", ""),
        "recent_reviews": [],          # iTunes lookup doesn't return reviews
        "version": r.get("version"),
        "last_updated": datetime.utcnow().isoformat(),
        "source": "apple",
    }


# ── Google Play Store ──────────────────────────────────────────────────────

def fetch_playstore_data(bundle_id: str, lang: str = "en", country: str = "us") -> Dict[str, Any]:
    """Fetch app metadata from Google Play via google-play-scraper."""
    try:
        from google_play_scraper import app as gp_app, reviews as gp_reviews, Sort
    except ImportError:
        raise RuntimeError("google-play-scraper is not installed — add it to requirements.txt")

    info = gp_app(bundle_id, lang=lang, country=country)

    # Fetch a few recent reviews
    recent: List[Dict[str, Any]] = []
    try:
        result, _ = gp_reviews(bundle_id, lang=lang, country=country, sort=Sort.NEWEST, count=5)
        for rev in result:
            recent.append({
                "author": rev.get("userName", ""),
                "rating": rev.get("score", 0),
                "text": (rev.get("content", "") or "")[:300],
            })
    except Exception as exc:
        logger.warning("Could not fetch Play Store reviews: %s", exc)

    return {
        "rating": round(info.get("score") or 0.0, 1),
        "review_count": info.get("ratings", 0),
        "category_ranking": info.get("genre"),
        "whats_new": info.get("recentChangesHTML", ""),
        "recent_reviews": recent,
        "version": info.get("version"),
        "last_updated": datetime.utcnow().isoformat(),
        "source": "google_play",
    }


# ── Unified refresh ────────────────────────────────────────────────────────

def refresh_app_store_data(app) -> Dict[str, Any]:
    """Refresh store data for an App ORM instance.

    Tries App Store first (if app_store_url set), then Play Store
    (if bundle_id set).  Merges both when both are available.
    Returns the merged raw_store_data dict.
    """
    merged: Dict[str, Any] = dict(app.raw_store_data or {})

    if app.app_store_url:
        try:
            apple_data = fetch_appstore_data(app.app_store_url)
            merged.update(apple_data)
            logger.info("Refreshed App Store data for app %d (%s)", app.id, app.name)
        except Exception as exc:
            logger.warning("App Store fetch failed for app %d: %s", app.id, exc)

    if app.bundle_id and app.platform in ("android", "both"):
        try:
            play_data = fetch_playstore_data(app.bundle_id)
            # Prefer Play Store reviews; average ratings from both stores if available
            if "rating" in merged and "rating" in play_data:
                play_data["rating"] = round((merged["rating"] + play_data["rating"]) / 2, 1)
            merged.update(play_data)
            logger.info("Refreshed Play Store data for app %d (%s)", app.id, app.name)
        except Exception as exc:
            logger.warning("Play Store fetch failed for app %d: %s", app.id, exc)

    merged["last_refreshed"] = datetime.utcnow().isoformat()
    return merged


# ── Social proof snippet ───────────────────────────────────────────────────

def build_social_proof_snippet(raw_store_data: Dict[str, Any]) -> str:
    """Return a short social-proof string suitable for embedding in captions.

    Example: "⭐ 4.8 stars · 12k reviews — here's why:"
    """
    rating = raw_store_data.get("rating")
    count = raw_store_data.get("review_count", 0)

    if not rating:
        return ""

    if count >= 1_000_000:
        count_str = f"{count // 1_000_000}M"
    elif count >= 1_000:
        count_str = f"{count // 1_000}k"
    else:
        count_str = str(count)

    return f"⭐ {rating} stars · {count_str} reviews — here's why:"
