import copy
import random

DEFAULT_CONFIG = {
    "floors": 2,
    "rooms": 5,
    "hero_hp": 30,
    "base_attack": 3,
    "enemy_atk": 2,
    "enemy_hp_base": 6,
    "relic_cap": 3,
    "shop_price": 5,
    "rest_heal": 8,
    "start_gold": 10,
}

KNOWN_RELICS = ("ember", "shell")
SHOP_STOCK = KNOWN_RELICS
ELITE_RELIC_OFFER = "ember"
EMBER_ATTACK_BONUS = 2
ROOM_KINDS = ("fight", "elite", "shop", "rest")
GOLD_REWARDS = {"fight": 4, "elite": 6, "boss": 10}
STATUSES = ("running", "victory", "defeat")

SAVE_FIELDS = ("floor", "hp", "max_hp", "gold", "status", "index", "relics", "rooms")


class RoguelikeRun:
    def __init__(self, seed, config=None):
        self.seed = seed
        self.config = dict(DEFAULT_CONFIG)
        if config:
            self.config.update(config)
        self.floor = 1
        self.max_hp = self.config["hero_hp"]
        self.hp = self.max_hp
        self.gold = self.config["start_gold"]
        self.relics = {}
        self.status = "running"
        self.rooms = self._generate_rooms(self.floor)
        self.index = 0
        self._entered = False

    def _generate_rooms(self, floor):
        rng = random.Random("{}:{}".format(self.seed, floor))
        kinds = list(ROOM_KINDS)
        rng.shuffle(kinds)
        kinds.append("boss")
        return [{"type": kind, "cleared": False} for kind in kinds]

    def _attack(self):
        ember = self.relics.get("ember", 0)
        return self.config["base_attack"] + ember * EMBER_ATTACK_BONUS

    def _enemy_hp(self, kind):
        base = self.config["enemy_hp_base"] + self.floor * 2
        if kind == "elite":
            return base + 4
        if kind == "boss":
            return base * 2
        return base

    def enter(self, index):
        if self.status != "running":
            raise ValueError("run is over")
        if not isinstance(index, int) or index != self.index:
            raise ValueError("rooms must be entered in order")
        self._entered = True
        return dict(self.rooms[index])

    def resolve(self):
        if self.status != "running":
            raise ValueError("run is over")
        if not self._entered:
            raise ValueError("enter the room before resolving it")
        room = self.rooms[self.index]
        if room["cleared"]:
            raise ValueError("room already cleared")
        kind = room["type"]
        result = {"type": kind}
        if kind in ("fight", "elite", "boss"):
            result.update(self._resolve_combat(kind))
        elif kind == "rest":
            healed = min(self.config["rest_heal"], self.max_hp - self.hp)
            self.hp += healed
            result["healed"] = healed
        room["cleared"] = True
        self._entered = False
        if kind == "boss":
            if self.status == "running":
                if self.floor >= self.config["floors"]:
                    self.status = "victory"
                else:
                    self.floor += 1
                    self.rooms = self._generate_rooms(self.floor)
                    self.index = 0
        else:
            self.index += 1
        return result

    def _resolve_combat(self, kind):
        enemy_hp = self._enemy_hp(kind)
        rounds = -(-enemy_hp // self._attack())
        damage = (rounds - 1) * self.config["enemy_atk"]
        self.hp = max(0, self.hp - damage)
        reward = GOLD_REWARDS[kind]
        self.gold += reward
        result = {
            "enemy_hp": enemy_hp,
            "rounds": rounds,
            "damage_taken": damage,
            "gold": reward,
        }
        if kind == "elite":
            result["relic_offer"] = ELITE_RELIC_OFFER
        if self.hp <= 0:
            self.status = "defeat"
        return result

    def buy(self, relic):
        if self.status != "running":
            raise ValueError("run is over")
        if not self._entered or self.rooms[self.index]["type"] != "shop":
            raise ValueError("not inside a shop room")
        if relic not in SHOP_STOCK:
            raise ValueError("unknown relic: {}".format(relic))
        price = self.config["shop_price"]
        if self.gold < price:
            raise ValueError("not enough gold")
        self.add_relic(relic)
        self.gold -= price
        return dict(self.relics)

    def add_relic(self, relic):
        if relic not in KNOWN_RELICS:
            raise ValueError("unknown relic: {}".format(relic))
        if self.relics.get(relic, 0) >= self.config["relic_cap"]:
            raise ValueError("relic stack cap reached: {}".format(relic))
        self.relics[relic] = self.relics.get(relic, 0) + 1
        return dict(self.relics)

    def save(self):
        data = self.state()
        data["seed"] = self.seed
        return data

    def restore(self, data):
        self._validate_save(data)
        self.seed = data.get("seed", self.seed)
        self.floor = data["floor"]
        self.max_hp = data["max_hp"]
        self.hp = data["hp"]
        self.gold = data["gold"]
        self.status = data["status"]
        self.index = data["index"]
        self.relics = copy.deepcopy(data["relics"])
        self.rooms = copy.deepcopy(data["rooms"])
        self._entered = False

    def _validate_save(self, data):
        if not isinstance(data, dict) or not all(key in data for key in SAVE_FIELDS):
            raise ValueError("corrupt save: missing fields")
        max_hp = data["max_hp"]
        hp = data["hp"]
        if not isinstance(max_hp, int) or max_hp <= 0:
            raise ValueError("corrupt save: bad max_hp")
        if not isinstance(hp, int) or not 0 <= hp <= max_hp:
            raise ValueError("corrupt save: hp out of range")
        if not isinstance(data["floor"], int) or not 1 <= data["floor"] <= self.config["floors"]:
            raise ValueError("corrupt save: floor out of range")
        if not isinstance(data["gold"], int) or data["gold"] < 0:
            raise ValueError("corrupt save: bad gold")
        if data["status"] not in STATUSES:
            raise ValueError("corrupt save: bad status")
        if not isinstance(data["index"], int) or not 0 <= data["index"] < self.config["rooms"]:
            raise ValueError("corrupt save: index out of range")
        relics = data["relics"]
        if not isinstance(relics, dict):
            raise ValueError("corrupt save: bad relics")
        for name, stacks in relics.items():
            if name not in KNOWN_RELICS or not isinstance(stacks, int):
                raise ValueError("corrupt save: bad relics")
            if not 1 <= stacks <= self.config["relic_cap"]:
                raise ValueError("corrupt save: relic stacks out of range")
        rooms = data["rooms"]
        if not isinstance(rooms, list) or len(rooms) != self.config["rooms"]:
            raise ValueError("corrupt save: bad rooms")
        kinds = []
        for room in rooms:
            if not isinstance(room, dict) or set(room) != {"type", "cleared"}:
                raise ValueError("corrupt save: bad room entry")
            if room["type"] not in ROOM_KINDS + ("boss",) or not isinstance(room["cleared"], bool):
                raise ValueError("corrupt save: bad room entry")
            kinds.append(room["type"])
        if kinds[-1] != "boss" or sorted(kinds[:-1]) != sorted(ROOM_KINDS):
            raise ValueError("corrupt save: bad room layout")
        cleared = [room["cleared"] for room in rooms]
        if data["status"] == "victory":
            if not all(cleared):
                raise ValueError("corrupt save: inconsistent cleared flags")
        elif not all(cleared[: data["index"]]) or any(cleared[data["index"]:]):
            raise ValueError("corrupt save: inconsistent cleared flags")

    def state(self):
        return {
            "floor": self.floor,
            "hp": self.hp,
            "max_hp": self.max_hp,
            "gold": self.gold,
            "status": self.status,
            "index": self.index,
            "relics": copy.deepcopy(self.relics),
            "rooms": copy.deepcopy(self.rooms),
        }
