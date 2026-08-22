"""Named individual warriors and their permanent progression."""
from . import constants as C
from . import talents as T

class Unit:
    def __init__(self, unit_id, name, *values, stats=None, talents=None,
                 origin="the road", age=18, kit="light", realm=None,
                 is_hero=False):
        self.id, self.name, self.origin = unit_id, name, origin
        self.age = int(age)
        if stats is None:
            if len(values) >= 7 and talents is None:
                # Compatibility with the former six-number constructor; the
                # live model still stores only the five canonical stats.
                stats, talents = dict(zip(C.STATS, values[:5])), values[6]
            elif len(values) >= 6 and talents is None:
                # New positional form: five stats followed by talents.
                stats, talents = dict(zip(C.STATS, values[:5])), values[5]
            else:
                stats = dict(zip(C.STATS, values[:5]))
        self.stats = {k: int(stats.get(k, C.STAT_MIN)) for k in C.STATS}
        self.talents = list(talents or ())[:C.NUM_TALENTS]
        self.kit = kit if kit in C.KITS else "light"
        self.realm = realm
        self.xp = 0
        self.seasoning = 0
        self.wounds = []
        self.battle_wounds = []
        self.stun_until = None
        self.alive = True
        self.is_hero = bool(is_hero)
        self.is_heir = False
        self.shaken = False
        self.max_hit_points = max(C.STAT_MIN, self.stats["hit_points"])
        self.current_hit_points = self.max_hit_points

    @property
    def hp(self):
        return self.current_hit_points

    @hp.setter
    def hp(self, value):
        self.current_hit_points = max(0, int(value))
        if self.current_hit_points == 0:
            self.alive = False

    @property
    def hit_points(self): return self.current_hit_points
    @property
    def max_hp(self): return self.max_hit_points
    @property
    def current_hp(self): return self.current_hit_points

    def kit_mods(self):
        return dict(C.KITS[self.kit]["mods"])

    def stat(self, name):
        value = self.stats.get(name, 0) + self.kit_mods().get(name, 0)
        for wound in self.wounds + self.battle_wounds:
            value += C.WOUND_STAT_EFFECT.get(wound, {}).get(name, 0)
        if name == "resolve" and self.shaken:
            value = min(value, C.SHAKEN_RESOLVE_CAP)
        return max(0, value)

    def is_dead(self):
        return not self.alive

    def skill_label(self):
        return {key: self.stat(key) for key in C.STATS}

    def _gain(self, allocation):
        for key, amount in allocation.items():
            self.stats[key] = min(C.STAT_MAX, max(C.STAT_MIN,
                                                  self.stats[key] + amount))
        self.max_hit_points = max(1, self.stat("hit_points"))
        self.current_hit_points = min(self.current_hit_points, self.max_hit_points)
        self.seasoning += 1
        return dict(allocation)

    def gain_from_training(self, rng, focus=None):
        total = T.diminish(C.GAIN_POINTS_PER_GAIN, self.seasoning)
        allocation = T.training_alloc(rng, self.talents, total, focus)
        return self._gain(allocation)

    def gain_from_combat(self, rng):
        total = T.diminish(C.GAIN_POINTS_PER_GAIN, self.seasoning)
        allocation = T.combat_alloc(rng, self.talents, total)
        return self._gain(allocation)

    def add_combat_xp(self, amount, rng):
        self.xp += int(amount)
        while self.xp >= C.XP_PER_GAIN:
            self.xp -= C.XP_PER_GAIN
            self.gain_from_combat(rng)

    def stat_vector(self):
        return tuple(self.stat(k) for k in C.STATS)

    def age_one_year(self):
        self.age += 1

    def __repr__(self):
        return f"Unit({self.id}, {self.name!r})"
