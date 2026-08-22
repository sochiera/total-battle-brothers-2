"""Talent rolls and affinity-only growth."""
from . import constants as C

def roll_talents(rng):
    return rng.sample(list(C.TALENT_POOL), C.NUM_TALENTS)

def diminish(raw, seasoning):
    return max(1, int(round(raw / (1.0 + seasoning * C.DIMINISH_FACTOR))))

def _weights(talents, focus=None):
    weights = {key: 0 for key in C.STATS}
    for talent in talents:
        for stat in C.TALENT_STATS.get(talent, ()):
            weights[stat] += 2 if stat == focus else 1
    return weights

def _allocate(rng, talents, total, conditioning, focus=None):
    weights = _weights(talents, focus)
    result = {key: 0 for key in C.STATS}
    result[conditioning] = 1
    remaining = max(0, total - 1)
    gates = {
        C.BUILDING_DRILL_YARD: {"melee", "fatigue"},
        C.BUILDING_SMITHY: {"melee", "hit_points"},
        C.BUILDING_FLETCHER: {"ranged"},
        C.BUILDING_STABLES: {"fatigue"},
    }
    allowed = gates.get(focus)
    candidates = [key for key, weight in weights.items() if weight and (allowed is None or key in allowed)]
    if candidates:
        for _ in range(remaining):
            result[rng.choice(candidates)] += 1
    return {key: value for key, value in result.items() if value}

def training_alloc(rng, talents, total, focus=None):
    return _allocate(rng, talents, total, C.TRAIN_CONDITIONING_STAT, focus)

def combat_alloc(rng, talents, total):
    return _allocate(rng, talents, total, C.XP_CONDITIONING_STAT)
