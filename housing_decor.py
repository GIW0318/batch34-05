import copy


class HousingDecor:
    _ROLES = ("owner", "roommate", "visitor")
    _GRANTABLE_ROLES = ("roommate", "visitor")
    _DEFAULT_CONFIG = {
        "comfort_cap": 100,
        "set_bonus": 5,
        "set_min": 2,
        "theme_bonus": 1,
    }

    def __init__(self, houses, furniture, config=None):
        self._houses = copy.deepcopy(houses)
        self._furniture = copy.deepcopy(furniture)
        self._config = dict(self._DEFAULT_CONFIG)
        if config:
            self._config.update(config)

        self._next_ids = {}
        for name, house in self._houses.items():
            placed = house.setdefault("placed", [])
            numeric_ids = [
                placement.get("id")
                for placement in placed
                if isinstance(placement.get("id"), int)
                and not isinstance(placement.get("id"), bool)
            ]
            self._next_ids[name] = max(numeric_ids, default=0) + 1

    def grant(self, house, actor, player, role):
        target = self._house(house)
        self._require_owner(target, actor)
        if role not in self._GRANTABLE_ROLES:
            raise ValueError("unsupported role")
        if player == target.get("owner") or player in target.get("members", {}):
            raise ValueError("player is already a member")

        target.setdefault("members", {})[player] = role

    def revoke(self, house, actor, player):
        target = self._house(house)
        self._require_owner(target, actor)
        members = target.get("members", {})
        if (
            player not in members
            or player == target.get("owner")
            or members[player] == "owner"
        ):
            raise ValueError("cannot revoke this member")

        del members[player]

    def place(self, house, room, actor, item, x, y):
        target = self._house(house)
        room_data = self._room(target, room)
        self._require_editor(target, actor)
        self._require_room_access(target, room_data, actor)

        item_data = self._furniture.get(item)
        if item_data is None:
            raise ValueError("unknown furniture")
        if not self._allowed_in_room(item_data, room):
            raise ValueError("furniture cannot be placed in this room")

        width = self._positive_int(item_data, "w")
        height = self._positive_int(item_data, "h")
        room_width = self._positive_int(room_data, "w")
        room_height = self._positive_int(room_data, "h")
        if not self._is_int(x) or not self._is_int(y):
            raise ValueError("coordinates must be integers")
        if x < 0 or y < 0 or x + width > room_width or y + height > room_height:
            raise ValueError("furniture does not fit in the room")

        for placement in target.setdefault("placed", []):
            if placement.get("room") != room:
                continue
            other = self._furniture.get(placement.get("item"), {})
            other_width = other.get("w", placement.get("w"))
            other_height = other.get("h", placement.get("h"))
            if not self._is_positive_int(other_width) or not self._is_positive_int(
                other_height
            ):
                continue
            other_x = placement.get("x")
            other_y = placement.get("y")
            if not self._is_int(other_x) or not self._is_int(other_y):
                continue
            if (
                x < other_x + other_width
                and other_x < x + width
                and y < other_y + other_height
                and other_y < y + height
            ):
                raise ValueError("furniture overlaps an existing placement")

        placement = {
            "id": self._new_id(house, target),
            "item": item,
            "room": room,
            "x": x,
            "y": y,
        }
        target["placed"].append(placement)
        return copy.deepcopy(placement)

    def remove(self, house, room, actor, placement_id):
        target = self._house(house)
        room_data = self._room(target, room)
        self._require_editor(target, actor)
        self._require_room_access(target, room_data, actor)

        placements = target.setdefault("placed", [])
        for index, placement in enumerate(placements):
            if (
                placement.get("id") == placement_id
                and placement.get("room") == room
            ):
                del placements[index]
                return None
        raise ValueError("unknown placement")

    def comfort(self, house, room=None):
        target = self._house(house)
        rooms = target.get("rooms", {})
        if room is not None and room not in rooms:
            raise ValueError("unknown room")

        room_names = [room] if room is not None else list(rooms)
        total = 0
        for room_name in room_names:
            total += self._room_comfort(target, room_name, rooms[room_name])
        return total

    def state(self):
        return {"houses": copy.deepcopy(self._houses)}

    def _house(self, name):
        try:
            return self._houses[name]
        except (KeyError, TypeError):
            raise ValueError("unknown house")

    @staticmethod
    def _room(house, name):
        try:
            return house.get("rooms", {})[name]
        except (KeyError, TypeError):
            raise ValueError("unknown room")

    def _role(self, house, actor):
        members = house.get("members", {})
        if actor == house.get("owner"):
            return "owner"
        if actor not in members or members[actor] not in self._ROLES:
            raise ValueError("actor is not a house member")
        return members[actor]

    def _require_owner(self, house, actor):
        if self._role(house, actor) != "owner":
            raise ValueError("owner permission required")

    def _require_editor(self, house, actor):
        if self._role(house, actor) not in ("owner", "roommate"):
            raise ValueError("roommate permission required")

    def _require_room_access(self, house, room, actor):
        if room.get("locked") and self._role(house, actor) != "owner":
            raise ValueError("room is locked")

    @staticmethod
    def _allowed_in_room(item, room):
        rooms = item.get("rooms", [])
        if isinstance(rooms, str):
            rooms = [rooms]
        return room in rooms

    def _new_id(self, house_name, house):
        used = {placement.get("id") for placement in house.setdefault("placed", [])}
        next_id = self._next_ids.get(house_name, 1)
        while next_id in used:
            next_id += 1
        self._next_ids[house_name] = next_id + 1
        return next_id

    def _room_comfort(self, house, room_name, room):
        items = []
        for placement in house.get("placed", []):
            if placement.get("room") == room_name:
                item = self._furniture.get(placement.get("item"))
                if item is not None:
                    items.append(item)

        score = sum(item.get("comfort", 0) for item in items)

        room_theme = room.get("theme")
        for item in items:
            themes = item.get("themes", [])
            if isinstance(themes, str):
                themes = [themes]
            if room_theme in themes:
                score += self._config["theme_bonus"]

        set_counts = {}
        for item in items:
            item_set = item.get("set")
            if item_set:
                set_counts[item_set] = set_counts.get(item_set, 0) + 1
        for count in set_counts.values():
            if count >= self._config["set_min"]:
                score += self._config["set_bonus"]

        cap = self._config.get("comfort_cap")
        return score if cap is None else min(score, cap)

    @staticmethod
    def _is_int(value):
        return isinstance(value, int) and not isinstance(value, bool)

    @classmethod
    def _is_positive_int(cls, value):
        return cls._is_int(value) and value > 0

    @classmethod
    def _positive_int(cls, data, key):
        value = data.get(key)
        if not cls._is_positive_int(value):
            raise ValueError("invalid dimension")
        return value
