import copy

import pytest

import farming_seasons as fs

FARM = {
    "gold": 100,
    "season": "spring",
    "day": 0,
    "weather": "sunny",
    "inventory": {"tomato": 3},
    "plots": {
        "p1": {"kind": "field", "crop": None, "growth": 0, "water": 1, "health": 2},
        "p2": {"kind": "field", "crop": None, "growth": 0, "water": 1, "health": 2},
        "g1": {"kind": "greenhouse", "crop": None, "growth": 0, "water": 1, "health": 2},
    },
}
CROPS = {
    "wheat": {"seasons": ["spring", "summer"], "days": 4, "yield": 6, "seed": 10, "price": 5, "hardy": True},
    "tomato": {"seasons": ["summer"], "days": 3, "yield": 4, "seed": 15, "price": 9, "hardy": False},
    "pumpkin": {"seasons": ["autumn"], "days": 5, "yield": 8, "seed": 20, "price": 12, "hardy": True},
}
CONFIG = {"season_days": 3, "rain_bonus": 1, "drought_penalty": 1, "greenhouse_bonus": 1}


def farm():
    return fs.FarmSeasons(copy.deepcopy(FARM), copy.deepcopy(CROPS), dict(CONFIG))


def test_initial_state():
    st = farm().state()
    assert st["season"] == "spring"
    assert st["day"] == 0
    assert st["weather"] == "sunny"
    assert st["gold"] == 100
    assert st["inventory"] == {"tomato": 3}
    assert st["plots"]["p1"]["crop"] is None


def test_unknown_crop_is_rejected():
    f = farm()
    with pytest.raises(ValueError):
        f.plant("p1", "banana")


def test_off_season_field_is_rejected():
    f = farm()
    with pytest.raises(ValueError):
        f.plant("p1", "tomato")


def test_greenhouse_allows_off_season():
    f = farm()
    f.plant("g1", "tomato")
    assert f.state()["plots"]["g1"]["crop"] == "tomato"


def test_plant_charges_seed_and_rejects_duplicate():
    f = farm()
    f.plant("p1", "wheat")
    assert f.state()["gold"] == 90
    with pytest.raises(ValueError):
        f.plant("p1", "wheat")


def test_insufficient_gold_is_rejected():
    data = copy.deepcopy(FARM)
    data["gold"] = 5
    f = fs.FarmSeasons(data, copy.deepcopy(CROPS), dict(CONFIG))
    with pytest.raises(ValueError):
        f.plant("p1", "wheat")


def test_sunny_day_grows_in_season_crop():
    f = farm()
    f.plant("p1", "wheat")
    f.next_day("sunny")
    st = f.state()
    assert st["plots"]["p1"]["growth"] == 2
    assert st["plots"]["p1"]["water"] == 0


def test_rain_day_adds_growth_and_water():
    f = farm()
    f.plant("p1", "wheat")
    f.next_day("rain")
    st = f.state()
    assert st["plots"]["p1"]["growth"] == 3
    assert st["plots"]["p1"]["water"] == 2


def test_drought_day_reduces_growth():
    f = farm()
    f.plant("p1", "wheat")
    f.next_day("drought")
    assert f.state()["plots"]["p1"]["growth"] == 1


def test_irrigate_raises_water_with_cap():
    f = farm()
    f.plant("p1", "wheat")
    f.irrigate("p1")
    f.irrigate("p1")
    assert f.state()["plots"]["p1"]["water"] == 3


def test_frost_kills_tender_crop():
    data = copy.deepcopy(FARM)
    data["season"] = "summer"
    f = fs.FarmSeasons(data, copy.deepcopy(CROPS), dict(CONFIG))
    f.plant("p1", "tomato")
    f.next_day("frost")
    assert f.state()["plots"]["p1"]["crop"] == "tomato"
    assert f.state()["plots"]["p1"]["health"] == 1
    f.next_day("frost")
    assert f.state()["plots"]["p1"]["crop"] is None


def test_frost_spares_hardy_crop():
    f = farm()
    f.plant("p1", "wheat")
    f.next_day("frost")
    f.next_day("frost")
    st = f.state()["plots"]["p1"]
    assert st["crop"] == "wheat"
    assert st["health"] == 2


def test_harvest_too_early_is_rejected():
    f = farm()
    f.plant("p1", "wheat")
    f.next_day("sunny")
    with pytest.raises(ValueError):
        f.harvest("p1")


def test_harvest_adds_in_season_bonus_and_clears_plot():
    f = farm()
    f.plant("p1", "wheat")
    f.next_day("sunny")
    f.next_day("sunny")
    f.harvest("p1")
    st = f.state()
    assert st["inventory"]["wheat"] == 8
    assert st["plots"]["p1"]["crop"] is None
    assert st["plots"]["p1"]["growth"] == 0


def test_market_price_and_sell_and_detached_state():
    f = farm()
    assert f.price("tomato") == 18
    f.sell("tomato", 2)
    st = f.state()
    assert st["gold"] == 136
    assert st["inventory"]["tomato"] == 1
    with pytest.raises(ValueError):
        f.sell("tomato", 5)
    st["gold"] = 0
    assert f.state()["gold"] == 136
