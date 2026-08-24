from pathlib import Path
import subprocess
import sys

from tbb.rules import constants as C
from tbb.rules.calendar import Calendar
from tbb.rules.terrain import move_cost, can_found


def test_calendar_roman_months_and_year_boundary():
    assert C.MONTH_LABELS == tuple("I II III IV V VI VII VIII IX X XI XII XIII".split())
    calendar = Calendar()
    assert "Month I" in calendar.label()
    calendar.advance(12)
    assert calendar.month_name() == "XIII"
    calendar.advance()
    assert (calendar.year, calendar.month) == (2, 0)


def test_campaign_terrain_costs_and_river_crossings():
    assert [move_cost(kind) for kind in
            (C.TERRAIN_PLAINS, C.TERRAIN_FOREST, C.TERRAIN_HILLS,
             C.TERRAIN_ROAD, C.TERRAIN_VILLAGE, C.TERRAIN_RUINS)] == [1, 2, 2, 1, 1, 1]
    assert move_cost(C.TERRAIN_RIVER) is None
    assert move_cost(C.TERRAIN_RIVER, "ford") == 1
    assert can_found(C.TERRAIN_PLAINS)
    assert can_found(C.TERRAIN_RUINS)
    assert not can_found(C.TERRAIN_FOREST)


def test_rules_package_has_no_presentation_import():
    rules_root = Path(__file__).parents[1] / "tbb" / "rules"
    forbidden = ("import pygame", "from pygame", "tbb.app", "from ..app",
                 "from .app")
    for source in rules_root.glob("*.py"):
        text = source.read_text(encoding="utf-8")
        assert not any(token in text for token in forbidden), source

    probe = subprocess.run(
        [sys.executable, "-c",
         "import sys; import tbb.rules; "
         "assert not any(n == 'pygame' or n.startswith('tbb.app') "
         "for n in sys.modules)"],
        cwd=rules_root.parents[1], capture_output=True, text=True,
        check=False)
    assert probe.returncode == 0, probe.stderr
