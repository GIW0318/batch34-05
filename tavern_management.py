class TavernManagement:
    def __init__(self, tavern, recipes, config=None):
        pass

    def arrive(self, name, party, now):
        return None

    def seat(self, now):
        return None

    def order(self, ticket, dish, now):
        return None

    def serve(self, ticket, now):
        return None

    def tick(self, now):
        return []

    def restock(self, item, qty, unit_cost):
        return None

    def state(self):
        return {}
