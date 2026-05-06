"""
Media Generation Service (MVP)
Uses Pillow to generate text-overlay images as video thumbnails/placeholders.
FFmpeg integration scaffolded for real video generation.
"""

import os
import logging
import textwrap
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

MEDIA_DIR = Path("/tmp/social_media_assets")
MEDIA_DIR.mkdir(exist_ok=True)

# Colour palettes for variation branding
PALETTES = [
    {"bg": (15, 15, 35), "text": (255, 220, 50), "accent": (255, 80, 80)},
    {"bg": (20, 20, 20), "text": (255, 255, 255), "accent": (100, 200, 255)},
    {"bg": (240, 240, 240), "text": (20, 20, 20), "accent": (80, 180, 80)},
]


def generate_text_image(hook: str, variation_index: int = 0, width: int = 1080, height: int = 1920) -> Optional[str]:
    """Generate a 9:16 vertical image with hook text overlay. Returns file path."""
    try:
        from PIL import Image, ImageDraw, ImageFont

        palette = PALETTES[variation_index % len(PALETTES)]
        img = Image.new("RGB", (width, height), color=palette["bg"])
        draw = ImageDraw.Draw(img)

        # Accent bar at top
        draw.rectangle([0, 0, width, 12], fill=palette["accent"])
        draw.rectangle([0, height - 12, width, height], fill=palette["accent"])

        # Try to use a bundled font; fall back to default
        try:
            font_large = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", 72)
            font_small = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", 42)
        except OSError:
            font_large = ImageFont.load_default()
            font_small = font_large

        # Wrap hook text
        lines = textwrap.wrap(hook, width=20)
        y = height // 3
        for line in lines:
            bbox = draw.textbbox((0, 0), line, font=font_large)
            text_w = bbox[2] - bbox[0]
            draw.text(((width - text_w) // 2, y), line, font=font_large, fill=palette["text"])
            y += 90

        # Watermark
        watermark = "social-automation-mvp"
        wm_bbox = draw.textbbox((0, 0), watermark, font=font_small)
        draw.text(
            ((width - (wm_bbox[2] - wm_bbox[0])) // 2, height - 80),
            watermark,
            font=font_small,
            fill=(*palette["accent"], 128),
        )

        out_path = MEDIA_DIR / f"post_v{variation_index}_{abs(hash(hook))}.png"
        img.save(str(out_path), "PNG")
        logger.info(f"Generated image: {out_path}")
        return str(out_path)
    except ImportError:
        logger.warning("Pillow not installed — skipping image generation")
        return None
    except Exception as e:
        logger.error(f"Image generation failed: {e}")
        return None


def generate_video_script_file(hook: str, script: str, variation_index: int = 0) -> Optional[str]:
    """
    Write an FFmpeg-ready script placeholder.
    Real video generation requires stock footage; scaffold is provided.
    """
    out_path = MEDIA_DIR / f"script_v{variation_index}_{abs(hash(hook))}.txt"
    content = f"""# AUTO-GENERATED VIDEO SCRIPT
# Variation: {variation_index}
# Hook (0–3s): {hook}

--- SCRIPT ---
{script}

--- FFMPEG COMMAND (placeholder) ---
# ffmpeg -i background.mp4 -vf "drawtext=text='{hook}':fontsize=72:x=(w-text_w)/2:y=h/3:fontcolor=white" output.mp4
"""
    out_path.write_text(content)
    return str(out_path)
