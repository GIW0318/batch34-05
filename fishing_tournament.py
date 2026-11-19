import copy

WEATHERS = ("calm", "rain", "storm")

STATUS_IDLE = "idle"
STATUS_OPEN = "open"
STATUS_CLOSED = "closed"
STATUS_SETTLED = "settled"


class FishingTournament:
    def __init__(self, anglers, zones, config=None):
        config = config or {}
        self._deadline = config.get("deadline")
        self._pot = config.get("pot", 0)
        self._payout_bps = list(config.get("payout_bps", []))
        self._storm_extra = config.get("storm_extra", 3)

        self._anglers = {}
        for name, profile in anglers.items():
            self._anglers[name] = {
                "stamina": profile.get("stamina", 0),
                "bait": dict(profile.get("bait", {})),
                "score": 0,
                "catches": [],
                "payout": 0,
            }
        self._zones = {
            name: [dict(species) for species in zone.get("species", [])]
            for name, zone in zones.items()
        }
        self._cast_counts = {name: {} for name in self._anglers}

        self._status = STATUS_IDLE
        self._weather = "calm"
        self._opened_at = None
        self._closed_at = None
        self._payouts = {}

    def open(self, now):
        if self._status != STATUS_IDLE:
            raise ValueError("tournament cannot be opened now")
        self._status = STATUS_OPEN
        self._weather = "calm"
        self._opened_at = now

    def set_weather(self, weather, now):
        if self._status != STATUS_OPEN:
            raise ValueError("weather can only change while the tournament is open")
        if weather not in WEATHERS:
            raise ValueError("unknown weather: %r" % (weather,))
        self._weather = weather

    def cast(self, angler, zone, now):
        if self._status != STATUS_OPEN:
            raise ValueError("tournament is not open")
        if self._deadline is not None and now > self._deadline:
            raise ValueError("tournament deadline has passed")
        if angler not in self._anglers:
            raise ValueError("angler is not registered: %r" % (angler,))
        if zone not in self._zones:
            raise ValueError("unknown zone: %r" % (zone,))

        species_list = self._zones[zone]
        if not species_list:
            raise ValueError("zone has no species: %r" % (zone,))
        count = self._cast_counts[angler].get(zone, 0)
        species = species_list[count % len(species_list)]

        if self._weather not in species.get("weathers", []):
            raise ValueError(
                "species %r does not bite in weather %r" % (species["name"], self._weather)
            )

        stamina_cost = species.get("stamina", 0)
        if self._weather == "storm":
            stamina_cost += self._storm_extra
        bait_kind = species.get("bait")

        profile = self._anglers[angler]
        if profile["stamina"] < stamina_cost:
            raise ValueError("not enough stamina")
        if bait_kind is not None and profile["bait"].get(bait_kind, 0) < 1:
            raise ValueError("not enough bait: %r" % (bait_kind,))

        points = species.get("points", 0)
        if self._weather == "rain":
            points *= 2

        profile["stamina"] -= stamina_cost
        if bait_kind is not None:
            profile["bait"][bait_kind] -= 1
        profile["score"] += points
        profile["catches"].append(
            {
                "species": species["name"],
                "zone": zone,
                "points": points,
                "weather": self._weather,
                "time": now,
            }
        )
        self._cast_counts[angler][zone] = count + 1
        return {"species": species["name"], "points": points, "zone": zone}

    def close(self, now):
        if self._status != STATUS_OPEN:
            raise ValueError("tournament is not open")
        self._status = STATUS_CLOSED
        self._closed_at = now

    def settle(self):
        if self._status == STATUS_SETTLED:
            raise ValueError("tournament already settled")
        if self._status != STATUS_CLOSED:
            raise ValueError("tournament must be closed before settling")

        ranked = self._ranked_anglers(only_with_catches=True)
        payouts = {}
        paid_total = 0
        for rank, name in enumerate(ranked):
            if rank >= len(self._payout_bps):
                break
            amount = self._pot * self._payout_bps[rank] // 10000
            payouts[name] = amount
            paid_total += amount
        if ranked:
            payouts[ranked[0]] = payouts.get(ranked[0], 0) + (self._pot - paid_total)

        for name, amount in payouts.items():
            self._anglers[name]["payout"] = amount
        self._payouts = payouts
        self._status = STATUS_SETTLED
        return dict(payouts)

    def leaderboard(self):
        return [
            {"angler": name, "score": self._anglers[name]["score"]}
            for name in self._ranked_anglers()
        ]

    def state(self):
        return {
            "status": self._status,
            "weather": self._weather,
            "anglers": copy.deepcopy(self._anglers),
            "payouts": dict(self._payouts),
        }

    def _ranked_anglers(self, only_with_catches=False):
        names = [
            name
            for name, profile in self._anglers.items()
            if not only_with_catches or profile["catches"]
        ]
        names.sort(key=lambda name: (-self._anglers[name]["score"], name))
        return names
