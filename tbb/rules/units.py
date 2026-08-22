"""Units: every warrior is a named individual with stats, talents, a gear kit,
wounds, stun and life state. Death is permanent.
"""
from . import constants as C
from . import talents as T


class Unit:
    _pid = 0  # not used; unit ids come from the campaign counter

    def __init__(self, unit_id, name, melee, ranged, toughness, fatigue,
                 resolve, initiative, talents, kit=C.KIT_POOR, realm=None):
        self.id = unit_id
        self.name = name
        self.realm = realm
        self.stats = {
            "melee": melee, "ranged": ranged, "toughness": toughness,
            "fatigue": fatigue, "resolve": resolve, "initiative": initiative,
        }
        self.talents = list(talents)
        self.kit = kit
        self.xp = 0
        self.seasoning = 0          # completed gains -> diminishing returns
        self.wounds = []            # list of wound names
        self.battle_wounds = []     # temporary wounds still active in a battle
        self.stun_until = None      # battle-only: round when the stun ends
        self.alive = True
        self.is_hero = False
        self.is_heir = False

    # ---- derived stats ----------------------------------------------------
    def kit_mods(self):
        return dict(C.KITS[self.kit]["mods"])

    def stat(self, name):
        m = self.kit_mods()
        base = self.stats.get(name, 0) + m.get(name, 0)
        for w in self.wounds:
            base += C.WOUND_STAT_EFFECT.get(w, {}).get(name, 0)
        for w in self.battle_wounds:
            base += C.WOUND_STAT_EFFECT.get(w, {}).get(name, 0)
        return base

    def is_dead(self):
        return not self.alive

    def skill_label(self):
        order = list(C.STATS)
        return {k: self.stat(k) for k in order}

    # ---- talent-gated growth ----------------------------------------------
    def _gain(self, alloc, rng):
        for name in C.STATS:
            nxt = max(C.STAT_MIN, min(C.STAT_MAX,
                                      self.stats[name] + alloc.get(name, 0)))
            self.stats[name] = nxt
        self.seasoning += 1
        return dict(alloc)

    def gain_from_training(self, rng):
        """Points kept from a completed training month. Diminishing."""
        total = T.diminish(C.GAIN_POINTS_PER_GAIN, self.seasoning)
        alloc = T.training_alloc(rng, self.talents, total)
        return self._gain(alloc, rng)

    def gain_from_combat(self, rng):
        """Points kept from a band of combat experience. Diminishing."""
        total = T.diminish(C.GAIN_POINTS_PER_GAIN, self.seasoning)
        alloc = T.combat_alloc(rng, self.talents, total)
        return self._gain(alloc, rng)

    # convenience for tests and UI
    def stat_vector(self):
        return tuple(self.stat(k) for k in C.STATS)

    def __repr__(self):
        return "Unit(%s, %s)" % (self.name, self.realm)