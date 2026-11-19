import copy

GENES = ("coat", "size", "speed")

PHENOTYPES = {
    "coat": ("red", "white"),
    "size": ("large", "small"),
    "speed": ("fast", "slow"),
}


class PetBreeding:
    def __init__(self, pets, config=None):
        config = config or {}
        self._cooldown = config.get("cooldown", 0)
        self._max_generation = config.get("max_generation", 10)
        self._pets = {}
        for name, pet in pets.items():
            record = copy.deepcopy(pet)
            record.setdefault("parents", [])
            record.setdefault("last_bred", None)
            record.setdefault("generation", 1)
            self._pets[name] = record
        self._bred_history = {name: [] for name in pets}
        self._next_id = 1

    def _require(self, name):
        if name not in self._pets:
            raise ValueError(f"unknown pet: {name}")
        return self._pets[name]

    def _ancestors(self, name):
        seen = set()
        stack = [name]
        while stack:
            current = stack.pop()
            if current in seen:
                continue
            seen.add(current)
            stack.extend(self._pets[current]["parents"])
        return seen

    def _cooldown_remaining(self, name, now):
        bred = [t for t in self._bred_history.get(name, []) if t < now]
        if not bred:
            return 0
        return max(0, self._cooldown - (now - max(bred)))

    @staticmethod
    def _is_dominant(allele):
        return allele.isupper()

    def _combine(self, father, mother):
        genes = {}
        for gene in GENES:
            pair = [father["genes"][gene][0], mother["genes"][gene][1]]
            pool = father["genes"][gene] + mother["genes"][gene]
            if all(not self._is_dominant(allele) for allele in pool):
                pair[0] = pair[0].upper()
            genes[gene] = pair
        return genes

    def breed(self, a, b, now, sex="f"):
        if sex not in ("m", "f"):
            raise ValueError(f"invalid sex: {sex}")
        if a == b:
            raise ValueError("cannot breed a pet with itself")
        first = self._require(a)
        second = self._require(b)
        if first["species"] != second["species"]:
            raise ValueError("cannot breed different species")
        if first["sex"] == second["sex"]:
            raise ValueError("cannot breed same-sex pets")
        if self._ancestors(a) & self._ancestors(b):
            raise ValueError("pets share a common ancestor")
        for name in (a, b):
            pet = self._pets[name]
            last_bred = pet["last_bred"]
            if last_bred is not None and now - last_bred < self._cooldown:
                raise ValueError("pet is still in cooldown")
        generation = max(first["generation"], second["generation"]) + 1
        if generation > self._max_generation:
            raise ValueError("generation limit exceeded")
        father, mother = (first, second) if first["sex"] == "m" else (second, first)
        while f"pet{self._next_id}" in self._pets:
            self._next_id += 1
        child_id = f"pet{self._next_id}"
        self._next_id += 1
        self._pets[child_id] = {
            "species": first["species"],
            "sex": sex,
            "genes": self._combine(father, mother),
            "generation": generation,
            "parents": [a, b],
            "last_bred": None,
        }
        first["last_bred"] = now
        second["last_bred"] = now
        self._bred_history.setdefault(a, []).append(now)
        self._bred_history.setdefault(b, []).append(now)
        return child_id

    def stats(self, pet):
        record = self._require(pet)
        result = {}
        dominant_count = 0
        for gene in GENES:
            dominant, recessive = PHENOTYPES[gene]
            if any(self._is_dominant(allele) for allele in record["genes"][gene]):
                result[gene] = dominant
                dominant_count += 1
            else:
                result[gene] = recessive
        result["generation"] = record["generation"]
        result["power"] = 10 + 2 * dominant_count + (record["generation"] - 1) * 3
        return result

    def cooldown(self, pet, now):
        self._require(pet)
        return self._cooldown_remaining(pet, now)

    def state(self):
        return {"pets": copy.deepcopy(self._pets)}
