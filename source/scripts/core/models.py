from core.config import PERSONALITY_EFFECTS, STAT_NAMES, VET_HEAL
from core.utils import clamp


class Cat:
    """Represents the player's cat and all mutable life stats."""

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

    def personality_effect(self, effect_name):
        """Return the personality-specific modifier for a named effect."""
        return PERSONALITY_EFFECTS.get(self.personality, {}).get(effect_name, 0)

    def as_dict(self):
        """Serialize the cat into a save-file friendly dictionary."""
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
        """Increase hunger using base value plus personality adjustment."""
        self.hunger = clamp(self.hunger + 24 + self.personality_effect("feed_bonus"))

    def play(self):
        """Increase happiness using base value plus personality adjustment."""
        self.happiness = clamp(self.happiness + 20 + self.personality_effect("play_bonus"))

    def rest(self):
        """Increase energy using base value plus personality adjustment."""
        self.energy = clamp(self.energy + 30 + self.personality_effect("rest_bonus"))

    def clean(self):
        """Increase cleanliness using base value plus personality adjustment."""
        self.cleanliness = clamp(self.cleanliness + 28 + self.personality_effect("clean_bonus"))

    def apply_time_passage(self):
        """Advance one time tick and decay stats according to personality."""
        self.age_days += 1
        self.hunger = clamp(self.hunger - (3 + self.personality_effect("hunger_decay")))
        self.happiness = clamp(self.happiness - (2 + self.personality_effect("happiness_decay")))
        self.energy = clamp(self.energy - (2 + self.personality_effect("energy_decay")))
        self.cleanliness = clamp(self.cleanliness - (2 + self.personality_effect("cleanliness_decay")))

        # Health falls faster when multiple care stats are low at the same time.
        health_penalty = 0
        for stat_name in ("hunger", "happiness", "energy", "cleanliness"):
            stat_value = getattr(self, stat_name)
            if stat_value <= 20:
                health_penalty += 6
            elif stat_value <= 40:
                health_penalty += 3
        self.health = clamp(self.health - health_penalty)

    def vet_visit(self):
        """Restore health by the configured vet heal amount."""
        self.health = clamp(self.health + VET_HEAL)

    def dead_stat(self):
        """Return the first depleted stat name, or None when still alive."""
        for stat_name in STAT_NAMES:
            if getattr(self, stat_name) <= 0:
                return stat_name
        return None