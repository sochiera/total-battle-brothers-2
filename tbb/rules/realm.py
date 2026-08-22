"""One duchy: resources, population pool, succession and holdings."""
from . import constants as C

class Realm:
    def __init__(self, key, name, is_player=False, color=(0, 0, 0)):
        self.key, self.name, self.is_player, self.color = key, name, is_player, color
        self.gold = 0.0; self.wheat = 0.0; self.population = 0
        self.population_fraction = 0.0
        self.hero = None; self.heir = None
        self.unit_ids = set(); self.settlement_ids = []; self.orders = []
        self.morale = float(C.MORALE_START); self.destroyed = False
        self.drop_notes = []; self.ai_target = None; self.ai_path = []
        self.start_archetype = None

    def hero_unit(self, units): return units.get(self.hero) if self.hero is not None else None
    def heir_unit(self, units): return units.get(self.heir) if self.heir is not None else None
    def living_units(self, units): return [units[i] for i in sorted(self.unit_ids)
                                             if i in units and units[i].alive]
    def all_units(self, units): return [units[i] for i in sorted(self.unit_ids) if i in units]
    def holdings(self, settlements): return [settlements[i] for i in self.settlement_ids if i in settlements]
    def holdings_cap(self, settlements): return sum(h.pop_cap() for h in self.holdings(settlements))
    def can_raise_hero(self, settlements): return any(h.size in (C.SIZE_T, C.SIZE_C) for h in self.holdings(settlements))
    def building_upkeep(self, settlements): return sum(h.upkeep() for h in self.holdings(settlements))
    def staff_total(self, settlements): return sum(h.staff_needed() for h in self.holdings(settlements))
    def training_slots(self, settlements): return sum(h.training_slots() for h in self.holdings(settlements))
    def supplies(self, settlements):
        return {kind for h in self.holdings(settlements) for kind in h.supplies()}
    def morale_from_holdings(self, settlements): return sum(h.morale_effect() for h in self.holdings(settlements))
    def food_income(self, settlements):
        share = max(1, self.population // max(1, len(self.settlement_ids)))
        return sum(h.food_produced(share) for h in self.holdings(settlements))
    def gold_income(self, settlements): return 0
    def staffed(self, settlements, kind): return any(h.has(kind) for h in self.holdings(settlements))
    def snapshot(self):
        return {"key": self.key, "name": self.name, "is_player": self.is_player,
                "color": self.color, "gold": self.gold, "wheat": self.wheat,
                "population": self.population,
                "population_fraction": self.population_fraction,
                "hero": self.hero, "heir": self.heir,
                "unit_ids": sorted(self.unit_ids), "settlement_ids": list(self.settlement_ids),
                "orders": [o.snapshot() for o in self.orders], "morale": self.morale,
                "destroyed": self.destroyed, "start_archetype": self.start_archetype}
