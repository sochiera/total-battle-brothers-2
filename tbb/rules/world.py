"""Deterministic campaign map data; no presentation imports."""
from . import terrain as T

class World:
    def __init__(self, width, height):
        self.width, self.height = width, height
        self.grid = {}
        self.crossings = {}  # river hex -> ford or bridge
        self.regions = {}  # region name -> hexes
        self.region_by_hex = {}
        self.rivers = {}  # river name -> hexes
        self.river_by_hex = {}

    def in_bounds(self, pos):
        q, r = pos
        return 0 <= q < self.width and 0 <= r < self.height

    def terrain(self, pos):
        return self.grid.get(tuple(pos))

    def set_terrain(self, pos, value):
        self.grid[tuple(pos)] = value

    def set_crossing(self, pos, kind="ford"):
        terrain = self.terrain(pos)
        if terrain == "river":
            if kind not in ("ford", "bridge"):
                raise ValueError("crossing must be a ford or bridge")
        elif terrain == "mountain":
            if kind != "pass":
                raise ValueError("only a pass cuts through mountains")
        else:
            raise ValueError("crossings belong on river or mountain hexes")
        self.crossings[tuple(pos)] = kind

    def crossing(self, pos):
        return self.crossings.get(tuple(pos))

    def neighbours(self, pos):
        return T.neighbours(*pos, self.width, self.height)

    def is_passable(self, pos):
        return T.is_passable(self.terrain(pos), self.crossing(pos))

    def walkable_neighbours(self, pos):
        return [n for n in self.neighbours(pos) if self.is_passable(n)]

    def all_hexes(self):
        return list(self.grid)

    def region_at(self, pos):
        return self.region_by_hex.get(tuple(pos))

    def river_at(self, pos):
        return self.river_by_hex.get(tuple(pos))

    @property
    def region_names(self):
        return tuple(self.regions)

    @property
    def river_names(self):
        return tuple(self.rivers)

    def hex_count(self):
        return len(self.grid)
