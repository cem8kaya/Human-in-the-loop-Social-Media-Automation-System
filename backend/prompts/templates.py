"""
Reusable, configurable prompt templates for viral content generation.
Each template accepts a context dict and returns a formatted string.
"""

from typing import Dict

# ── Viral format definitions ───────────────────────────────────────────────

VIRAL_FORMATS = {
    "curiosity_gap": {
        "name": "Curiosity Gap",
        "description": "Tease information the viewer doesn't have yet",
        "hook_starters": [
            "Nobody knows this, but…",
            "This one thing changed everything…",
            "I discovered something most devs hide…",
            "What happens when you…",
        ],
    },
    "controversy": {
        "name": "Controversy / Hot Take",
        "description": "Challenge a widely held belief",
        "hook_starters": [
            "Unpopular opinion:",
            "This is going to upset some people, but…",
            "Everyone is wrong about…",
            "Stop doing X. Here's why:",
        ],
    },
    "built_in_x_days": {
        "name": "Built in X Days",
        "description": "Show a creation journey with a time constraint",
        "hook_starters": [
            "I built a complete app in {days} days.",
            "30-day indie dev challenge — here's day {day}.",
            "What I built with zero budget in {days} days.",
            "{days} days. One app. Real results.",
        ],
    },
    "nobody_knows": {
        "name": "Hidden Gem",
        "description": "Reveal an underrated app, game, or technique",
        "hook_starters": [
            "This app has 0 marketing but it's better than anything on the App Store.",
            "Nobody is talking about this game and I'm mad.",
            "Hidden gem alert:",
            "The app you didn't know you needed:",
        ],
    },
}


# ── System prompt ──────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a viral social media content expert specializing in mobile apps and games.
You create short-form video content for TikTok, Instagram Reels, and Twitter/X.
Your content style: direct, punchy, curiosity-driven, relatable to indie developers and gamers.
Never use generic marketing speak. Write like a real person, not a brand.
Always output valid JSON matching the schema requested."""


# ── Content generation prompt ──────────────────────────────────────────────

CONTENT_GENERATION_PROMPT = """
You are generating viral short-form social media content about mobile apps and games.

Trending topic: "{topic}"
Source: {source}
Viral format: {format_name} — {format_description}

Generate exactly 3 content variations. For each variation produce:
- hook: The first 3 seconds of a video — must grab attention instantly (max 15 words)
- script: Full 15–30 second video script (100–150 words)
- caption: Social media caption (max 280 characters, punchy, includes CTA)
- hashtags: 8–12 relevant hashtags as a comma-separated string

Focus exclusively on mobile apps / indie games.
Use one of these hook starters as inspiration (don't copy verbatim): {hook_starters}

Respond ONLY with a JSON array of 3 objects like this:
[
  {{
    "hook": "...",
    "script": "...",
    "caption": "...",
    "hashtags": "#tag1, #tag2, ..."
  }},
  ...
]
""".strip()


# ── Analytics feedback prompt ──────────────────────────────────────────────

CONTENT_IMPROVEMENT_PROMPT = """
You are optimizing social media content based on engagement data.

Previous content that performed well:
{top_performers}

Previous content that performed poorly:
{low_performers}

Trending topic: "{topic}"

Generate 3 improved content variations, learning from the performance patterns above.
Maintain the same JSON format as before.
""".strip()


def build_generation_prompt(topic: str, source: str, viral_format: str = "curiosity_gap") -> str:
    fmt = VIRAL_FORMATS.get(viral_format, VIRAL_FORMATS["curiosity_gap"])
    return CONTENT_GENERATION_PROMPT.format(
        topic=topic,
        source=source,
        format_name=fmt["name"],
        format_description=fmt["description"],
        hook_starters=" | ".join(fmt["hook_starters"]),
    )


def build_improvement_prompt(topic: str, source: str, top_performers: str, low_performers: str) -> str:
    return CONTENT_IMPROVEMENT_PROMPT.format(
        topic=topic,
        source=source,
        top_performers=top_performers,
        low_performers=low_performers,
    )
