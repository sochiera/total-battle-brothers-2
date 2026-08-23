"""Headless contract for the generated 64x48 multi-biome overworld."""
from tbb.rules import constants as C
from tbb.rules import terrain as G
from tbb.rules import pathfind
from tbb.rules.rng import RNG
from tbb.rules.worldgen import generate
from tbb.rules.campaign import Campaign

SEEDS = (734102, 2, 3)


def test_every_seed_contains_every_biome_and_full_grid():
    for seed in SEEDS:
        data = generate(RNG(seed))
        world = data["world"]
        assert world.hex_count() == C.MAP_WIDTH * C.MAP_HEIGHT
        present = set(world.grid.values())
        assert set(C.CAMPAIGN_TERRAINS) <= present, \
            (seed, set(C.CAMPAIGN_TERRAINS) - present)
        # rivers must be crossable somewhere
        assert any(kind in C.RIVER_CROSSINGS
                   for kind in world.crossings.values())
    # Keep the broad worldgen promise exercised without making every
    # pathfinding assertion below run 150 full campaigns.
    for seed in range(150):
        data = generate(RNG(seed))
        assert len(data["realms"]) == C.NUM_DUCHIES
        assert all(realm.settlement_ids for realm in data["realms"].values())
        assert set(C.CAMPAIGN_TERRAINS) <= set(data["world"].grid.values())


def test_mountain_blocks_travel_except_through_cut_passes():
    for seed in SEEDS:
        data = generate(RNG(seed))
        world = data["world"]
        mountains = [p for p, t in world.grid.items()
                     if t == C.TERRAIN_MOUNTAIN]
        assert mountains
        passes = [p for p, kind in world.crossings.items()
                  if kind == C.MOUNTAIN_PASS]
        assert len(passes) >= 2
        for pos in mountains:
            if pos in passes:
                assert G.move_cost(C.TERRAIN_MOUNTAIN, "pass") == \
                    C.PASS_MOVE_COST
            else:
                assert G.move_cost(C.TERRAIN_MOUNTAIN) is None
                assert not world.is_passable(pos)


def test_cheapest_west_east_route_costs_twenty_or_more_and_uses_a_pass():
    for seed in SEEDS:
        data = generate(RNG(seed))
        world = data["world"]
        wests = [p for p in world.grid
                 if p[0] <= 1 and world.is_passable(p)]
        easts = [p for p in world.grid
                 if p[0] >= C.MAP_WIDTH - 2 and world.is_passable(p)]
        assert wests and easts
        best = None
        path = None
        for start in wests[::3]:
            for goal in easts[::3]:
                route = pathfind.a_star(world, start, goal)
                assert route, (seed, start, goal)
                cost = sum(G.move_cost(world.terrain(p),
                                       world.crossing(p))
                           for p in route[1:])
                if best is None or cost < best:
                    best, path = cost, route
        assert best >= C.LONG_AXIS_MIN_MP
        assert any(world.terrain(p) == C.TERRAIN_MOUNTAIN and
                   world.crossing(p) == C.MOUNTAIN_PASS for p in path)


def test_march_orders_refuse_raw_mountain():
    campaign = Campaign(734102)
    party = campaign.hero_party(campaign.player.key)
    mountain = next(p for p, t in campaign.world.grid.items()
                    if t == C.TERRAIN_MOUNTAIN and
                    campaign.world.crossing(p) != C.MOUNTAIN_PASS)
    # stand the company right beside the wall
    party.move_to(mountain)
    neighbour = campaign.world.neighbours(mountain)[0]
    campaign.world.set_terrain(neighbour, C.TERRAIN_PLAINS)
    party.move_to(neighbour)
    party.mp = C.CAMPAIGN_MOVEMENT_POINTS
    result = campaign.move_party(party.pid, mountain)
    assert not result and "pass" in result.reason


def test_realm_capitals_keep_room_and_neutrals_and_camps_exist():
    for seed in SEEDS:
        campaign = Campaign(seed)
        capitals = [campaign.settlements[r.settlement_ids[0]].hex
                    for r in campaign.realms.values()]
        assert len(set(capitals)) == len(capitals)
        for i, a in enumerate(capitals):
            for b in capitals[i + 1:]:
                assert G.hex_distance(a, b) >= 5
        neutrals = [h for h in campaign.settlements.values()
                    if h.owner is None]
        assert C.MIN_NEUTRALS <= len(neutrals) <= C.MAX_NEUTRALS
        bandits = [p for p in campaign.parties if p.kind == "bandit"]
        assert len(bandits) == C.NUM_ROBBER_BANDS
        for party in bandits:
            assert C.BANDIT_PARTY_SIZE[0] <= len(party.unit_ids) <= \
                C.BANDIT_PARTY_SIZE[1]
            camped = (campaign.world.terrain(party.hex) ==
                      C.TERRAIN_RUINS or
                      any(campaign.world.terrain(n) == C.TERRAIN_RUINS
                          for n in campaign.world.neighbours(party.hex)))
            assert camped


def test_founding_ground_and_farmland_contract():
    campaign = Campaign(734102)
    world = campaign.world
    assert G.can_found(C.TERRAIN_FARMLAND)
    for blocked in (C.TERRAIN_MARSH, C.TERRAIN_COAST, C.TERRAIN_FOREST,
                    C.TERRAIN_MOUNTAIN):
        assert not G.can_found(blocked)
    near_holding = any(
        world.terrain(n) == C.TERRAIN_FARMLAND
        for h in campaign.settlements.values()
        for n in world.neighbours(h.hex))
    assert near_holding


def test_same_seed_is_bit_stable_and_different_seeds_differ():
    first, second = generate(RNG(4242)), generate(RNG(4242))
    assert first["world"].grid == second["world"].grid
    assert first["world"].crossings == second["world"].crossings
    third = generate(RNG(9001))
    assert first["world"].grid != third["world"].grid


def test_campaign_terrain_constants_are_locked():
    expected = {C.TERRAIN_PLAINS: 1, C.TERRAIN_FOREST: 2,
                C.TERRAIN_HILLS: 2, C.TERRAIN_RIVER: None,
                C.TERRAIN_ROAD: 1, C.TERRAIN_VILLAGE: 1,
                C.TERRAIN_RUINS: 1, C.TERRAIN_MOUNTAIN: None,
                C.TERRAIN_MARSH: 3, C.TERRAIN_FARMLAND: 1,
                C.TERRAIN_COAST: 1}
    for terrain, cost in expected.items():
        assert C.MOVE_COST[terrain] == cost
        assert G.move_cost(terrain) == cost
    assert G.move_cost(C.TERRAIN_MOUNTAIN, C.MOUNTAIN_PASS) == \
        C.PASS_MOVE_COST == 2
    assert G.move_cost(C.TERRAIN_RIVER, "ford") == 1
    assert (C.BATTLE_WIDTH, C.BATTLE_HEIGHT) == (30, 20)
    assert C.TEMP_WOUND_MONTHS == 3
    assert C.LONG_AXIS_MIN_MP == 45
