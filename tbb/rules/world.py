"""The campaign hex world: terrain grid plus shared placement helpers."""
from . import constants as C
from . import terrain as T


class World:
    def __init__(self, width, height):
        self.width = width
        self.height = height
        self.grid = {}  # (q, r) -> terrain code

    def in_bounds(self, pos):
        q, r = pos
        return 0 <= q < self.width and 0 <= r < self.height

    def terrain(self, pos):
        return self.grid.get(tuple(pos))

    def set_terrain(self, pos, terrain):
        self.grid[tuple(pos)] = terrain

    def neighbours(self, pos):
        return T.neighbours(*pos, self.width, self.height)

    def is_passable(self, pos):
        return T.is_passable(self.terrain(pos))

    def walkable_neighbours(self, pos):
        return [n for n in self.neighbours(pos) if self.is_passable(n)]

    def all_hexes(self):
        return list(self.grid.keys())

    def hex_count(self):
        return len(self.grid)