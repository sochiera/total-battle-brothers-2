from tbb.rules import constants as C
from tbb.rules.rng import RNG
from tbb.rules.units import Unit


def test_gifted_swordsman_and_scout_diverge_as_growth_affinities():
    swordsman = Unit(1, "Sword", 40, 30, 40, 40, 40,
                     ["blade", "vitality", "endurance"])
    scout = Unit(2, "Scout", 40, 30, 40, 40, 40,
                 ["bow", "scouting", "endurance"])
    sword_rng, scout_rng = RNG(5), RNG(5)
    first = sum(swordsman.gain_from_training(
        sword_rng, C.BUILDING_DRILL_YARD).values())
    for _ in range(10):
        swordsman.gain_from_training(sword_rng, C.BUILDING_DRILL_YARD)
    late = sum(swordsman.gain_from_training(
        sword_rng, C.BUILDING_DRILL_YARD).values())
    for _ in range(8):
        scout.gain_from_training(scout_rng, C.BUILDING_DRILL_YARD)
    assert late < first
    assert swordsman.stat("melee") > scout.stat("melee")
    assert scout.stat("ranged") >= 30
    assert all(C.STAT_MIN <= value <= C.STAT_MAX
               for value in swordsman.stats.values())
