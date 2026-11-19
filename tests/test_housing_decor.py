import copy

import pytest

import housing_decor as hd

HOUSES = {
    "h1": {
        "owner": "alice",
        "members": {"alice": "owner", "bob": "roommate", "erin": "visitor"},
        "rooms": {
            "living": {"w": 4, "h": 3, "theme": "modern", "locked": False},
            "den": {"w": 3, "h": 3, "theme": "rustic", "locked": True},
        },
        "placed": [],
    }
}
FURNITURE = {
    "sofa": {"w": 2, "h": 1, "comfort": 5, "set": "modern", "themes": ["modern"], "rooms": ["living"]},
    "lamp": {"w": 1, "h": 1, "comfort": 2, "set": "modern", "themes": ["modern"], "rooms": ["living", "den"]},
    "rug": {"w": 2, "h": 2, "comfort": 3, "set": "rustic", "themes": ["rustic"], "rooms": ["living", "den"]},
    "stove": {"w": 1, "h": 1, "comfort": 4, "set": "rustic", "themes": ["rustic"], "rooms": ["den"]},
}
CONFIG = {"comfort_cap": 30, "set_bonus": 5, "set_min": 2, "theme_bonus": 1}


def house():
    return hd.HousingDecor(copy.deepcopy(HOUSES), copy.deepcopy(FURNITURE), dict(CONFIG))


def test_initial_state():
    st = house().state()
    assert st["houses"]["h1"]["members"]["bob"] == "roommate"
    assert st["houses"]["h1"]["placed"] == []


def test_visitor_cannot_place():
    h = house()
    with pytest.raises(ValueError):
        h.place("h1", "living", "erin", "lamp", 0, 0)


def test_roommate_can_place():
    h = house()
    h.place("h1", "living", "bob", "lamp", 0, 0)
    placed = h.state()["houses"]["h1"]["placed"]
    assert len(placed) == 1
    assert placed[0]["item"] == "lamp"


def test_unknown_room_and_item_are_rejected():
    h = house()
    with pytest.raises(ValueError):
        h.place("h1", "garage", "alice", "lamp", 0, 0)
    with pytest.raises(ValueError):
        h.place("h1", "living", "alice", "throne", 0, 0)


def test_item_must_fit_room_kind():
    h = house()
    with pytest.raises(ValueError):
        h.place("h1", "living", "alice", "stove", 0, 0)


def test_out_of_bounds_is_rejected():
    h = house()
    with pytest.raises(ValueError):
        h.place("h1", "living", "alice", "sofa", 3, 0)


def test_overlap_is_rejected():
    h = house()
    h.place("h1", "living", "alice", "sofa", 0, 0)
    with pytest.raises(ValueError):
        h.place("h1", "living", "alice", "sofa", 1, 0)


def test_adjacent_placement_is_allowed():
    h = house()
    h.place("h1", "living", "alice", "sofa", 0, 0)
    h.place("h1", "living", "alice", "sofa", 2, 0)
    assert len(h.state()["houses"]["h1"]["placed"]) == 2


def test_locked_room_blocks_roommate_only():
    h = house()
    with pytest.raises(ValueError):
        h.place("h1", "den", "bob", "lamp", 0, 0)
    h.place("h1", "den", "alice", "lamp", 0, 0)
    assert h.state()["houses"]["h1"]["placed"][0]["room"] == "den"


def test_grant_requires_owner():
    h = house()
    with pytest.raises(ValueError):
        h.grant("h1", "bob", "carol", "roommate")


def test_grant_adds_member_and_rejects_bad_role():
    h = house()
    h.grant("h1", "alice", "carol", "roommate")
    assert h.state()["houses"]["h1"]["members"]["carol"] == "roommate"
    with pytest.raises(ValueError):
        h.grant("h1", "alice", "carol", "roommate")
    with pytest.raises(ValueError):
        h.grant("h1", "alice", "dave", "owner")


def test_revoke_removes_permission():
    h = house()
    h.revoke("h1", "alice", "bob")
    with pytest.raises(ValueError):
        h.place("h1", "living", "bob", "lamp", 0, 0)
    with pytest.raises(ValueError):
        h.revoke("h1", "alice", "alice")


def test_remove_by_id():
    h = house()
    pid = h.place("h1", "living", "bob", "lamp", 0, 0)["id"]
    h.remove("h1", "living", "bob", pid)
    assert h.state()["houses"]["h1"]["placed"] == []
    with pytest.raises(ValueError):
        h.remove("h1", "living", "bob", 99)


def test_comfort_counts_theme_and_set_bonus():
    h = house()
    h.place("h1", "living", "alice", "sofa", 0, 0)
    h.place("h1", "living", "alice", "lamp", 2, 0)
    assert h.comfort("h1") == 14


def test_comfort_cap_and_detached_state():
    cfg = dict(CONFIG)
    cfg["comfort_cap"] = 10
    h = hd.HousingDecor(copy.deepcopy(HOUSES), copy.deepcopy(FURNITURE), cfg)
    h.place("h1", "living", "alice", "sofa", 0, 0)
    h.place("h1", "living", "alice", "lamp", 2, 0)
    assert h.comfort("h1") == 10
    st = h.state()
    st["houses"]["h1"]["members"]["bob"] = "owner"
    assert h.state()["houses"]["h1"]["members"]["bob"] == "roommate"
