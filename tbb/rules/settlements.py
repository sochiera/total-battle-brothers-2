"""Settlements: village / town / city. Buildings (locked roster), garrison
capacity, and the shared population staff pool all live here as pure data;
the monthly simulation lives in economy.py.
"""
from . import constants as C


class Building:
    def __init__(self, kind, staffed=False):
        self.kind = kind          # BUILDING_* key
        self.staffed = staffed    # staffed building pays upkeep & grants effect

    @property
    def defn(self):
        return C.BUILDINGS[self.kind]

    def effect_hint(self):
        return self.defn["effect"]


class Order:
    """A realm-wide long-term order (build, develop, found, train, gear).
    Orders complete on whole-month boundaries only."""
    def __init__(self, kind, kind_data, months, settlement_id=None, unit_id=None):
        self.kind = kind              # 'build'|'develop'|'found'|'train'|'gear'
        self.kind_data = kind_data    # e.g. building key / target size / kit id
        self.months = months          # remaining whole months
        self.months_total = months
        self.settlement_id = settlement_id
        self.unit_id = unit_id

    def label(self):
        if self.kind == "build":
            return "Raise %s" % self.kind_data
        if self.kind == "develop":
            return "Grow to %s" % self.kind_data
        if self.kind == "found":
            return "Found %s" % self.kind_data
        if self.kind == "train":
            return "Train drill"
        if self.kind == "gear":
            return "Order %s" % C.KITS[self.kind_data]["name"]
        return self.kind


class SettlementModel:
    """Static worldgen-only catcher -- the live settlement lives on World."""


class Holding:
    """A live holding owned by a realm (or neutral, owner None)."""
    def __init__(self, sid, name, hex_pos, size, owner=None):
        self.id = sid
        self.name = name
        self.hex = tuple(hex_pos)
        self.size = size  # village / town / city
        self.owner = owner  # realm key or None for neutrals
        self.buildings = {}   # building kind -> Building

    # requirement gates ----------------------------------------------------
    def size_index(self):
        try:
            return C.SIZE_ORDER.index(self.size)
        except ValueError:
            return 0

    def pop_cap(self):
        return C.POP_CAP[self.size]

    def building_slots(self):
        return C.BUILDING_SLOTS[self.size]

    def building_slots_free(self):
        used = len(self.buildings)
        return max(0, self.building_slots() - used)

    def garrison_cap(self):
        cap = C.GARRISON_BASE[self.size]
        if self.has(C.BUILDING_MILITIA_HALL):
            cap += C.MILITIA_HALL_CAP
        if self.has(C.BUILDING_WALLS):
            cap += C.WALLS_CAP
        if self.has(C.BUILDING_KEEP):
            cap += C.KEEP_CAP
        return cap

    def has(self, kind):
        b = self.buildings.get(kind)
        return b is not None and b.staffed

    def morale_effect(self):
        m = 0
        if self.has(C.BUILDING_KEEP):
            m += C.KEEP_MORALE
        if self.has(C.BUILDING_CHAPEL):
            m += C.CHAPEL_MORALE
        return m

    def training_slots(self):
        count = 0
        for k, b in self.buildings.items():
            if k == C.BUILDING_TRAINING_YARD and b.staffed:
                count += C.TRAINING_SLOTS_PER_YARD
        return count

    def supplies(self):
        """Kits this holding's realm can order."""
        can = set()
        for k, b in self.buildings.items():
            if b.staffed and k == C.BUILDING_SMITHY:
                can.add("smithy")
            if b.staffed and k == C.BUILDING_BOWYER:
                can.add("bowyer")
        return can

    def food_produced(self):
        food = 0
        for k, b in self.buildings.items():
            if not b.staffed:
                continue
            if k == C.BUILDING_FARM:
                food += C.FARM_FOOD
            elif k == C.BUILDING_GRANARY:
                food += C.GRANARY_FOOD
        return food

    def gold_produced(self):
        gold = 0
        for k, b in self.buildings.items():
            if not b.staffed:
                continue
            if k == C.BUILDING_MARKET:
                gold += C.MARKET_GOLD
        return gold

    def upkeep(self):
        return sum(b.defn["upkeep"] for b in self.buildings.values()
                   if b.staffed)

    def staff_needed(self):
        return sum(1 for b in self.buildings.values() if b.staffed)

    def __repr__(self):
        return "Holding(%s %s)" % (self.size, self.name)