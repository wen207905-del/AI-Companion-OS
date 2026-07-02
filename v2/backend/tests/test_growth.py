"""Growth engine tests."""

from engine.growth_engine import GrowthEngine


def test_growth_xp_and_level(memory_db):
    engine = GrowthEngine(memory_db)
    p1 = engine.add_xp("bai_rou", 50)
    assert p1["xp"] == 50
    assert p1["level"] == 1
    p2 = engine.add_xp("bai_rou", 60)
    assert p2["level"] >= 2
    profile = engine.get_profile("bai_rou")
    assert profile["xp"] == 110
