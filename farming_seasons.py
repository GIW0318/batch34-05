class FarmSeasons:
    def __init__(self, farm, crops, config=None):
        pass

    def plant(self, plot, crop, now=0):
        return None

    def irrigate(self, plot):
        return None

    def next_day(self, weather="sunny"):
        return None

    def harvest(self, plot, now=0):
        return None

    def price(self, crop):
        return None

    def sell(self, crop, qty):
        return None

    def state(self):
        return {}
