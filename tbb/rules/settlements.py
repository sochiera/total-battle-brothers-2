"""Holdings and long-running, whole-month orders."""
from . import constants as C

class Building:
    def __init__(self, kind, staffed=False): self.kind, self.staffed = kind, bool(staffed)
    @property
    def defn(self): return C.BUILDINGS[self.kind]
    def effect_hint(self): return self.defn["effect"]
    def snapshot(self): return {"kind": self.kind, "staffed": self.staffed}

class Order:
    def __init__(self, kind, kind_data=None, months=1, settlement_id=None, unit_id=None, focus=None):
        self.kind, self.kind_data, self.months = kind, kind_data, int(months)
        self.months_total = int(months); self.settlement_id, self.unit_id, self.focus = settlement_id, unit_id, focus
    def label(self):
        if self.kind == "build": return f"Raise {self.kind_data}"
        if self.kind == "develop": return f"Develop to {self.kind_data}"
        if self.kind == "found": return "Found village"
        if self.kind == "train": return "Train warrior"
        if self.kind == "gear": return f"Issue {C.KITS[self.kind_data]['name']}"
        return self.kind
    def snapshot(self):
        return {"kind": self.kind, "kind_data": self.kind_data, "months": self.months,
                "months_total": self.months_total, "settlement_id": self.settlement_id,
                "unit_id": self.unit_id, "focus": self.focus}

class Holding:
    def __init__(self, sid, name, hex_pos, size, owner=None):
        self.id, self.name, self.hex, self.size, self.owner = sid, name, tuple(hex_pos), size, owner
        self.buildings = {}
    def size_index(self): return C.SIZE_ORDER.index(self.size)
    def pop_cap(self): return C.POP_CAP[self.size]
    def building_slots(self): return C.BUILDING_SLOTS[self.size]
    def building_slots_free(self): return max(0, self.building_slots() - len(self.buildings))
    def has(self, kind): return kind in self.buildings and self.buildings[kind].staffed
    def garrison_cap(self):
        return C.GARRISON_BASE[self.size] + (C.MILITIA_HALL_CAP if self.has(C.BUILDING_MILITIA_HALL) else 0) + (C.WALLS_CAP if self.has(C.BUILDING_WALLS) else 0) + (C.KEEP_CAP if self.has(C.BUILDING_KEEP) else 0)
    def staff_needed(self): return sum(C.BUILDINGS[k]["staff"] for k,b in self.buildings.items() if b.staffed)
    def upkeep(self): return sum(C.BUILDINGS[k]["upkeep"] for k,b in self.buildings.items() if b.staffed)
    def morale_effect(self): return C.KEEP_MORALE if self.has(C.BUILDING_KEEP) else 0
    def training_slots(self):
        slots = 0
        if self.has(C.BUILDING_DRILL_YARD):
            slots += C.TRAINING_SLOTS_PER_DRILL_YARD
        slots += sum(C.TRAINING_SLOTS_PER_SPECIALIST
                     for kind in (C.BUILDING_SMITHY, C.BUILDING_FLETCHER,
                                  C.BUILDING_STABLES)
                     if self.has(kind))
        return slots
    def supplies(self):
        result = set()
        if self.has(C.BUILDING_SMITHY): result.add(C.BUILDING_SMITHY)
        if self.has(C.BUILDING_FLETCHER): result.add(C.BUILDING_FLETCHER)
        return result
    def farm_output(self, local_population):
        return C.FARM_BASE_WHEAT + min(local_population, self.pop_cap()) // C.FARM_POP_DIVISOR
    def food_produced(self, local_population=0):
        return sum(self.farm_output(local_population) for k,b in self.buildings.items() if k == C.BUILDING_FARM and b.staffed)
    def snapshot(self):
        return {"id": self.id, "name": self.name, "hex": self.hex, "size": self.size,
                "owner": self.owner, "buildings": {k: b.snapshot() for k,b in self.buildings.items()}}
