"""Tests for image exposure fallback."""

from image.exposure_fallback import fallback_exposures, is_content_filter_error


def test_fallback_chain_nude():
    chain = fallback_exposures("nude")
    assert chain[0] == "partial"
    assert "full_clothed" in chain


def test_content_filter_detection():
    assert is_content_filter_error(Exception('SiliconFlow API 451: prohibited'))
    assert not is_content_filter_error(Exception("timeout"))
