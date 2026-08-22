"""Realms (duchies): the player plus four AI rivals. Each keeps exactly one
living hero, a designated heir (or explicitly none), resources, population,
holdings, units and orders."""
from . import constants as C


class Realm:
    def __init__(self, key, name, is_player=False, color=(0, 0, 0)):
        self.key = key
        self.name = name
        self.is_player = is_player
        self.color = color
        self.gold = 0.0
        self.wheat = 0.0
        self.population = 0
        self.hero = None            # unit id
        self.heir = None            # unit id or None
        self.unit_ids = set()       # all owned units (anywhere on the map)
        self.settlement_ids = []    # owned holdings
        self.orders = []            # list of Order
        self.morale = 75.0
        self.drop_notes = []
        self.destroyed = False
        # AI scratch (not part of rules semantics)
        self.ai_target = None
        self.ai_path = []
        self.ai_think_timer = 0

    # ------------------------------------------------------------------ units
    def hero_unit(self, units):
        if self.hero is None:
            return None
        return units.get(self.hero)

    def heir_unit(self, units):
        if self.heir is None:
            return None
        return units.get(self.heir)

    def living_units(self, units):
        return [units[i] for i in sorted(self.unit_ids) if units[i].alive]

    def all_units(self, units):
        return [units[i] for i in sorted(self.unit_ids)]

    # ------------------------------------------------------------------ state
    def is_alive(self):
        return not self.destroyed

    def can_raise_hero(self, settlements):
        """A town (or bigger) is required to raise a new commander."""
        return any(s.size != "village" for s in self.holdings(settlements))

    def holdings(self, settlements):
        return [settlements[sid] for sid in self.settlement_ids
                if sid in settlements]

    def holdings_cap(self, settlements):
        return sum(s.pop_cap() for s in self.holdings(settlements))

    def gold_income(self, settlements):
        return sum(s.gold_produced() for s in self.holdings(settlements))

    def food_income(self, settlements):
        return sum(s.food_produced() for s in self.holdings(settlements))

    def building_upkeep(self, settlements):
        return sum(s.upkeep() for s in self.holdings(settlements))

    def staff_total(self, settlements):
        return sum(s.staff_needed() for s in self.holdings(settlements))

    def training_slots(self, settlements):
        return sum(s.training_slots() for s in self.holdings(settlements))

    def supplies(self, settlements):
        """Set of kit-building capabilities the realm currently provides."""
        can = set()
        for s in self.holdings(settlements):
            can |= s.supplies()
        return can

    def morale_from_holdings(self, settlements):
        return sum(s.morale_effect() for s in self.holdings(settlements))

    def add_note(self, text):
        self.drop_notes.append(text)

    def snapshot(self):
        return {
            "key": self.key, "name": self.name, "is_player": self.is_player,
            "gold": self.gold, "wheat": self.wheat,
            "population": self.population, "hero": self.hero,
            "heir": self.heir,
            "unit_ids": sorted(self.unit_ids),
            "settlement_ids": list(self.settlement_ids),
            "morale": self.morale, "destroyed": self.destroyed,
        }