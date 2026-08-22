"""Campaign hex terrain and neighbour maths (axial coordinates).

Axial coords (q, r) with s = -q-r. Neighbour offsets are the six axial
directions. The world grid is MAP_WIDTH x MAP_HEIGHT.
"""
from . import constants as C

NEIGHBOURS = [
    (1, 0), (1, -1), (0, -1),
    (-1, 0), (-1, 1), (0, 1),
]


def neighbours(q, r, width=C.MAP_WIDTH, height=C.MAP_HEIGHT):
    res = []
    for dq, dr in NEIGHBOURS:
        nq, nr = q + dq, r + dr
        if 0 <= nq < width and 0 <= nr < height:
            res.append((nq, nr))
    return res


def hex_distance(a, b):
    (q1, r1), (q2, r2) = a, b
    s1, s2 = -q1 - r1, -q2 - r2
    return max(abs(q1 - q2), abs(r1 - r2), abs(s1 - s2))


def move_cost(terrain):
    return C.MOVE_COST[terrain]


def is_passable(terrain):
    return C.MOVE_COST[terrain] is not None


def can_found(terrain):
    """A new village may only rise on empty suitable (plain) land."""
    return terrain == C.TERRAIN_PLAIN


def battle_terrain_from_campaign(terrain):
    """Campaign terrain -> battle terrain (village handled separately)."""
    return terrain