import copy


class FarmSeasons:
    def __init__(self, farm, crops, config=None):
        self.farm = farm
        self.crops = crops
        config = config or {}
        self.season_days = config.get("season_days", 3)
        self.rain_bonus = config.get("rain_bonus", 1)
        self.drought_penalty = config.get("drought_penalty", 1)
        self.greenhouse_bonus = config.get("greenhouse_bonus", 1)
        self.water_cap = 3
        self.seasons = ["spring", "summer", "autumn", "winter"]

    def _is_greenhouse(self, plot):
        return self.farm["plots"][plot]["kind"] == "greenhouse"

    def _in_season(self, crop, season):
        return season in self.crops[crop]["seasons"]

    def _reset_plot(self, plot):
        plot.update({"crop": None, "growth": 0, "water": 1, "health": 2})

    def plant(self, plot, crop, now=0):
        if plot not in self.farm["plots"]:
            raise ValueError("unknown plot: %s" % plot)
        if crop not in self.crops:
            raise ValueError("unknown crop: %s" % crop)
        current = self.farm["plots"][plot]
        if current["crop"] is not None:
            raise ValueError("plot %s is already occupied" % plot)
        info = self.crops[crop]
        if not self._is_greenhouse(plot) and not self._in_season(crop, self.farm["season"]):
            raise ValueError("crop %s is out of season" % crop)
        seed_cost = info["seed"]
        if self.farm["gold"] < seed_cost:
            raise ValueError("not enough gold for seed")
        self.farm["gold"] -= seed_cost
        current.update({"crop": crop, "growth": 0, "water": 1, "health": 2})

    def irrigate(self, plot):
        if plot not in self.farm["plots"]:
            raise ValueError("unknown plot: %s" % plot)
        current = self.farm["plots"][plot]
        current["water"] = min(self.water_cap, current["water"] + 1)

    def next_day(self, weather="sunny"):
        self.farm["weather"] = weather
        if self.season_days > 0 and (self.farm["day"] + 1) % self.season_days == 0:
            index = self.seasons.index(self.farm["season"])
            self.farm["season"] = self.seasons[(index + 1) % len(self.seasons)]
        self.farm["day"] += 1

        season = self.farm["season"]
        for plot in self.farm["plots"].values():
            crop = plot["crop"]
            if crop is None:
                continue
            info = self.crops[crop]
            greenhouse = plot["kind"] == "greenhouse"
            in_season = self._in_season(crop, season)

            if in_season or greenhouse:
                growth = 2
            else:
                growth = 1

            if weather == "rain":
                growth += self.rain_bonus
                plot["water"] = min(self.water_cap, plot["water"] + 1)
            elif weather == "drought":
                growth -= self.drought_penalty
                plot["water"] = max(0, plot["water"] - 1)
            elif weather == "frost":
                growth -= 1
                plot["water"] = max(0, plot["water"] - 1)
                if not info["hardy"]:
                    plot["health"] -= 1
            else:
                plot["water"] = max(0, plot["water"] - 1)

            plot["growth"] = max(0, plot["growth"] + growth)

            if plot["health"] <= 0:
                self._reset_plot(plot)

    def harvest(self, plot, now=0):
        if plot not in self.farm["plots"]:
            raise ValueError("unknown plot: %s" % plot)
        current = self.farm["plots"][plot]
        crop = current["crop"]
        if crop is None:
            raise ValueError("plot %s has no crop" % plot)
        info = self.crops[crop]
        if current["growth"] < info["days"]:
            raise ValueError("crop %s is not mature yet" % crop)

        amount = info["yield"]
        if self._in_season(crop, self.farm["season"]):
            amount += 2
        if current["kind"] == "greenhouse":
            amount += self.greenhouse_bonus

        inventory = self.farm["inventory"]
        inventory[crop] = inventory.get(crop, 0) + amount
        self._reset_plot(current)
        return amount

    def price(self, crop):
        if crop not in self.crops:
            raise ValueError("unknown crop: %s" % crop)
        multiplier = 1
        if not self._in_season(crop, self.farm["season"]):
            multiplier *= 2
        if self.farm["weather"] in ("drought", "frost"):
            multiplier *= 2
        return self.crops[crop]["price"] * multiplier

    def sell(self, crop, qty):
        if not isinstance(qty, int) or isinstance(qty, bool) or qty <= 0:
            raise ValueError("qty must be a positive integer")
        inventory = self.farm["inventory"]
        if crop not in inventory or inventory[crop] < qty:
            raise ValueError("not enough inventory to sell")
        earnings = self.price(crop) * qty
        self.farm["gold"] += earnings
        remaining = inventory[crop] - qty
        if remaining == 0:
            del inventory[crop]
        else:
            inventory[crop] = remaining
        return earnings

    def state(self):
        return copy.deepcopy(
            {
                "season": self.farm["season"],
                "day": self.farm["day"],
                "weather": self.farm["weather"],
                "gold": self.farm["gold"],
                "inventory": self.farm["inventory"],
                "plots": self.farm["plots"],
            }
        )
