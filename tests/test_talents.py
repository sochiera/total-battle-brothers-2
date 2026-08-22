"""Talents + training diverge from talents + combat XP: identical starting
stats, different talent sets, same months of training vs same fights result in
stat vectors that differ in the gifted directions and do not converge."""
from tbb.rules import constants as C
from tbb.rules import talents as T
from tbb.rules.rng import RNG
from tbb.rules.units import Unit


def clone(seed, talents):
    r = RNG(seed)
    u = Unit(1, "Clone", 40, 30, 40, 50, 45, 35, talents)
    return u, r


def test_bowgifted_never_gains_melee_from_training():
    u, rng = clone(5, ["bows", "wits", "toughness"])
    melee = u.stat("melee")
    for _ in range(6):
        u.gain_from_training(rng)
    assert u.stat("melee") == melee  # strictly talent gated, no melee talent
    assert u.stat("ranged") > 30


def test_differently_gifted_trained_recruits_diverge():
    sword, rng_s = clone(50, ["swords", "strength", "toughness"])
    scout, rng_b = clone(50, ["bows", "wits", "toughness"])
    for _ in range(8):
        sword.gain_from_training(rng_s)
        scout.gain_from_training(rng_b)
    assert sword.stat("melee") > scout.stat("melee") + 3
    assert sword.stat("melee") > 40  # gifted at the sword, he grows
    assert scout.stat("melee") == 40  # never gains what he lacks
    assert scout.stat("ranged") > sword.stat("ranged") + 2


def test_differently_gifted_fighters_diverge_after_combat():
    sword, rng_s = clone(60, ["swords", "strength", "toughness"])
    scout, rng_b = clone(60, ["bows", "wits", "toughness"])
    for _ in range(10):
        sword.gain_from_combat(rng_s)
        scout.gain_from_combat(rng_b)
    assert sword.stat("melee") > scout.stat("melee") + 3
    assert scout.stat("melee") == 40
    assert scout.stat("ranged") > sword.stat("ranged") + 2


def test_same_talent_trained_and_fought_diverge_training_vs_war():
    # same talents: drill builds conditioning, war hardens resolve
    a, ra = clone(70, ["swords", "strength", "toughness"])
    b, rb = clone(70, ["swords", "strength", "toughness"])
    for _ in range(6):
        a.gain_from_training(ra)
        b.gain_from_combat(rb)
    assert a.stat("fatigue") > b.stat("fatigue")
    assert b.stat("resolve") > a.stat("resolve")
    # neither converges onto an identical fighter
    assert a.stat_vector() != b.stat_vector()


def test_diminishing_returns_late():
    u, rng = clone(70, ["swords", "strength", "toughness"])
    first = sum(u.gain_from_training(rng).values())
    for _ in range(20):
        u.gain_from_training(rng)
    late = sum(u.gain_from_training(rng).values())
    assert late < first


def test_stat_caps_never_exceeded():
    u, rng = clone(80, ["swords", "strength", "toughness"])
    for _ in range(50):
        u.gain_from_combat(rng)
    for k, v in u.stats.items():
        assert v <= C.STAT_MAX
        assert v >= C.STAT_MIN


def test_talents_samples_no_repeat_and_size():
    r = RNG(1)
    for _ in range(20):
        set_ = T.roll_talents(r)
        assert len(set_) == C.NUM_TALENTS
        assert len(set(set_)) == C.NUM_TALENTS