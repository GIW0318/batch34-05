import copy

import pytest

import fishing_tournament as ft

ANGLERS = {
    "mira": {"stamina": 30, "bait": {"worm": 2, "lure": 1}},
    "tomas": {"stamina": 30, "bait": {"worm": 1, "lure": 1}},
    "weak": {"stamina": 3, "bait": {"worm": 1}},
    "bare": {"stamina": 20, "bait": {}},
}
ZONES = {
    "lake": {
        "species": [
            {"name": "carp", "points": 10, "stamina": 4, "bait": "worm", "weathers": ["calm", "rain"]},
            {"name": "pike", "points": 14, "stamina": 5, "bait": "lure", "weathers": ["calm", "rain"]},
        ]
    },
    "deep": {
        "species": [
            {"name": "anglerfish", "points": 30, "stamina": 6, "bait": "lure", "weathers": ["rain"]},
        ]
    },
    "reef": {
        "species": [
            {"name": "ray", "points": 20, "stamina": 6, "bait": "lure", "weathers": ["storm"]},
        ]
    },
}
CONFIG = {"deadline": 100, "pot": 1000, "payout_bps": [6000, 4000], "storm_extra": 3}


def tour():
    return ft.FishingTournament(copy.deepcopy(ANGLERS), copy.deepcopy(ZONES), dict(CONFIG))


def test_open_sets_status():
    t = tour()
    t.open(0)
    st = t.state()
    assert st["status"] == "open"
    assert st["weather"] == "calm"


def test_cast_before_open_is_rejected():
    t = tour()
    with pytest.raises(ValueError):
        t.cast("mira", "lake", now=1)


def test_unknown_angler_is_rejected():
    t = tour()
    t.open(0)
    with pytest.raises(ValueError):
        t.cast("ghost", "lake", now=1)


def test_unknown_zone_is_rejected():
    t = tour()
    t.open(0)
    with pytest.raises(ValueError):
        t.cast("mira", "volcano", now=1)


def test_cast_consumes_stamina_and_bait():
    t = tour()
    t.open(0)
    got = t.cast("mira", "lake", now=1)
    st = t.state()
    assert got["species"] == "carp"
    assert got["points"] == 10
    assert st["anglers"]["mira"]["stamina"] == 26
    assert st["anglers"]["mira"]["bait"] == {"worm": 1, "lure": 1}
    assert st["anglers"]["mira"]["score"] == 10
    assert len(st["anglers"]["mira"]["catches"]) == 1


def test_species_rotates_per_zone():
    t = tour()
    t.open(0)
    t.cast("mira", "lake", now=1)
    second = t.cast("mira", "lake", now=2)
    st = t.state()
    assert second["species"] == "pike"
    assert second["points"] == 14
    assert st["anglers"]["mira"]["stamina"] == 21
    assert st["anglers"]["mira"]["score"] == 24
    assert [c["species"] for c in st["anglers"]["mira"]["catches"]] == ["carp", "pike"]


def test_weather_blocks_wrong_species():
    t = tour()
    t.open(0)
    with pytest.raises(ValueError):
        t.cast("mira", "deep", now=1)


def test_rain_doubles_points():
    t = tour()
    t.open(0)
    t.set_weather("rain", now=1)
    got = t.cast("mira", "lake", now=2)
    assert got["points"] == 20
    assert t.state()["weather"] == "rain"


def test_storm_adds_stamina_cost():
    t = tour()
    t.open(0)
    t.set_weather("storm", now=1)
    t.cast("mira", "reef", now=2)
    assert t.state()["anglers"]["mira"]["stamina"] == 21


def test_insufficient_stamina_is_rejected():
    t = tour()
    t.open(0)
    with pytest.raises(ValueError):
        t.cast("weak", "lake", now=1)


def test_missing_bait_is_rejected():
    t = tour()
    t.open(0)
    with pytest.raises(ValueError):
        t.cast("bare", "lake", now=1)


def test_deadline_blocks_cast():
    t = tour()
    t.open(0)
    with pytest.raises(ValueError):
        t.cast("mira", "lake", now=101)


def test_leaderboard_breaks_ties_by_name():
    t = tour()
    t.open(0)
    t.cast("mira", "lake", now=1)
    t.cast("tomas", "lake", now=2)
    board = t.leaderboard()
    assert [row["angler"] for row in board[:2]] == ["mira", "tomas"]
    assert [row["score"] for row in board[:2]] == [10, 10]


def test_settle_pays_ranks():
    t = tour()
    t.open(0)
    t.cast("mira", "lake", now=1)
    t.cast("tomas", "lake", now=2)
    t.close(50)
    t.settle()
    st = t.state()
    assert st["status"] == "settled"
    assert st["payouts"] == {"mira": 600, "tomas": 400}


def test_settle_twice_is_rejected_and_state_is_detached():
    t = tour()
    t.open(0)
    t.cast("mira", "lake", now=1)
    t.close(50)
    t.settle()
    with pytest.raises(ValueError):
        t.settle()
    st = t.state()
    st["anglers"]["mira"]["score"] = 999
    assert t.state()["anglers"]["mira"]["score"] == 10
