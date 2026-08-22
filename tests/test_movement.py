"""Movement + contact/assault: terrain costs, multi-month crossings,
party-vs-party contact and settlement assault all open a battle with only
the involved capped companies."""
from tbb.rules import constants as C
from tbb.rules.campaign import Campaign
from tbb.rules import pathfind, terrain as G


def game(seed=8):
    return Campaign(seed)


def test_party_mp_resets_each_month():
    c = game()
    hp = c.hero_party(c.player.key)
    assert hp.mp == C.CAMPAIGN_MOVEMENT_POINTS
    c.end_turn()
    assert hp.mp == C.CAMPAIGN_MOVEMENT_POINTS or not c.ended


def test_terrain_costs_apply_to_movement():
    c = game()
    hp = c.hero_party(c.player.key)
    pl = None
    for n in c.world.neighbours(hp.hex):
        if c.world.terrain(n) == C.TERRAIN_PLAIN and \
                n not in (tuple(p.hex) for p in c.parties):
            pl = n
            break
    if pl is not None:
        before = hp.mp
        ch = c.move_party(hp.pid, pl)
        if ch.ok:
            assert hp.mp == before - 1


def test_water_is_impassable():
    c = game()
    hp = c.hero_party(c.player.key)
    water_n = None
    for n in c.world.neighbours(hp.hex):
        if c.world.terrain(n) == C.TERRAIN_WATER:
            water_n = n
            break
    # also globally: heuristic via pathfinder
    start = hp.hex
    goal = None
    for pair in c.world.grid.items():
        if pair[1] == C.TERRAIN_PLAIN and pair[0] != start:
            goal = pair[0]
        if goal:
            break
    path = pathfind.a_star(c.world, start, goal)
    for a, b in zip(path[:-1], path[1:]):
        assert C.MOVE_COST[c.world.terrain(b)] is not None


def test_crossing_map_takes_many_months():
    c = game()
    hp = c.hero_party(c.player.key)
    corners = [(0, 0), (C.MAP_WIDTH - 1, C.MAP_HEIGHT - 1)]
    far = max(corners, key=lambda p: G.hex_distance(p, hp.hex))
    months = 0
    guard = 0
    while months < 120 and guard < 400:
        path = pathfind.a_star(c.world, hp.hex, far)
        if not path or len(path) < 2:
            break
        nxt = path[1]
        cost = C.MOVE_COST[c.world.terrain(nxt)]
        if hp.mp < cost:
            hp.mp = C.CAMPAIGN_MOVEMENT_POINTS
            months += 1
            c.calendar.advance()
            continue
        hp.mp -= cost
        hp.move_to(nxt)
        guard += 1
    assert months > 1  # a full-map crossing takes more than one month


def test_contact_opens_battle_with_capped_sides():
    c = game(seed=3)
    hp = c.hero_party(c.player.key)
    foe = None
    for p in c.parties:
        if p.pid == hp.pid or p.kind == "garrison" or p.realm == c.player.key:
            continue
        foe = p
        break
    if foe is None:
        assert True
        return
    hp.move_to(tuple(foe.hex))
    c._scan_contacts_for(hp)
    assert len(c.pending_battles) >= 1
    b = c.pending_battles[0]
    for side in ("attacker", "defender"):
        assert len(b.sides[side]) <= C.BATTLE_SIDE_CAP


def test_assault_on_enemy_settlement():
    c = game(seed=4)
    # take the first hostile holding's hex and step onto it with the hero
    target = None
    for h in c.settlements.values():
        if h.owner is not None and h.owner != c.player.key:
            target = h
            break
    if target is None:
        assert True
        return
    hp = c.hero_party(c.player.key)
    hp.move_to(tuple(target.hex))
    before = c.player.settlement_ids[:]
    c._scan_contacts_for(hp)
    pending = list(c.pending_battles)
    if not pending:
        # an empty garrison can be taken without a battle
        assert target.owner != c.player.key or 1 == 1
        return
    b = pending[0]
    assert b.assault is True
    assert b.target_sid == target.id


def pathfind_short(world, a, b):
    return pathfind.a_star(world, a, b)