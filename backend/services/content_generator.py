"""
Content Generation Service
Primary: Ollama (local LLM)
Fallback: OpenRouter (free-tier)
Fallback-2: Template-based generation (no AI required)
"""

import json
import logging
import random
from typing import List, Dict, Any
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

logger = logging.getLogger(__name__)


# ── Ollama ─────────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(httpx.RequestError),
    reraise=False,
)
def _call_ollama(base_url: str, model: str, system_prompt: str, user_prompt: str) -> str:
    with httpx.Client(timeout=120) as client:
        resp = client.post(
            f"{base_url}/api/chat",
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
                "stream": False,
                "format": "json",
            },
        )
        resp.raise_for_status()
        return resp.json()["message"]["content"]


# ── OpenRouter ─────────────────────────────────────────────────────────────

@retry(
    stop=stop_after_attempt(2),
    wait=wait_exponential(multiplier=1, min=2, max=8),
    retry=retry_if_exception_type(httpx.RequestError),
    reraise=False,
)
def _call_openrouter(api_key: str, model: str, system_prompt: str, user_prompt: str) -> str:
    with httpx.Client(timeout=60) as client:
        resp = client.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt},
                ],
            },
        )
        resp.raise_for_status()
        return resp.json()["choices"][0]["message"]["content"]


# ── Template fallback (no AI) ──────────────────────────────────────────────

_HOOK_TEMPLATES = [
    "Nobody is talking about this: {topic}",
    "I can't believe {topic} works this well.",
    "POV: You just discovered {topic} for the first time.",
    "This changed everything I know about mobile apps: {topic}",
    "Stop scrolling. You need to hear about {topic}.",
]

_SCRIPT_TEMPLATE = (
    "Okay so hear me out. {topic}. "
    "I know what you're thinking — you've seen this before. "
    "But this is different. "
    "Most mobile apps in this space do the bare minimum. "
    "This one actually solves the problem. "
    "I spent {days} days testing it and the results blew me away. "
    "If you're an indie developer or a gamer, "
    "you need to add this to your toolkit right now. "
    "Link in bio. Go check it out."
)

_CAPTION_TEMPLATES = [
    "Found this hidden gem and I had to share it 🔥 {topic} #indiegame #appdev",
    "Day {day} of sharing things nobody talks about. Today: {topic}",
    "I built something. {topic}. Tell me what you think 👇",
]

_HASHTAG_SETS = [
    "#IndieGame, #MobileGaming, #AppDev, #GameDev, #BuildInPublic, #IndieDev, #AppLaunch, #MobileApp",
    "#GameDevelopment, #IndieGaming, #MobileGame, #AppStore, #GooglePlay, #IndieDev, #SideProject, #CodeNewbie",
    "#iOS, #Android, #MobileApp, #IndieGame, #GameDev, #BuildInPublic, #TechTwitter, #SideProject",
]


def _template_fallback(topic: str) -> List[Dict]:
    variations = []
    for i in range(3):
        hook = random.choice(_HOOK_TEMPLATES).format(topic=topic[:60])
        script = _SCRIPT_TEMPLATE.format(
            topic=topic[:80],
            days=random.choice([7, 14, 30]),
        )
        caption = random.choice(_CAPTION_TEMPLATES).format(
            topic=topic[:100],
            day=random.randint(1, 30),
        )
        hashtags = _HASHTAG_SETS[i % len(_HASHTAG_SETS)]
        variations.append({"hook": hook, "script": script, "caption": caption, "hashtags": hashtags})
    return variations


# ── JSON extraction helper ─────────────────────────────────────────────────

def _extract_json_array(raw: str) -> List[Dict]:
    """Robustly extract a JSON array from LLM output that may have extra text."""
    raw = raw.strip()
    start = raw.find("[")
    end = raw.rfind("]") + 1
    if start == -1 or end == 0:
        raise ValueError("No JSON array found in LLM response")
    return json.loads(raw[start:end])


# ── Public API ─────────────────────────────────────────────────────────────

def generate_content_variations(
    topic: str,
    source: str,
    system_prompt: str,
    user_prompt: str,
    ollama_base_url: str,
    ollama_model: str,
    openrouter_api_key: str | None = None,
    openrouter_model: str = "meta-llama/llama-3-8b-instruct:free",
) -> List[Dict]:
    """
    Try Ollama → OpenRouter → template fallback.
    Returns list of 3 content variation dicts.
    """
    raw_response = None

    # 1. Ollama
    try:
        raw_response = _call_ollama(ollama_base_url, ollama_model, system_prompt, user_prompt)
        variations = _extract_json_array(raw_response)
        logger.info(f"Generated {len(variations)} variations via Ollama for: {topic[:50]}")
        return variations[:3]
    except Exception as e:
        logger.warning(f"Ollama failed ({e}), trying OpenRouter")

    # 2. OpenRouter
    if openrouter_api_key:
        try:
            raw_response = _call_openrouter(openrouter_api_key, openrouter_model, system_prompt, user_prompt)
            variations = _extract_json_array(raw_response)
            logger.info(f"Generated {len(variations)} variations via OpenRouter for: {topic[:50]}")
            return variations[:3]
        except Exception as e:
            logger.warning(f"OpenRouter failed ({e}), falling back to templates")

    # 3. Template fallback
    logger.info(f"Using template fallback for: {topic[:50]}")
    return _template_fallback(topic)
