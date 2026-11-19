import copy


class TavernManagement:
    def __init__(self, tavern, recipes, config=None):
        self.tavern = tavern
        self.recipes = recipes
        self.config = config or {}

        self.seats = tavern["seats"]
        self.gold = tavern["gold"]
        self.stock = dict(tavern["stock"])
        self.reputation = tavern["reputation"]

        self.queue = []
        self.seated = {}
        self.served = 0

    def _cfg(self, key, default):
        return self.config.get(key, default)

    def _stock_cap(self, item):
        capacity = self.tavern.get("capacity")
        if isinstance(capacity, dict):
            capacity = capacity.get(item)
        if capacity is None:
            capacity = self.config.get("stock_max", self.config.get("stock_cap"))
        return capacity

    def arrive(self, name, party, now):
        if not isinstance(party, int) or isinstance(party, bool) or party <= 0:
            raise ValueError("party size must be a positive integer")
        if party > self.seats:
            raise ValueError("party larger than total seats")
        if any(row["name"] == name for row in self.queue) or name in self.seated:
            raise ValueError("guest already registered")
        self.queue.append({"name": name, "party": party, "arrival": now})
        return None

    def seat(self, now):
        occupied = sum(guest["party"] for guest in self.seated.values())
        for index, row in enumerate(self.queue):
            if row["party"] <= self.seats - occupied:
                guest = self.queue.pop(index)
                self.seated[guest["name"]] = {
                    "party": guest["party"],
                    "arrival": guest["arrival"],
                    "order": None,
                }
                return guest["name"]
        return None

    def order(self, ticket, dish, now):
        guest = self.seated.get(ticket)
        if guest is None:
            raise ValueError("unknown or unseated ticket")
        if guest["order"] is not None:
            raise ValueError("guest already placed an order")
        recipe = self.recipes.get(dish)
        if recipe is None:
            raise ValueError("unknown dish")

        ingredients = recipe["ingredients"]
        if any(self.stock.get(item, 0) < amount for item, amount in ingredients.items()):
            self.reputation = max(0, self.reputation - self._cfg("rep_leave", 2))
            del self.seated[ticket]
            return {"ok": False, "ready": None, "reason": "stock"}

        for item, amount in ingredients.items():
            self.stock[item] = self.stock.get(item, 0) - amount
        ready = now + recipe["prep"]
        guest["order"] = {"dish": dish, "ready": ready}
        return {"ok": True, "ready": ready, "reason": None}

    def serve(self, ticket, now):
        guest = self.seated.get(ticket)
        if guest is None:
            raise ValueError("unknown ticket")
        order = guest["order"]
        if order is None:
            raise ValueError("guest has no pending order")
        if now < order["ready"]:
            raise ValueError("dish is not ready yet")

        recipe = self.recipes[order["dish"]]
        remaining = self._cfg("patience", 10) - (now - guest["arrival"])
        tip = max(0, remaining) // self._cfg("tip_div", 2)
        total = recipe["price"] + tip

        self.gold += total
        self.reputation = min(
            self._cfg("rep_max", 100), self.reputation + recipe["rep"]
        )
        self.served += 1
        del self.seated[ticket]
        return total

    def tick(self, now):
        patience = self._cfg("patience", 10)
        left = []
        for name in list(self.seated):
            guest = self.seated[name]
            if now - guest["arrival"] <= patience:
                continue
            if guest["order"] is not None:
                penalty = self._cfg("rep_leave", 2)
            else:
                penalty = self._cfg("rep_impatient", 1)
            self.reputation = max(0, self.reputation - penalty)
            del self.seated[name]
            left.append(name)
        return left

    def restock(self, item, qty, unit_cost):
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("restock qty must be a positive integer")
        if (
            not isinstance(unit_cost, (int, float))
            or isinstance(unit_cost, bool)
            or unit_cost <= 0
        ):
            raise ValueError("unit cost must be positive")
        if item not in self.stock:
            raise ValueError("unknown stock item")
        cap = self._stock_cap(item)
        if cap is not None and self.stock[item] + qty > cap:
            raise ValueError("stock capacity exceeded")
        cost = qty * unit_cost
        if self.gold < cost:
            raise ValueError("not enough gold")
        self.gold -= cost
        self.stock[item] += qty
        return None

    def state(self):
        return {
            "queue": copy.deepcopy(self.queue),
            "seated": copy.deepcopy(self.seated),
            "stock": copy.deepcopy(self.stock),
            "gold": self.gold,
            "reputation": self.reputation,
            "served": self.served,
        }
