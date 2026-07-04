"""Tests for anti_repeat_service."""

from services.anti_repeat_service import (
    contains_forbidden,
    is_too_similar,
    similarity,
)


def test_similarity_identical():
    assert similarity("我刚把汤温着", "我刚把汤温着") == 1.0


def test_similarity_different():
    assert similarity("我刚点了烧烤", "做完题脑子快炸了") < 0.4


def test_is_too_similar_blocks_template_variants():
    recent = ["你是不是忘了我，想你了"]
    assert is_too_similar("你是不是忘了我？想你了呀", recent, threshold=0.7)


def test_contains_forbidden():
    phrases = ["想你了", "是不是忘了"]
    assert contains_forbidden("在吗，想你了", phrases)
    assert not contains_forbidden("我刚把汤温着，等你忙完", phrases)
