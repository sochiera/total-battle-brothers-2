"""Parties: field detachments on the campaign map. A hero party carries the
realm's field army (hero + at most COMPANY_CAP warriors) and retreatable bandit
raiders. Garrison parties sit in a settlement until assaulted."""


class Party:
    def __init__(self, pid, kind, realm, pos, unit_ids, settlement_id=None,
                 is_bandit=False):
        self.pid = pid
        self.kind = kind            # 'hero' | 'garrison' | 'bandit'
        self.realm = realm          # realm key or None (bandits / neutrals)
        self.hex = tuple(pos)
        self.unit_ids = list(unit_ids)
        self.settlement_id = settlement_id
        self.mp = 0

    def move_to(self, pos):
        self.hex = tuple(pos)

    def add(self, uid):
        if uid not in self.unit_ids:
            self.unit_ids.append(uid)

    def remove(self, uid):
        if uid in self.unit_ids:
            self.unit_ids.remove(uid)

    def size(self):
        return len(self.unit_ids)

    def alive_units(self, units):
        return [units[u] for u in self.unit_ids if u in units and units[u].alive]

    def is_bandit(self):
        return self.kind == "bandit"

    def snapshot(self):
        return {"pid": self.pid, "kind": self.kind, "realm": self.realm,
                "hex": self.hex, "unit_ids": list(self.unit_ids),
                "settlement_id": self.settlement_id, "mp": self.mp}