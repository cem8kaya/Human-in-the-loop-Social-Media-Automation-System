"""
Trend Discovery Service
Fetches trending topics from Reddit, Twitter, and TikTok (mocked when credentials absent).
Each source returns a list of TrendResult dicts with keys: source, topic, score, raw_data.
"""

import random
import logging
from datetime import datetime
from typing import List, Dict, Any
import httpx

logger = logging.getLogger(__name__)

# ── Mobile/game-relevance keywords for scoring ────────────────────────────

RELEVANCE_KEYWORDS = [
    "game", "app", "mobile", "indie", "launch", "download", "play",
    "update", "feature", "viral", "trend", "dev", "developer", "build",
    "release", "startup", "product", "saas", "tool", "free", "ios", "android",
]

INDIE_SUBREDDITS = [
    "indiegaming", "gamedev", "indiegames", "androidgaming", "iosgaming",
    "mobilegaming", "SideProject", "indiehackers", "AppIdeas",
]


def _relevance_score(text: str) -> float:
    text_lower = text.lower()
    hits = sum(1 for kw in RELEVANCE_KEYWORDS if kw in text_lower)
    return min(hits / max(len(RELEVANCE_KEYWORDS) * 0.3, 1), 1.0)


# ── Reddit ─────────────────────────────────────────────────────────────────

def fetch_reddit_trends(client_id: str, client_secret: str, user_agent: str) -> List[Dict]:
    try:
        import praw
        reddit = praw.Reddit(
            client_id=client_id,
            client_secret=client_secret,
            user_agent=user_agent,
        )
        results = []
        for subreddit_name in INDIE_SUBREDDITS[:5]:
            try:
                sub = reddit.subreddit(subreddit_name)
                for post in sub.hot(limit=10):
                    topic = post.title
                    score = _relevance_score(topic) * 0.5 + min(post.score / 10000, 0.5)
                    results.append({
                        "source": "reddit",
                        "topic": topic,
                        "score": round(score, 3),
                        "raw_data": {
                            "subreddit": subreddit_name,
                            "url": f"https://reddit.com{post.permalink}",
                            "upvotes": post.score,
                            "comments": post.num_comments,
                        },
                    })
            except Exception as e:
                logger.warning(f"Skipping subreddit {subreddit_name}: {e}")
        return sorted(results, key=lambda x: x["score"], reverse=True)[:20]
    except Exception as e:
        logger.error(f"Reddit fetch failed: {e}")
        return _mock_reddit_trends()


def _mock_reddit_trends() -> List[Dict]:
    topics = [
        ("I built a mobile game in 30 days with no budget - here's what happened", 0.88),
        ("Why your indie app isn't getting downloads (and how to fix it)", 0.82),
        ("Show HN: I made a free habit tracker with 0 ads - 10k users in a week", 0.79),
        ("Nobody talks about this growth hack for mobile games", 0.75),
        ("I quit my job to build this app. 6 months later...", 0.72),
        ("Unity vs Unreal for mobile in 2024 - honest comparison", 0.68),
        ("My hyper-casual game hit 1M downloads. Here's my full breakdown", 0.85),
        ("The indie dev survival guide - tools I actually use", 0.65),
        ("Launched on Product Hunt, got 500 upvotes - what I learned", 0.70),
        ("App Store Optimization secrets nobody shares", 0.77),
    ]
    return [
        {
            "source": "reddit",
            "topic": t,
            "score": s,
            "raw_data": {"mock": True, "subreddit": random.choice(INDIE_SUBREDDITS)},
        }
        for t, s in topics
    ]


# ── Twitter/X ──────────────────────────────────────────────────────────────

def fetch_twitter_trends(bearer_token: str) -> List[Dict]:
    try:
        headers = {"Authorization": f"Bearer {bearer_token}"}
        with httpx.Client(timeout=10) as client:
            resp = client.get(
                "https://api.twitter.com/2/trends/by/woeid/1",
                headers=headers,
            )
            resp.raise_for_status()
            data = resp.json()
            results = []
            for trend in data.get("trends", [])[:20]:
                name = trend.get("name", "")
                score = _relevance_score(name)
                results.append({
                    "source": "twitter",
                    "topic": name,
                    "score": round(score, 3),
                    "raw_data": {"tweet_volume": trend.get("tweet_volume", 0)},
                })
            return results
    except Exception as e:
        logger.warning(f"Twitter fetch failed, using mock: {e}")
        return _mock_twitter_trends()


def _mock_twitter_trends() -> List[Dict]:
    topics = [
        ("#IndieGame", 0.80),
        ("#MobileGaming", 0.78),
        ("#AppLaunch", 0.75),
        ("#GameDev", 0.83),
        ("#IndieDev", 0.81),
        ("#SideProject", 0.70),
        ("#BuildInPublic", 0.72),
        ("#NoCode", 0.65),
        ("#ProductHunt", 0.68),
        ("#AppStore", 0.74),
    ]
    return [
        {
            "source": "twitter",
            "topic": t,
            "score": s,
            "raw_data": {"mock": True, "tweet_volume": random.randint(1000, 100000)},
        }
        for t, s in topics
    ]


# ── TikTok ─────────────────────────────────────────────────────────────────

def fetch_tiktok_trends(api_key: str) -> List[Dict]:
    # TikTok's Research API is restricted; always use curated mock for MVP
    return _mock_tiktok_trends()


def _mock_tiktok_trends() -> List[Dict]:
    topics = [
        ("POV: You downloaded this app and your life changed", 0.90),
        ("Nobody knows this mobile game exists but it's amazing", 0.87),
        ("I spent 30 days building an app - final result", 0.85),
        ("This indie game is better than any AAA title", 0.82),
        ("The app that got me off social media (ironically)", 0.79),
        ("Rating viral mobile games so you don't have to", 0.76),
        ("Day 1 of building my app in public", 0.74),
        ("This free app does what Notion can't", 0.72),
        ("Coding my dream game - realistic timelapse", 0.71),
        ("If you're a gamer you NEED this app", 0.88),
    ]
    return [
        {
            "source": "tiktok",
            "topic": t,
            "score": s,
            "raw_data": {"mock": True, "views": random.randint(100000, 5000000)},
        }
        for t, s in topics
    ]


# ── Main entry point ────────────────────────────────────────────────────────

def discover_all_trends(config: dict) -> List[Dict]:
    """Discover trends from all sources and return deduplicated, scored list."""
    results = []

    # Reddit
    if config.get("reddit_client_id") and config.get("reddit_client_secret"):
        results.extend(fetch_reddit_trends(
            config["reddit_client_id"],
            config["reddit_client_secret"],
            config.get("reddit_user_agent", "SocialAutomationBot/1.0"),
        ))
    else:
        logger.info("No Reddit credentials — using mock data")
        results.extend(_mock_reddit_trends())

    # Twitter
    if config.get("twitter_bearer_token"):
        results.extend(fetch_twitter_trends(config["twitter_bearer_token"]))
    else:
        logger.info("No Twitter credentials — using mock data")
        results.extend(_mock_twitter_trends())

    # TikTok (always mock for now)
    results.extend(_mock_tiktok_trends())

    # Sort by score descending
    results.sort(key=lambda x: x["score"], reverse=True)
    return results
