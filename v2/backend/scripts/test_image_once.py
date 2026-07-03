"""One-shot image generation smoke test."""
import asyncio
import sys

from image.config import SILICONFLOW_API_KEY
from image.identity_loader import load_identity
from image.orchestrator import ImageEngineError, generate_character_image
from image.router import route_request
from personality.photo_templates import get_photo_template_meta


async def main(character_id: str = "liu_qingning") -> int:
    print("SILICONFLOW_API_KEY configured:", bool(SILICONFLOW_API_KEY))
    meta = get_photo_template_meta(character_id)
    ident = load_identity(character_id)
    ref = (ident or {}).get("reference_image_path")
    route = route_request(
        character_id=character_id,
        reference_path=ref,
        style="selfie",
    )
    print(f"character: {character_id}")
    print(f"template: {meta.get('template')}")
    print(f"reference_file: {ref}")
    print(f"model: {route.model} ({route.reason})")
    try:
        result = await generate_character_image(
            character_id,
            scene="bedroom",
            style="selfie",
            emotion="shy smile",
            exposure="casual_home",
            extra="natural selfie looking at camera",
            priority="quality",
        )
    except ImageEngineError as exc:
        print("FAILED:", exc)
        return 1
    print("SUCCESS url:", result.get("url"))
    print("route:", result.get("route"))
    return 0


if __name__ == "__main__":
    cid = sys.argv[1] if len(sys.argv) > 1 else "liu_qingning"
    raise SystemExit(asyncio.run(main(cid)))
