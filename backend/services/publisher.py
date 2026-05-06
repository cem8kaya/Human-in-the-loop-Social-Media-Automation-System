"""
Publisher Service
Handles posting to social platforms.
Real API calls when credentials present; mock otherwise.
"""

import logging
from datetime import datetime
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def publish_to_twitter(post_data: Dict, credentials: Dict) -> Dict[str, Any]:
    try:
        import tweepy
        auth = tweepy.OAuthHandler(credentials["api_key"], credentials["api_secret"])
        auth.set_access_token(credentials["access_token"], credentials["access_token_secret"])
        api = tweepy.API(auth)
        text = f"{post_data['caption']}\n\n{post_data['hashtags']}"[:280]
        tweet = api.update_status(text)
        return {"success": True, "platform_id": str(tweet.id), "url": f"https://twitter.com/i/status/{tweet.id}"}
    except ImportError:
        return _mock_publish("twitter", post_data)
    except Exception as e:
        logger.error(f"Twitter publish failed: {e}")
        return {"success": False, "error": str(e)}


def publish_to_instagram(post_data: Dict, credentials: Dict) -> Dict[str, Any]:
    # Instagram Graph API requires media upload — mock for MVP
    return _mock_publish("instagram", post_data)


def publish_to_tiktok(post_data: Dict, credentials: Dict) -> Dict[str, Any]:
    # TikTok Content Posting API is invite-only — mock for MVP
    return _mock_publish("tiktok", post_data)


def _mock_publish(platform: str, post_data: Dict) -> Dict[str, Any]:
    import random
    import string
    fake_id = "".join(random.choices(string.digits, k=18))
    platform_urls = {
        "twitter": f"https://twitter.com/i/status/{fake_id}",
        "instagram": f"https://www.instagram.com/p/{fake_id}/",
        "tiktok": f"https://www.tiktok.com/@user/video/{fake_id}",
    }
    logger.info(f"[MOCK] Published to {platform}: {post_data.get('caption', '')[:80]}")
    return {
        "success": True,
        "platform_id": fake_id,
        "url": platform_urls.get(platform, "#"),
        "mock": True,
        "posted_at": datetime.utcnow().isoformat(),
    }


def publish_post(platform: str, post_data: Dict, credentials: Dict) -> Dict[str, Any]:
    handlers = {
        "twitter": publish_to_twitter,
        "instagram": publish_to_instagram,
        "tiktok": publish_to_tiktok,
    }
    handler = handlers.get(platform)
    if not handler:
        return {"success": False, "error": f"Unknown platform: {platform}"}
    return handler(post_data, credentials)
