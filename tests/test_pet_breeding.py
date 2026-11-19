import copy

import pytest

import pet_breeding as pb

PETS = {
    "ash": {
        "species": "fox",
        "sex": "m",
        "genes": {"coat": ["R", "r"], "size": ["B", "b"], "speed": ["s", "s"]},
        "generation": 1,
        "parents": [],
        "last_bred": None,
    },
    "blaze": {
        "species": "fox",
        "sex": "f",
        "genes": {"coat": ["r", "r"], "size": ["b", "b"], "speed": ["s", "s"]},
        "generation": 1,
        "parents": [],
        "last_bred": None,
    },
    "cinder": {
        "species": "fox",
        "sex": "m",
        "genes": {"coat": ["R", "R"], "size": ["B", "B"], "speed": ["S", "S"]},
        "generation": 1,
        "parents": [],
        "last_bred": None,
    },
    "willow": {
        "species": "wolf",
        "sex": "f",
        "genes": {"coat": ["r", "r"], "size": ["b", "b"], "speed": ["s", "s"]},
        "generation": 1,
        "parents": [],
        "last_bred": None,
    },
}
CONFIG = {"cooldown": 10, "max_generation": 5}


def kennel(config=None):
    return pb.PetBreeding(copy.deepcopy(PETS), dict(config or CONFIG))


def test_same_sex_is_rejected():
    k = kennel()
    with pytest.raises(ValueError):
        k.breed("ash", "cinder", now=0)


def test_cross_species_is_rejected():
    k = kennel()
    with pytest.raises(ValueError):
        k.breed("ash", "willow", now=0)


def test_self_breeding_is_rejected():
    k = kennel()
    with pytest.raises(ValueError):
        k.breed("ash", "ash", now=0)


def test_cooldown_blocks_repeat_breeding():
    k = kennel()
    k.breed("ash", "blaze", now=0)
    with pytest.raises(ValueError):
        k.breed("ash", "blaze", now=5)


def test_cooldown_expires():
    k = kennel()
    first = k.breed("ash", "blaze", now=0)
    assert k.cooldown("ash", 5) == 5
    second = k.breed("ash", "blaze", now=10)
    assert second != first
    assert k.cooldown("ash", 10) == 0


def test_offspring_generation_and_parents():
    k = kennel()
    child = k.breed("ash", "blaze", now=0, sex="f")
    st = k.state()["pets"][child]
    assert st["generation"] == 2
    assert st["parents"] == ["ash", "blaze"]
    assert st["sex"] == "f"


def test_allele_pairing_rule():
    k = kennel()
    child = k.breed("ash", "blaze", now=0)
    genes = k.state()["pets"][child]["genes"]
    assert genes["coat"] == ["R", "r"]
    assert genes["size"] == ["B", "b"]


def test_stats_express_traits_and_power():
    k = kennel()
    child = k.breed("ash", "blaze", now=0)
    st = k.stats(child)
    assert st["coat"] == "red"
    assert st["size"] == "large"
    assert st["speed"] == "fast"
    assert st["generation"] == 2
    assert st["power"] == 19


def test_recessive_gene_mutates():
    k = kennel()
    child = k.breed("ash", "blaze", now=0)
    assert k.state()["pets"][child]["genes"]["speed"] == ["S", "s"]


def test_base_stats_power():
    k = kennel()
    st = k.stats("ash")
    assert st == {"coat": "red", "size": "large", "speed": "slow", "generation": 1, "power": 14}


def test_parent_child_pairing_is_rejected():
    k = kennel()
    child = k.breed("ash", "blaze", now=0, sex="f")
    with pytest.raises(ValueError):
        k.breed("ash", child, now=20)


def test_siblings_with_shared_ancestor_are_rejected():
    k = kennel()
    one = k.breed("ash", "blaze", now=0, sex="f")
    two = k.breed("ash", "blaze", now=10, sex="m")
    with pytest.raises(ValueError):
        k.breed(one, two, now=20)


def test_generation_cap_is_enforced():
    k = kennel({"cooldown": 10, "max_generation": 1})
    with pytest.raises(ValueError):
        k.breed("ash", "blaze", now=0)


def test_breed_registers_offspring_and_stamps_parents():
    k = kennel()
    child = k.breed("ash", "blaze", now=7)
    st = k.state()
    assert child in st["pets"]
    assert st["pets"]["ash"]["last_bred"] == 7
    assert st["pets"]["blaze"]["last_bred"] == 7
    assert st["pets"][child]["last_bred"] is None


def test_state_is_detached():
    k = kennel()
    k.breed("ash", "blaze", now=0)
    st = k.state()
    st["pets"]["ash"]["genes"]["coat"][0] = "X"
    assert k.state()["pets"]["ash"]["genes"]["coat"] == ["R", "r"]
