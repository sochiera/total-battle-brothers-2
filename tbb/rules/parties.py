"""Mobile hero companies and immobile settlement garrisons."""
from . import constants as C

class Party:
    def __init__(self, pid, kind, realm, pos, unit_ids=(), settlement_id=None):
        self.pid, self.kind, self.realm, self.hex = pid, kind, realm, tuple(pos)
        self.unit_ids, self.settlement_id, self.mp = list(unit_ids), settlement_id, 0
        self.road_bonus = False
    def move_to(self, pos): self.hex = tuple(pos)
    def add(self, uid):
        if uid not in self.unit_ids: self.unit_ids.append(uid)
    def remove(self, uid):
        if uid in self.unit_ids: self.unit_ids.remove(uid)
    def size(self): return len(self.unit_ids)
    def alive_units(self, units): return [units[i] for i in self.unit_ids if i in units and units[i].alive]
    def is_bandit(self): return self.kind == "bandit"
    def snapshot(self): return {"pid": self.pid, "kind": self.kind, "realm": self.realm,
                                "hex": self.hex, "unit_ids": list(self.unit_ids),
                                "settlement_id": self.settlement_id, "mp": self.mp,
                                "road_bonus": self.road_bonus}
