"""Talents: rolled per warrior, gate which stat gains are kept when training
or fighting. They grant no flat bonuses.

Every gain hands out GAIN_POINTS_PER_GAIN points. A conditioning share always
goes to one universal stat (training -> fatigue, combat XP -> resolve) because
marching hardens the body and war hardens nerve. Every other point goes only
to stats named by the warrior's talent set, so a bow-gifted scout never
improves melee no matter how long he drills.
"""
from . import constants


def STATS_ORDER():
    return list(constants.STATS)


def diminish(raw, seasoning):
    return max(1, int(round(raw / (1.0 + seasoning * constants.DIMINISH_FACTOR))))


def pooled_stats(talents):
    """Union of stat names gifted by the given talent set."""
    out = []
    for t in talents:
        for s in constants.TALENT_STATS[t]:
            if s not in out:
                out.append(s)
    return out


def roll_talents(rng):
    """Sample NUM_TALENTS without replacement from the locked pool."""
    return rng.sample_no_repeat(constants.TALENT_POOL, constants.NUM_TALENTS)


def _allocate(rng, total, talents, cond_stat, cond_share):
    alloc = {s: 0 for s in STATS_ORDER()}
    if cond_share > 0 and total > 0:
        alloc[cond_stat] = min(total, cond_share)
        total -= alloc[cond_stat]
    stats = pooled_stats(talents)
    if not stats or total <= 0:
        return alloc
    per, rem = divmod(total, len(stats))
    for s in stats:
        alloc[s] += per
    for _ in range(rem):
        alloc[rng.choice(stats)] += 1
    return alloc


def training_alloc(rng, talents, total=None):
    """Points kept from a completed training order (whole months)."""
    if total is None:
        total = constants.GAIN_POINTS_PER_GAIN
    return _allocate(rng, total, talents,
                     constants.TRAIN_CONDITIONING_STAT,
                     constants.TRAIN_CONDITIONING_SHARE)


def combat_alloc(rng, talents, total=None):
    """Points kept from a band of experience from fighting."""
    if total is None:
        total = constants.GAIN_POINTS_PER_GAIN
    return _allocate(rng, total, talents,
                     constants.XP_CONDITIONING_STAT,
                     constants.XP_CONDITIONING_SHARE)