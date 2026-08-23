#!/usr/bin/env python3
"""Regenerate the original pixel tiles committed under assets/tiles/.

Run from the project root after editing the procedural painters in
tbb/app/art.py:

    SDL_VIDEODRIVER=dummy .venv/bin/python3 tools/render_tiles.py
"""
import os
import sys
from pathlib import Path

os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pygame

from tbb.app import art

TILES = {
    "plains": lambda: art._grass_tile(1),
    "forest": lambda: art.woods_tile(2),
    "hills": lambda: art.hill_tile(3),
    "river": lambda: art.river_tile(4),
    "road": lambda: art.road_tile(5),
    "ruins": lambda: art.ruins_tile(6),
    "village": lambda: art.village_tile(7),
    "ford": lambda: art.crossing_tile(8, "ford"),
    "bridge": lambda: art.crossing_tile(9, "bridge"),
    "mountain": lambda: art.mountain_tile(10),
    "marsh": lambda: art.marsh_tile(11),
    "farmland": lambda: art.farmland_tile(12),
    "coast": lambda: art.coast_tile(13),
    "pass": lambda: art.pass_tile(14),
}


def main():
    pygame.init()
    pygame.display.set_mode((1, 1))
    out = Path(__file__).resolve().parents[1] / "assets" / "tiles"
    out.mkdir(parents=True, exist_ok=True)
    for name, painter in TILES.items():
        path = out / ("%s.png" % name)
        pygame.image.save(painter(), str(path))
        print("wrote", path, path.stat().st_size, "bytes")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
