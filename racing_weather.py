import copy


class RacingWeather:
    def __init__(self, track, cars, config=None):
        config = config or {}
        self._track = copy.deepcopy(track)
        self._cars = copy.deepcopy(cars)
        self._penalties = copy.deepcopy(config.get("penalties", {}))
        self._weather = "dry"
        self._drivers = {}
        self._known_tires = set()
        for tires in self._penalties.values():
            self._known_tires.update(tires.keys())

    def register(self, driver, car, tire):
        if driver in self._drivers:
            raise ValueError("driver already registered")
        if car not in self._cars:
            raise ValueError("unknown car")
        if self._known_tires and tire not in self._known_tires:
            raise ValueError("unknown tire")
        self._drivers[driver] = {
            "car": car,
            "tire": tire,
            "status": "registered",
            "started": None,
            "lap": 0,
            "next_cp": 0,
            "last_time": None,
            "checkpoints": [],
            "total": None,
            "penalty": None,
            "final": None,
        }

    def start(self, driver, now):
        entry = self._require_driver(driver)
        if entry["status"] != "registered":
            raise ValueError("race already started")
        entry["status"] = "running"
        entry["started"] = now
        entry["last_time"] = now

    def checkpoint(self, driver, index, now):
        entry = self._require_driver(driver)
        if entry["status"] != "running":
            raise ValueError("driver is not running")
        total_laps = self._track["laps"]
        cp_count = len(self._track["checkpoints"])
        if entry["lap"] >= total_laps:
            raise ValueError("all laps already completed")
        if not isinstance(index, int) or index < 0 or index >= cp_count:
            raise ValueError("unknown checkpoint")
        if index != entry["next_cp"]:
            raise ValueError("checkpoint out of order")
        if entry["last_time"] is not None and now <= entry["last_time"]:
            raise ValueError("checkpoint time must be strictly increasing")
        surface = self._track["checkpoints"][index]["surface"]
        entry["checkpoints"].append(
            {
                "index": index,
                "time": now,
                "weather": self._weather,
                "surface": surface,
            }
        )
        entry["last_time"] = now
        if index == cp_count - 1:
            entry["lap"] += 1
            entry["next_cp"] = 0
        else:
            entry["next_cp"] = index + 1

    def set_weather(self, weather, now):
        if weather not in ("dry", "rain", "storm"):
            raise ValueError("unknown weather")
        self._weather = weather

    def finish(self, driver, now):
        entry = self._require_driver(driver)
        if entry["status"] == "finished":
            raise ValueError("driver already finished")
        if entry["status"] != "running":
            raise ValueError("driver has not started")
        required = self._track["laps"] * len(self._track["checkpoints"])
        if entry["lap"] < self._track["laps"] or len(entry["checkpoints"]) < required:
            raise ValueError("not all checkpoints completed")
        if now <= entry["last_time"]:
            raise ValueError("finish time must be strictly increasing")
        bonus = self._cars[entry["car"]].get("penalty_bonus", 0)
        penalty = 0
        for point in entry["checkpoints"]:
            raw = (
                self._penalties.get(point["weather"], {})
                .get(entry["tire"], {})
                .get(point["surface"], 0)
            )
            penalty += max(0, raw - bonus)
        total = int(now - entry["started"])
        entry["total"] = total
        entry["penalty"] = penalty
        entry["final"] = total + penalty
        entry["status"] = "finished"

    def leaderboard(self):
        rows = []
        for driver, entry in self._drivers.items():
            if entry["status"] == "finished":
                rows.append(
                    {
                        "driver": driver,
                        "car": entry["car"],
                        "tire": entry["tire"],
                        "total": entry["total"],
                        "penalty": entry["penalty"],
                        "final": entry["final"],
                        "status": "finished",
                    }
                )
            else:
                rows.append(
                    {
                        "driver": driver,
                        "car": entry["car"],
                        "tire": entry["tire"],
                        "total": None,
                        "penalty": None,
                        "final": None,
                        "status": "dnf",
                    }
                )
        rows.sort(
            key=lambda row: (
                row["status"] != "finished",
                row["final"] if row["final"] is not None else 0,
                row["driver"],
            )
        )
        return copy.deepcopy(rows)

    def state(self):
        return copy.deepcopy({"weather": self._weather, "drivers": self._drivers})

    def _require_driver(self, driver):
        if driver not in self._drivers:
            raise ValueError("driver not registered")
        return self._drivers[driver]
