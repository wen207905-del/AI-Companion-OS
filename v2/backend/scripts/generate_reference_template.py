"""Generate character reference portraits matching user template aesthetic.

User refs (config/character_templates/*.jpg) are photorealistic full-body nude
gravure-style images — not anime/clothed portraits.
"""
from __future__ import annotations

import argparse
import asyncio
import sys
from pathlib import Path

import httpx

from config import PROJECT_ROOT
from image.config import DEFAULT_NEGATIVE, SILICONFLOW_API_KEY
from image.identity_loader import load_identity
from image.prompt_loader import get_character_base_prompt
from image.router import route_request
from image.siliconflow import SiliconFlowError, generate_image

TEMPLATE_DIR = PROJECT_ROOT / "config" / "character_templates"

# Best-looking user ref for style anchoring (photoreal gravure aesthetic)
DEFAULT_STYLE_REF = TEMPLATE_DIR / "ba0366a7e909f65fe4b4947768dd5993.jpg"

PHOTOREAL_PREFIX = (
    "masterpiece, best quality, ultra high resolution, 8k uhd, photorealistic, "
    "hyperrealistic, raw photo, professional fashion portrait photography, "
    "stunning peerless East Asian beauty, flawless symmetrical face, "
    "luminous expressive eyes with long thick lashes, perfect nose and lips, "
    "flawless porcelain skin with subtle subsurface scattering, "
)

PHOTOREAL_BODY = (
    "full body portrait, elegant fitted black silk evening dress, "
    "curvy hourglass silhouette, long slender legs, graceful posture, "
)

PHOTOREAL_SCENE = (
    "standing facing camera, arms relaxed at sides, soft studio diffused lighting, "
    "neutral minimalist interior background with soft architectural bokeh, "
    "shallow depth of field, extremely detailed skin texture, subtle film grain, "
    "single subject centered, no watermark, no text"
)

REFERENCE_NEGATIVE = (
    f"{DEFAULT_NEGATIVE}, anime, cartoon, chibi, illustration, 3d render, "
    "painting, drawing, cel shaded, plastic skin, doll, ugly, plain face, "
    "average looking, asymmetrical face, clothes, bra, panties, censored bar, "
    "oversaturated, harsh lighting, busy background"
)


def _build_reference_prompt(character_id: str, emotion: str, pose: str) -> str:
    base = get_character_base_prompt(character_id)
    identity = load_identity(character_id) or {}
    face = identity.get("face_prompt_en", "")
    hair = identity.get("hair_default", "")
    marks = identity.get("distinctive_marks", "")

    parts = [
        PHOTOREAL_PREFIX,
        base + "." if base else "",
        face + "." if face else "",
        hair + "." if hair else "",
        marks + "." if marks else "",
        PHOTOREAL_BODY,
        f"Expression: {emotion}.",
        f"Pose: {pose}.",
        PHOTOREAL_SCENE,
    ]
    return " ".join(p for p in parts if p)


async def generate_reference(
    character_id: str,
    *,
    style_ref: Path | None = None,
    use_style_ref: bool = True,
    emotion: str = "",
    pose: str = "",
) -> Path:
    if not SILICONFLOW_API_KEY:
        raise SystemExit("SILICONFLOW_API_KEY not configured in .env")

    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)
    dest = TEMPLATE_DIR / f"{character_id}.jpg"

    default_emotions = {
        "ye_ruxue": "cold distant aloof icy beauty, rarely smiles, penetrating gaze slightly narrowed",
        "bai_rou": "warm gentle inviting soft smile, caring eyes, head slightly tilted",
        "gu_wanqing": "cool confident sharp gaze, composed elegant expression",
        "liu_qingning": "bright cheerful youthful smile, energetic lively eyes",
        "shen_man": "lazy cat-like half-lidded gaze, sensual relaxed expression",
        "lin_tangtang": "confident playful smirk, bold flirtatious eyes",
        "su_nian": "wistful dreamy gentle smile, poetic melancholic gaze",
        "xingye_liuli": "pure innocent doll-like gaze, soft shy expression",
        "xiao_ying": "radiant healing smile, warm cute expression",
        "mo_xiaoran": "yandere soft smile, fragile melancholic eyes",
        "hua_li": "clingy cute pout, puppy eyes looking up",
        "wang_dahai": "relaxed brotherly smirk, confident masculine gaze",
    }
    default_poses = {
        "wang_dahai": "standing facing camera, athletic masculine posture, arms at sides",
    }
    emotion = emotion or default_emotions.get(
        character_id, "natural relaxed expression, looking at viewer"
    )
    pose = pose or default_poses.get(
        character_id, "standing straight facing camera, full body visible head to mid-thigh"
    )

    prompt = _build_reference_prompt(character_id, emotion, pose)

    ref_path: str | None = None
    if use_style_ref:
        chosen = style_ref if style_ref and style_ref.is_file() else DEFAULT_STYLE_REF
        if chosen.is_file():
            ref_path = str(chosen)

    route = route_request(
        character_id=character_id,
        style="cinematic_portrait" if not ref_path else "full_body",
        exposure="partial" if ref_path else "full_clothed",
        reference_path=ref_path,
        priority="quality",
    )
    print(f"Generating reference for {character_id}...")
    print(f"Model: {route.model} ({route.reason})")
    print(f"Style ref: {ref_path or '(none)'}")
    print(f"Prompt preview: {prompt[:240]}...")

    result = await generate_image(
        prompt,
        REFERENCE_NEGATIVE,
        route,
        seed=(load_identity(character_id) or {}).get("identity_seed"),
    )
    image_url = result["image_url"]
    print(f"Remote URL: {image_url[:120]}...")

    if image_url.startswith("data:"):
        import base64

        b64 = image_url.split(",", 1)[-1]
        dest.write_bytes(base64.b64decode(b64))
    else:
        async with httpx.AsyncClient(timeout=120) as client:
            resp = await client.get(image_url)
            resp.raise_for_status()
            dest.write_bytes(resp.content)

    print(f"Saved: {dest} ({dest.stat().st_size // 1024} KB)")
    return dest


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate character reference template")
    parser.add_argument("character_id", nargs="?", default="ye_ruxue")
    parser.add_argument(
        "--style-ref",
        type=Path,
        default=None,
        help="User ref JPG to anchor photoreal gravure aesthetic",
    )
    parser.add_argument("--no-style-ref", action="store_true", help="Pure text2img, no img2img")
    args = parser.parse_args()

    style_ref = None if args.no_style_ref else args.style_ref
    try:
        asyncio.run(
            generate_reference(
                args.character_id,
                style_ref=args.style_ref,
                use_style_ref=not args.no_style_ref,
            )
        )
    except SiliconFlowError as exc:
        print("FAILED:", exc)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
