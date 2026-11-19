import copy

import pytest

import racing_weather as rw

TRACK = {
    "name": "coast",
    "laps": 2,
    "checkpoints": [
        {"surface": "asphalt", "base": 10},
        {"surface": "gravel", "base": 12},
        {"surface": "asphalt", "base": 8},
    ],
}
CARS = {
    "falcon": {"penalty_bonus": 0},
    "viper": {"penalty_bonus": 1},
}
PENALTIES = {
    "dry": {
        "slick": {"asphalt": 0, "gravel": 3},
        "wet": {"asphalt": 1, "gravel": 2},
        "offroad": {"asphalt": 2, "gravel": 0},
    },
    "rain": {
        "slick": {"asphalt": 4, "gravel": 5},
        "wet": {"asphalt": 0, "gravel": 2},
        "offroad": {"asphalt": 3, "gravel": 0},
    },
    "storm": {
        "slick": {"asphalt": 8, "gravel": 9},
        "wet": {"asphalt": 3, "gravel": 4},
        "offroad": {"asphalt": 5, "gravel": 1},
    },
}
CONFIG = {"penalties": PENALTIES}
LAP_TIMES = [10, 22, 30, 40, 52, 60]


def race():
    return rw.RacingWeather(copy.deepcopy(TRACK), copy.deepcopy(CARS), copy.deepcopy(CONFIG))


def run_laps(r, driver, start=0, times=None):
    times = list(times or LAP_TIMES)
    r.start(driver, start)
    for i, t in enumerate(times):
        r.checkpoint(driver, i % 3, t)


def test_initial_state():
    r = race()
    st = r.state()
    assert st["weather"] == "dry"
    assert r.leaderboard() == []


def test_register_and_duplicate():
    r = race()
    r.register("ann", "falcon", "slick")
    assert r.state()["drivers"]["ann"]["tire"] == "slick"
    with pytest.raises(ValueError):
        r.register("ann", "viper", "wet")


def test_unknown_car_or_tire_is_rejected():
    r = race()
    with pytest.raises(ValueError):
        r.register("ann", "hover", "slick")
    with pytest.raises(ValueError):
        r.register("ann", "falcon", "spikes")


def test_start_sets_running():
    r = race()
    r.register("ann", "falcon", "slick")
    r.start("ann", 0)
    st = r.state()["drivers"]["ann"]
    assert st["status"] == "running"
    assert st["started"] == 0


def test_checkpoint_before_start_is_rejected():
    r = race()
    r.register("ann", "falcon", "slick")
    with pytest.raises(ValueError):
        r.checkpoint("ann", 0, 5)


def test_checkpoint_order_is_enforced():
    r = race()
    r.register("ann", "falcon", "slick")
    r.start("ann", 0)
    with pytest.raises(ValueError):
        r.checkpoint("ann", 1, 10)


def test_checkpoint_time_must_increase():
    r = race()
    r.register("ann", "falcon", "slick")
    r.start("ann", 0)
    r.checkpoint("ann", 0, 10)
    with pytest.raises(ValueError):
        r.checkpoint("ann", 1, 10)


def test_two_laps_of_checkpoints():
    r = race()
    r.register("ann", "falcon", "slick")
    run_laps(r, "ann")
    st = r.state()["drivers"]["ann"]
    assert len(st["checkpoints"]) == 6
    assert st["lap"] == 2
    assert st["next_cp"] == 0


def test_finish_before_all_checkpoints_is_rejected():
    r = race()
    r.register("ann", "falcon", "slick")
    r.start("ann", 0)
    r.checkpoint("ann", 0, 10)
    with pytest.raises(ValueError):
        r.finish("ann", 20)


def test_finish_adds_dry_penalty():
    r = race()
    r.register("ann", "falcon", "slick")
    run_laps(r, "ann")
    r.finish("ann", 70)
    entry = r.leaderboard()[0]
    assert entry["total"] == 70
    assert entry["penalty"] == 6
    assert entry["final"] == 76


def test_rain_penalizes_slick_tires():
    r = race()
    r.register("ann", "falcon", "slick")
    r.set_weather("rain", 0)
    run_laps(r, "ann")
    r.finish("ann", 70)
    assert r.leaderboard()[0]["final"] == 96


def test_offroad_tire_is_better_in_rain():
    r = race()
    r.register("ann", "falcon", "offroad")
    r.set_weather("rain", 0)
    run_laps(r, "ann")
    r.finish("ann", 70)
    assert r.leaderboard()[0]["final"] == 82


def test_weather_change_applies_only_to_later_segments():
    r = race()
    r.register("ann", "falcon", "slick")
    r.start("ann", 0)
    for i, t in enumerate([10, 22, 30]):
        r.checkpoint("ann", i, t)
    r.set_weather("rain", 35)
    for i, t in enumerate([40, 52, 60]):
        r.checkpoint("ann", i, t)
    r.finish("ann", 70)
    entry = r.leaderboard()[0]
    assert entry["penalty"] == 16
    assert entry["final"] == 86


def test_leaderboard_orders_finishers_and_marks_dnf():
    r = race()
    for name in ("ann", "ben", "cid"):
        r.register(name, "falcon", "slick")
    run_laps(r, "ann")
    r.finish("ann", 70)
    run_laps(r, "ben", times=[12, 26, 36, 48, 62, 72])
    r.finish("ben", 80)
    r.start("cid", 100)
    board = r.leaderboard()
    assert [row["driver"] for row in board] == ["ann", "ben", "cid"]
    assert board[2]["status"] == "dnf"
    assert board[2]["final"] is None


def test_double_finish_is_rejected_and_state_is_detached():
    r = race()
    r.register("ann", "falcon", "slick")
    run_laps(r, "ann")
    r.finish("ann", 70)
    with pytest.raises(ValueError):
        r.finish("ann", 80)
    st = r.state()
    st["drivers"]["ann"]["tire"] = "wet"
    assert r.state()["drivers"]["ann"]["tire"] == "slick"
