import copy

import pytest

import card_deck as cd

COLLECTION = {
    "alice": {"strike": 3, "guard": 2, "fireball": 2, "dragon": 1},
    "bob": {"strike": 4, "guard": 2, "fireball": 2},
    "carol": {"strike": 8},
}
CARDS = {
    "strike": {"rarity": "common", "attack": 3, "heal": 0},
    "guard": {"rarity": "common", "attack": 1, "heal": 2},
    "fireball": {"rarity": "epic", "attack": 5, "heal": 0},
    "dragon": {"rarity": "legendary", "attack": 8, "heal": 0},
}
ALICE_DECK = ["strike", "strike", "strike", "guard", "guard", "fireball", "fireball", "dragon"]
BOB_DECK = ["strike", "strike", "strike", "strike", "guard", "guard", "fireball", "fireball"]
BASE = {
    "deck_size": 8,
    "max_duplicates": 2,
    "epic_max": 2,
    "legendary_max": 1,
    "hero_hp": 20,
    "rounds": 6,
}


def game(config=None):
    cfg = dict(BASE)
    if config:
        cfg.update(config)
    return cd.CardDeck(copy.deepcopy(COLLECTION), copy.deepcopy(CARDS), cfg)


def test_register_adds_copies():
    g = game()
    g.register("dave", "strike", 2)
    assert g.state()["players"]["dave"]["strike"] == 2


def test_register_unknown_card_is_rejected():
    g = game()
    with pytest.raises(ValueError):
        g.register("dave", "meteor", 1)


def test_register_nonpositive_qty_is_rejected():
    g = game()
    with pytest.raises(ValueError):
        g.register("dave", "strike", 0)


def test_build_requires_exact_size():
    g = game()
    with pytest.raises(ValueError):
        g.build("alice", ALICE_DECK[:7])


def test_build_rejects_unowned_cards():
    g = game()
    with pytest.raises(ValueError):
        g.build("bob", BOB_DECK[:7] + ["dragon"])


def test_build_enforces_duplicate_cap():
    g = game()
    with pytest.raises(ValueError):
        g.build("carol", ["strike"] * 8)


def test_build_enforces_legendary_cap():
    g = game()
    g.register("alice", "dragon", 1)
    deck = ["dragon", "dragon", "strike", "strike", "strike", "guard", "guard", "fireball"]
    with pytest.raises(ValueError):
        g.build("alice", deck)


def test_build_stores_deck_copy():
    g = game()
    g.build("alice", ALICE_DECK)
    st = g.state()
    assert st["decks"]["alice"] == ALICE_DECK
    assert st["players"]["alice"]["strike"] == 3


def test_build_rejects_unknown_card():
    g = game()
    with pytest.raises(ValueError):
        g.build("carol", ["ghost"] + ["strike"] * 7)


def test_duel_requires_both_decks():
    g = game()
    with pytest.raises(ValueError):
        g.duel("carol", "bob")


def test_duel_damages_lower_attack_side():
    g = game({"rounds": 3})
    g.build("alice", ["dragon"] + ALICE_DECK[:7])
    g.build("carol", ["strike"] * 8)
    res = g.duel("alice", "carol")
    assert res["winner"] == "alice"
    assert res["hp"]["carol"] == 5
    assert res["hp"]["alice"] == 20


def test_tie_round_deals_no_damage():
    g = game({"rounds": 1})
    g.build("alice", ALICE_DECK)
    g.build("carol", ["strike"] * 8)
    res = g.duel("alice", "carol")
    assert res["log"][0]["damage"] == 0
    assert res["winner"] is None


def test_heal_is_capped_at_hero_max():
    g = game({"rounds": 1})
    g.build("alice", ["guard", "guard", "strike", "strike", "strike", "fireball", "fireball", "dragon"])
    g.build("carol", ["strike"] * 8)
    res = g.duel("alice", "carol")
    assert res["log"][0]["heal_a"] == 2
    assert res["hp"]["alice"] == 20


def test_build_enforces_epic_cap():
    g = game()
    g.register("alice", "fireball", 1)
    deck = ["fireball", "fireball", "fireball", "strike", "strike", "strike", "guard", "guard"]
    with pytest.raises(ValueError):
        g.build("alice", deck)


def test_state_is_detached():
    g = game()
    g.build("alice", ALICE_DECK)
    st = g.state()
    st["decks"]["alice"].append("dragon")
    st["players"]["alice"]["strike"] = 99
    assert len(g.state()["decks"]["alice"]) == 8
    assert g.state()["players"]["alice"]["strike"] == 3
