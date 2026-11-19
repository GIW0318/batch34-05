import copy

import pytest

import tavern_management as tm

TAVERN = {
    "seats": 4,
    "gold": 50,
    "stock": {"ale": 10, "fish": 5, "herb": 3},
    "reputation": 50,
}
RECIPES = {
    "stew": {"ingredients": {"fish": 2, "herb": 1}, "prep": 3, "price": 12, "rep": 2},
    "ale": {"ingredients": {"ale": 1}, "prep": 0, "price": 4, "rep": 1},
    "pie": {"ingredients": {"fish": 1, "herb": 2}, "prep": 2, "price": 9, "rep": 1},
}
CONFIG = {"patience": 10, "tip_div": 2, "rep_leave": 2, "rep_impatient": 1, "rep_max": 100}


def tavern(data=None):
    return tm.TavernManagement(copy.deepcopy(data or TAVERN), copy.deepcopy(RECIPES), dict(CONFIG))


def test_initial_state():
    st = tavern().state()
    assert st["gold"] == 50
    assert st["reputation"] == 50
    assert st["stock"] == {"ale": 10, "fish": 5, "herb": 3}
    assert st["queue"] == []
    assert st["seated"] == {}


def test_arrive_queues_party():
    t = tavern()
    t.arrive("mira", 2, now=0)
    queue = t.state()["queue"]
    assert len(queue) == 1
    assert queue[0]["party"] == 2


def test_party_larger_than_house_is_rejected():
    t = tavern()
    with pytest.raises(ValueError):
        t.arrive("mira", 5, now=0)


def test_duplicate_arrival_is_rejected():
    t = tavern()
    t.arrive("mira", 2, now=0)
    with pytest.raises(ValueError):
        t.arrive("mira", 2, now=1)


def test_seat_assigns_first_fitting_party():
    t = tavern()
    t.arrive("mira", 2, now=0)
    t.seat(0)
    st = t.state()
    assert "mira" in st["seated"]
    assert st["seated"]["mira"]["party"] == 2
    assert st["queue"] == []


def test_seat_returns_none_when_no_room():
    t = tavern()
    t.arrive("mira", 3, now=0)
    t.arrive("tomas", 2, now=1)
    assert t.seat(0) == "mira"
    assert t.seat(1) is None
    assert [row["name"] for row in t.state()["queue"]] == ["tomas"]


def test_order_requires_seated_customer():
    t = tavern()
    t.arrive("mira", 2, now=0)
    with pytest.raises(ValueError):
        t.order("mira", "stew", now=1)


def test_order_consumes_stock_and_sets_ready_time():
    t = tavern()
    t.arrive("mira", 2, now=0)
    t.seat(0)
    res = t.order("mira", "stew", now=1)
    st = t.state()
    assert res["ok"] is True
    assert res["ready"] == 4
    assert st["stock"]["fish"] == 3
    assert st["stock"]["herb"] == 2


def test_order_without_stock_penalizes_and_frees_seat():
    data = copy.deepcopy(TAVERN)
    data["stock"]["fish"] = 0
    t = tavern(data)
    t.arrive("mira", 2, now=0)
    t.seat(0)
    res = t.order("mira", "stew", now=1)
    st = t.state()
    assert res["ok"] is False
    assert res["reason"] == "stock"
    assert st["seated"] == {}
    assert st["reputation"] == 48


def test_serve_before_ready_is_rejected():
    t = tavern()
    t.arrive("mira", 2, now=0)
    t.seat(0)
    t.order("mira", "stew", now=0)
    with pytest.raises(ValueError):
        t.serve("mira", now=2)


def test_serve_pays_price_and_tip():
    t = tavern()
    t.arrive("mira", 2, now=0)
    t.seat(0)
    t.order("mira", "stew", now=0)
    total = t.serve("mira", now=3)
    st = t.state()
    assert total == 15
    assert st["gold"] == 65
    assert st["reputation"] == 52
    assert st["seated"] == {}


def test_tick_removes_impatient_guest():
    t = tavern()
    t.arrive("mira", 2, now=0)
    t.seat(0)
    left = t.tick(11)
    st = t.state()
    assert left == ["mira"]
    assert st["seated"] == {}
    assert st["reputation"] == 49


def test_tick_removes_guest_with_pending_order():
    t = tavern()
    t.arrive("mira", 2, now=0)
    t.seat(0)
    t.order("mira", "stew", now=1)
    left = t.tick(11)
    st = t.state()
    assert left == ["mira"]
    assert st["seated"] == {}
    assert st["reputation"] == 48


def test_restock_updates_gold_and_stock():
    t = tavern()
    t.restock("fish", 5, 2)
    st = t.state()
    assert st["stock"]["fish"] == 10
    assert st["gold"] == 40
    with pytest.raises(ValueError):
        t.restock("fish", 100, 2)
    with pytest.raises(ValueError):
        t.restock("salt", 1, 1)


def test_reputation_cap_and_detached_state():
    data = copy.deepcopy(TAVERN)
    data["reputation"] = 99
    t = tavern(data)
    for name in ("mira", "tomas"):
        t.arrive(name, 1, now=0)
        t.seat(0)
        t.order(name, "ale", now=0)
        t.serve(name, now=0)
    assert t.state()["reputation"] == 100
    st = t.state()
    st["stock"]["ale"] = 999
    assert t.state()["stock"]["ale"] == 8
