"""
Analytics Service
Fetches engagement data (mock for MVP) and computes scoring.
"""

import random
import logging
from datetime import datetime
from typing import Dict, Any

logger = logging.getLogger(__name__)


def fetch_platform_analytics(platform: str, platform_post_id: str, credentials: Dict) -> Dict[str, Any]:
    """Fetch real analytics or return mock data."""
    # Real implementations would call platform APIs here
    return _mock_analytics(platform)


def _mock_analytics(platform: str) -> Dict[str, Any]:
    base = {
        "twitter": {"views": (500, 50000), "likes": (10, 2000), "comments": (1, 200), "shares": (1, 500), "clicks": (5, 1000)},
        "instagram": {"views": (1000, 100000), "likes": (50, 5000), "comments": (2, 500), "shares": (5, 1000), "clicks": (10, 2000)},
        "tiktok": {"views": (5000, 1000000), "likes": (100, 50000), "comments": (10, 5000), "shares": (20, 10000), "clicks": (50, 5000)},
    }
    ranges = base.get(platform, base["twitter"])
    return {k: random.randint(*v) for k, v in ranges.items()}


def compute_engagement_score(views: int, likes: int, comments: int, shares: int, clicks: int) -> float:
    """
    Weighted engagement rate.
    Shares and comments weighted higher as stronger intent signals.
    """
    if views == 0:
        return 0.0
    weighted = likes * 1.0 + comments * 2.0 + shares * 3.0 + clicks * 1.5
    rate = weighted / views
    # Normalize to 0-1 range (cap at 10% engagement rate = score 1.0)
    return round(min(rate / 0.10, 1.0), 4)


def compute_content_score(engagement_score: float, variation_index: int, peer_scores: list) -> float:
    """
    A/B content score: relative ranking among siblings (same trend, different variation).
    Returns percentile 0-1 within the peer group.
    """
    if not peer_scores:
        return engagement_score
    all_scores = sorted(peer_scores + [engagement_score])
    rank = all_scores.index(engagement_score)
    return round(rank / max(len(all_scores) - 1, 1), 4)
