"""Image exposure fallback when SiliconFlow content filter triggers."""

from __future__ import annotations

EXPOSURE_FALLBACK_CHAIN: dict[str, list[str]] = {
    "nude": ["partial", "towel", "sleepwear", "casual_home", "full_clothed"],
    "implied": ["partial", "towel", "sleepwear", "casual_home"],
    "partial": ["towel", "sleepwear", "casual_home", "full_clothed"],
    "towel": ["sleepwear", "casual_home", "full_clothed"],
    "sleepwear": ["casual_home", "full_clothed"],
    "casual_home": ["full_clothed"],
}


def fallback_exposures(exposure: str) -> list[str]:
    """Ordered softer exposures to try after a content-filter failure."""
    chain = EXPOSURE_FALLBACK_CHAIN.get(exposure, [])
    return [e for e in chain if e != exposure]


def is_content_filter_error(exc: Exception) -> bool:
    msg = str(exc).lower()
    return "451" in msg or "prohibited" in msg or "sensitive content" in msg
