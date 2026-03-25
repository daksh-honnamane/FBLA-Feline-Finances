from core.config import STAT_NAMES, VET_HEAL
from core.utils import clamp


class Cat:
    def __init__(self, name, cat_type, personality):
        self.name = name
        self.cat_type = cat_type
        self.personality = personality
        self.hunger = 100
        self.happiness = 100
        self.energy = 100
        self.cleanliness = 100
        self.health = 100
        self.age_days = 1

    def as_dict(self):
        return {
            "name": self.name,
            "type": self.cat_type,
            "personality": self.personality,
            "stats": {
                "hunger": self.hunger,
                "happiness": self.happiness,
                "energy": self.energy,
                "cleanliness": self.cleanliness,
                "health": self.health,
                "age_days": self.age_days,
            },
        }

    def feed(self):
        self.hunger = clamp(self.hunger + 24)

    def play(self):
        self.happiness = clamp(self.happiness + 20)
        self.energy = clamp(self.energy - 8)

    def rest(self):
        self.energy = clamp(self.energy + 30)
        self.happiness = clamp(self.happiness + 5)

    def clean(self):
        self.cleanliness = clamp(self.cleanliness + 28)
        self.happiness = clamp(self.happiness + 4)

    def apply_time_passage(self):
        self.age_days += 1
        self.hunger = clamp(self.hunger - 3)
        self.happiness = clamp(self.happiness - 2)
        self.energy = clamp(self.energy - 2)
        self.cleanliness = clamp(self.cleanliness - 2)

        health_penalty = 0
        for stat_name in ("hunger", "happiness", "energy", "cleanliness"):
            stat_value = getattr(self, stat_name)
            if stat_value <= 20:
                health_penalty += 6
            elif stat_value <= 40:
                health_penalty += 3
        self.health = clamp(self.health - health_penalty)

    def vet_visit(self):
        self.health = clamp(self.health + VET_HEAL)

    def dead_stat(self):
        for stat_name in STAT_NAMES:
            if getattr(self, stat_name) <= 0:
                return stat_name
        return None