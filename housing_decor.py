class HousingDecor:
    def __init__(self, houses, furniture, config=None):
        pass

    def grant(self, house, actor, player, role):
        return None

    def revoke(self, house, actor, player):
        return None

    def place(self, house, room, actor, item, x, y):
        return None

    def remove(self, house, room, actor, placement_id):
        return None

    def comfort(self, house, room=None):
        return None

    def state(self):
        return {}
