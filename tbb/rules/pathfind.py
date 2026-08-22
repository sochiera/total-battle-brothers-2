"""Cheapest-first hex pathfinding on the campaign world."""
import heapq as _heapq
from . import constants as C
from . import terrain as G


def move_cost(world, pos, from_pos=None):
    return G.move_cost(world.terrain(pos), world.crossing(pos))


def a_star(world, start, goal, max_cost=None):
    """Return a list of hexes from start to goal (inclusive) using the
    cheapest path, or [] if unreachable. max_cost caps total movement."""
    start, goal = tuple(start), tuple(goal)
    if start == goal:
        return [goal]
    frontier = [(0, start)]
    came = {start: start}
    g = {start: 0}
    found = None
    while frontier:
        _, cur = _heapq.heappop(frontier)
        if cur == goal:
            found = cur
            break
        if max_cost is not None and g[cur] > max_cost:
            continue
        for nxt in world.neighbours(cur):
            c = move_cost(world, nxt)
            if c is None:
                continue
            nc = g[cur] + c
            if max_cost is not None and nc > max_cost:
                continue
            if nxt not in g or nc < g[nxt]:
                g[nxt] = nc
                came[nxt] = cur
                h = G.hex_distance(nxt, goal)
                _heapq.heappush(frontier, (nc + h, nxt))
    if found is None:
        return []
    # rebuild path
    path = [found]
    cur = found
    while came[cur] != cur:
        cur = came[cur]
        path.append(cur)
    path.reverse()
    return path


def step_cost(world, a, b):
    """Cost to step from a to b."""
    return move_cost(world, b)
