"""Pure axial-hex helpers shared by campaign and battle rules."""
from . import constants as C

NEIGHBOURS = ((1, 0), (1, -1), (0, -1), (-1, 0), (-1, 1), (0, 1))

def neighbours(q, r, width=C.MAP_WIDTH, height=C.MAP_HEIGHT):
    return [(q + dq, r + dr) for dq, dr in NEIGHBOURS
            if 0 <= q + dq < width and 0 <= r + dr < height]

def hex_distance(a, b):
    q1, r1 = a; q2, r2 = b
    return max(abs(q1-q2), abs(r1-r2), abs((-q1-r1)-(-q2-r2)))

def move_cost(terrain, crossing=None):
    if terrain == C.TERRAIN_RIVER:
        return 1 if crossing in C.RIVER_CROSSINGS else None
    return C.MOVE_COST.get(terrain)

def is_passable(terrain, crossing=None):
    return move_cost(terrain, crossing) is not None

def can_found(terrain, occupied=False):
    return not occupied and terrain in (C.TERRAIN_PLAINS, C.TERRAIN_RUINS)

def battle_terrain_from_campaign(terrain):
    return terrain if terrain in C.CAMPAIGN_TERRAINS else C.TERRAIN_PLAINS
