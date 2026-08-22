from tbb.rules.rng import RNG
from tbb.rules import constants as C
from tbb.rules.calendar import Calendar
from tbb.rules.terrain import hex_distance, neighbours, move_cost
from tbb.rules import worldgen
from tbb.rules.campaign import Campaign


def test_calendar_shape():
    assert C.MONTHS_PER_YEAR == 13
    assert C.WEEKS_PER_MONTH == 4
    assert C.WEEKS_PER_YEAR == 52
    assert len(C.MONTH_NAMES) == 13


def test_calendar_advance_and_whole_months():
    cal = Calendar(1, 0)
    assert cal.label() == "1, month of Frost"
    cal.advance()
    assert cal.month == 1
    cal2 = Calendar(1, 0)
    for _ in range(13):
        cal2.advance()
    assert cal2.year == 2 and cal2.month == 0
    assert cal2.elapsed_months(Calendar(1, 0)) == 13


def test_terrain_costs():
    assert move_cost(C.TERRAIN_PLAIN) == 1
    assert move_cost(C.TERRAIN_WOODS) == 2
    assert move_cost(C.TERRAIN_HILLS) == 3
    assert move_cost(C.TERRAIN_WATER) is None
    assert C.TERRAIN_VILLAGE in C.MOVE_COST


def test_hex_distance_and_neighbours():
    assert hex_distance((0, 0), (0, 0)) == 0
    assert hex_distance((0, 0), (1, 0)) == 1
    assert hex_distance((0, 0), (2, 0)) == 2
    assert len(neighbours(3, 3)) == 6
    assert len(neighbours(0, 0, 4, 4)) == 2  # corner


def test_campaign_boot():
    c = Campaign(seed=42)
    assert c.seed == 42
    assert c.player.is_player is True


def test_rng_determinism():
    a = RNG(99)
    b = RNG(99)
    assert a.choices(list(range(100)), k=10) == b.choices(list(range(100)),
                                                          k=10)